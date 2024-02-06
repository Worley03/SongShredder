# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['SongShredder.py'],
    pathex=[],
    binaries=[('ffmpeg-bin/', './')],
    datas=[('icon.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

to_exclude = {'opengl32sw.dll', 'Qt5DBus.dll', 'd3dcompiler_47.dll','Qt5Quick.dll','Qt5Qml.dll','libGLESv2.dll','libcrypto-1_1.dll','Qt5Network.dll','unicodedata.pyd','Qt5QmlModels.dll','Qt5Svg.dll','Qt5WebSockets.dll','libEGL.dll'}
a.binaries -= [(os.path.normcase(x), None, None) for x in to_exclude]
translation_path = os.path.join('PyQt5', 'Qt5', 'translations')
a.datas = [entry for entry in a.datas if not entry[0].startswith(translation_path)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SongShredder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
