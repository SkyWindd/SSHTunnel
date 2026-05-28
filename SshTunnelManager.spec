# -*- mode: python ; coding: utf-8 -*-
# SshTunnelManager.spec — PyInstaller build config
# Dùng chung cho cả Windows và Linux

import platform
import sys

# Tên output binary
app_name = 'SshTunnelManager'

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # cryptography
        'cryptography',
        'cryptography.hazmat.primitives.ciphers.aead',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        # app modules
        'core.logger',
        'core.models',
        'core.session_manager',
        'core.key_manager',
        'core.config_manager',
        'core.tunnel_process',
        'core.tunnel_monitor',
        'core.connection_handler_base',
        'core.app_base',
        'windows.plink_wrapper',
        'windows.connection_handler',
        'windows.windows_app',
        'linux.ssh_wrapper',
        'linux.connection_handler',
        'linux.linux_app',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Loại bỏ các module không cần thiết để giảm kích thước
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'PyQt5',
        'wx',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # Nén binary để giảm kích thước
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # App chạy trong terminal (không phải GUI)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows only: icon (bỏ comment nếu có file .ico)
    # icon='icon.ico',
)
