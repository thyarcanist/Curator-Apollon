# -*- mode: python ; coding: utf-8 -*-

block_cipher = None  # Remove encryption since it's deprecated

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/appearance/fonts/*', 'appearance/fonts'),
        ('src/appearance/img/*', 'appearance/img'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'ttkbootstrap',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'jaraco.text',
        'pkg_resources._vendor.jaraco',
        'importlib_resources.trees'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CuratorApollon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Temporarily set to True to see error messages
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/appearance/img/apollon.ico'
) 