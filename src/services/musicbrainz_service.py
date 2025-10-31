# Curator Apollon: MusicBrainz integration for artist deep-dive and discography
# Minimal, rate-limited client adhering to MB API rules

import requests
import time
from typing import Dict, List, Optional


class MusicBrainzService:
    BASE_URL = "https://musicbrainz.org/ws/2"

    def __init__(self, app_name: str = "CuratorApollon", app_version: str = "0.1", contact: str = "support@occybyte.com"):
        self.session = requests.Session()
        # MusicBrainz requires a meaningful User-Agent
        self.session.headers.update({
            "User-Agent": f"{app_name}/{app_version} ({contact})",
            "Accept": "application/json",
        })
        self._last_call_ts = 0.0

    def _respect_rate_limit(self):
        # MB: never more than ONE call per second
        now = time.time()
        elapsed = now - self._last_call_ts
        if elapsed < 1.05:
            time.sleep(1.05 - elapsed)
        self._last_call_ts = time.time()

    def search_artist(self, name: str, limit: int = 5) -> List[Dict]:
        if not name:
            return []
        self._respect_rate_limit()
        resp = self.session.get(
            f"{self.BASE_URL}/artist",
            params={"query": name, "limit": max(1, min(limit, 25)), "fmt": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        return data.get("artists", [])

    def get_release_groups_for_artist(self, artist_mbid: str, limit: int = 100, offset: int = 0) -> Dict:
        if not artist_mbid:
            return {"release-groups": [], "release-group-count": 0}
        self._respect_rate_limit()
        resp = self.session.get(
            f"{self.BASE_URL}/release-group",
            params={
                "artist": artist_mbid,
                "limit": max(1, min(limit, 100)),
                "offset": max(0, offset),
                "fmt": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json() or {"release-groups": [], "release-group-count": 0}


