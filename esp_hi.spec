# -*- mode: python ; coding: utf-8 -*-

# 编译：pyinstaller esp_hi.spec

block_cipher = None

# 添加的数据文件和资源
added_files = [
    ('frontend', 'frontend'),
    ('backend/devices.json', 'backend'),
]

# 主程序配置
a = Analysis(
    ['backend/app.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'flask',
        'flask_cors',
        'flask_socketio',
        'socketio',
        'engineio',
        'engineio.async_drivers.threading',
        'eventlet',
        'eventlet.greenio',
        'eventlet.green',
        'requests',
        'urllib3',
        'device_manager',
        'scanner_service',
        'calibration_service',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 可执行文件配置
exec = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ESP_HI_Control',
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
    icon='图标.ico'
)
