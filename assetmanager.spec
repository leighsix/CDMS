# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['assetmanager.py'],
    pathex=[],
    binaries=[('C:\\Users\\hyunc\\PycharmProjects\\CDMS\\.venv\\Lib\\site-packages\\libmgrs.cp312-win_amd64.pyd', '.')],
    datas=[],
    hiddenimports=['mgrs'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='assetmanager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='assetmanager',
)
