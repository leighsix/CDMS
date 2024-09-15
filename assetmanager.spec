# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['assetmanager.py'],
    pathex=[],
    binaries=[('C:\\Users\\hyunc\\anaconda3\\envs\\myenv\\Lib\\site-packages\\libmgrs.cp38-win_amd64.pyd', '.')],
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
    a.binaries,
    a.datas,
    [],
    name='assetmanager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
