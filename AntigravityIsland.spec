# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('island', 'island')],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32', 'mss', 'win32com.client', 'pythoncom', 'island.brain', 'island.voice', 'island.agy_daemon', 'island.window_manager', 'island.notifications', 'island.logos', 'island.notification_manager', 'sounddevice', 'numpy', 'pycaw', 'comtypes', 'psutil', 'edge_tts', 'aiohttp', 'speech_recognition'],
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
    name='AntigravityIsland',
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
    icon=['assets/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AntigravityIsland',
)
