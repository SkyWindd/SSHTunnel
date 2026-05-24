"""
ConfigManager — tương đương ConfigManager.cs
Đọc/ghi config.json, chạy Setup Wizard, quản lý DefaultVpsProvider.
"""

import json
import platform
import getpass
from pathlib import Path
from typing import Optional

from core.logger import Logger, Color
from core.models import (
    AppConfig, VpsConfig, TunnelConfig,
    MachineRole, VpsMode, ConnectionType
)
from core.key_manager import KeyManager, KeyMode
from core.session_manager import SessionManager

CONFIG_FILE = 'config.json'

# Default AWS VPS info
DEFAULT_VPS_HOST     = '13.229.239.111'
DEFAULT_VPS_PORT     = 22
DEFAULT_VPS_USERNAME = 'ubuntu'


# ── DefaultVpsProvider — tương đương C# ───────────────────

class DefaultVpsProvider:
    _unlocked:     bool  = False
    _temp_key_path: str  = ''

    @classmethod
    def is_unlocked(cls) -> bool:
        return cls._unlocked

    @classmethod
    def unlock_with_password(cls, password: str) -> bool:
        """Giải mã key bằng password, ghi ra file tạm."""
        try:
            key_bytes = KeyManager.decrypt_to_memory(password)
            cls._temp_key_path = KeyManager.write_temp_key(key_bytes)
            cls._unlocked = True
            Logger.success('Key đã được giải mã thành công.')
            return True
        except PermissionError:
            return False
        except Exception as e:
            Logger.error(f'Lỗi giải mã: {e}')
            return False

    @classmethod
    def get_vps_config(cls) -> VpsConfig:
        """Trả về VpsConfig với đường dẫn key đúng."""
        key_path = cls._temp_key_path if cls._temp_key_path else KeyManager.resolve_key_path()
        return VpsConfig(
            host         = DEFAULT_VPS_HOST,
            port         = DEFAULT_VPS_PORT,
            username     = DEFAULT_VPS_USERNAME,
            ssh_key_file = key_path,
        )

    @classmethod
    def cleanup(cls) -> None:
        """Xóa file key tạm khi thoát app."""
        if cls._temp_key_path:
            KeyManager.delete_temp_key(cls._temp_key_path)
            cls._temp_key_path = ''


# ── ConfigManager ──────────────────────────────────────────

class ConfigManager:

    @staticmethod
    def _config_path() -> Path:
        return KeyManager.app_dir() / CONFIG_FILE

    @staticmethod
    def load() -> AppConfig:
        """
        Load config từ file. Nếu chưa có → chạy Setup Wizard.
        """
        path = ConfigManager._config_path()
        if not path.exists():
            Logger.info('Config chưa có — chạy Setup Wizard...')
            return ConfigManager.run_setup_wizard()

        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            cfg  = ConfigManager._from_dict(data)
            Logger.info(f'Config loaded (session: "{cfg.session_id}", role: {cfg.role.name}, vps: {cfg.vps_mode.name})')
            return cfg
        except Exception as e:
            Logger.error(f'Lỗi đọc config: {e} — chạy Setup Wizard...')
            return ConfigManager.run_setup_wizard()

    @staticmethod
    def save(cfg: AppConfig) -> None:
        """Ghi config ra file JSON."""
        path = ConfigManager._config_path()
        try:
            path.write_text(
                json.dumps(ConfigManager._to_dict(cfg), indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            Logger.info(f"Config saved to '{CONFIG_FILE}'")
        except Exception as e:
            Logger.error(f'Lỗi ghi config: {e}')

    @staticmethod
    def run_setup_wizard() -> AppConfig:
        """
        Setup Wizard — tương đương C# RunSetupWizard().
        Hỏi user từng bước, trả về AppConfig đã setup.
        """
        print(f'\n{Color.CYAN}  ╔══════════════════════════════════════════════════╗')
        print(  '  ║        SSH Tunnel Manager — Setup Wizard         ║')
        print(  f'  ╚══════════════════════════════════════════════════╝{Color.RESET}')

        cfg = AppConfig()

        # ── Bước 1: Chọn Role ─────────────────────────────
        print('\n  Role of THIS machine:')
        print('  [A] Machine A — Client (opens PuTTY/RDP to remote)')
        print('  [B] Machine B — Server (the machine you want to reach)')
        while True:
            choice = input('  Choice [A/B]: ').strip().upper()
            if choice == 'A':
                cfg.role = MachineRole.MachineA
                break
            elif choice == 'B':
                cfg.role = MachineRole.MachineB
                break
            print('  Please enter A or B.')

        # ── Bước 2: Session ID ────────────────────────────
        print('\n  Session ID — a short name shared between Machine A and B.')
        print('  Examples: nhom1, alice-bob, dev-team')
        print('  Rules: 3–32 chars, letters/numbers/dash/underscore only.')
        while True:
            session_id = input('  Session ID: ').strip()
            if SessionManager.is_valid(session_id):
                cfg.session_id = session_id
                break
            print('  Invalid Session ID. Use 3-32 chars, letters/numbers/dash/underscore.')

        SessionManager.print_session_info(cfg.session_id)

        # ── Bước 3: VPS Mode ──────────────────────────────
        print('\n  VPS Mode:')
        print('  [1] Default VPS (AWS — built-in, free)')
        print('  [2] Custom VPS  (your own VPS)')
        while True:
            choice = input('  Choice [1/2]: ').strip()
            if choice == '1':
                cfg.vps_mode = VpsMode.Default
                print(f'  Default VPS : {DEFAULT_VPS_USERNAME}@{DEFAULT_VPS_HOST}:{DEFAULT_VPS_PORT}')
                break
            elif choice == '2':
                cfg.vps_mode = VpsMode.Custom
                cfg.custom_vps = ConfigManager._ask_custom_vps()
                break
            print('  Please enter 1 or 2.')

        # ── Bước 4: Key unlock (Default VPS) ─────────────
        if cfg.vps_mode == VpsMode.Default:
            ConfigManager._handle_key_setup()

        # ── Bước 5: Plink path (Windows only) ────────────
        if platform.system() == 'Windows':
            default_plink = 'plink.exe'
            val = input(f'\n  Path to plink.exe [{default_plink}]: ').strip()
            cfg.plink_path = val if val else default_plink

        # ── Bước 6: Auto-reconnect ────────────────────────
        val = input('\n  Enable auto-reconnect? (Y/n): ').strip().lower()
        cfg.auto_reconnect = val != 'n'

        # ── Tạo tunnels từ session ID ─────────────────────
        cfg.tunnels = ConfigManager._build_tunnels(cfg.session_id)

        ConfigManager.save(cfg)
        print(f'\n{Color.GREEN}  ✔  Configuration saved.{Color.RESET}')

        return cfg

    # ── Private helpers ────────────────────────────────────

    @staticmethod
    def _handle_key_setup() -> None:
        """Xử lý key: detect mode rồi unlock hoặc hướng dẫn."""
        KeyManager.print_key_status()
        mode = KeyManager.detect_mode()

        if mode == KeyMode.Encrypted:
            # Hỏi Group Password
            print(f'\n{Color.CYAN}  🔐 Nhập Group Password để mở khóa key VPS:{Color.RESET}')
            for attempt in range(1, 4):
                password = ConfigManager._read_password(f'  Group Password (lần {attempt}/3): ')
                if DefaultVpsProvider.unlock_with_password(password):
                    print(f'{Color.GREEN}  ✔  Mở khóa thành công!{Color.RESET}')
                    return
                if attempt < 3:
                    print(f'{Color.RED}  ✘  Sai mật khẩu, thử lại...{Color.RESET}')
            print(f'{Color.RED}  ✘  Sai mật khẩu 3 lần.{Color.RESET}')

        elif mode == KeyMode.Plain:
            if platform.system() != 'Windows':
                # Linux: có .pem → dùng thẳng
                Logger.info('Dùng file key .pem trực tiếp.')
            else:
                # Windows: có .ppk → hỏi đặt password mã hóa
                print(f'\n{Color.YELLOW}  ℹ  Phát hiện file key chưa mã hóa.')
                print('     Hãy đặt Group Password để mã hóa key ngay bây giờ.')
                print(f'     Password này dùng chung cho cả nhóm.{Color.RESET}')
                password = ConfigManager._set_group_password_interactive()
                if password:
                    try:
                        KeyManager.encrypt_plain_key(password)
                        DefaultVpsProvider.unlock_with_password(password)
                        print(f'{Color.GREEN}  ✔  Key đã mã hóa và mở khóa thành công!{Color.RESET}')
                        print(f'{Color.YELLOW}  ⚠  Hãy XÓA file \'default_vps.ppk\' gốc sau khi setup xong.{Color.RESET}')
                    except Exception as e:
                        Logger.error(f'Mã hóa thất bại: {e}')

        elif mode == KeyMode.Missing:
            plain_name = 'default_vps.pem' if platform.system() != 'Windows' else 'default_vps.ppk'
            print(f'{Color.YELLOW}  ⚠  Không tìm thấy file key .pem.')
            print(f'     Đặt file \'{plain_name}\' cạnh SshTunnelManager.')
            if platform.system() != 'Windows':
                print('     Nếu chỉ có file .ppk, convert bằng lệnh:')
                print('     puttygen default_vps.ppk -O private-openssh -o default_vps.pem')
            print(f'{Color.RESET}')

    @staticmethod
    def _ask_custom_vps() -> VpsConfig:
        """Hỏi thông tin Custom VPS."""
        print('\n  Custom VPS configuration:')
        host     = input('  Host (IP or domain): ').strip()
        port_str = input('  Port [22]: ').strip()
        port     = int(port_str) if port_str.isdigit() else 22
        username = input('  Username [root]: ').strip() or 'root'
        key_file = input('  SSH key file path (leave blank for password): ').strip()
        password = ''
        if not key_file:
            password = ConfigManager._read_password('  Password: ')
        return VpsConfig(
            host         = host,
            port         = port,
            username     = username,
            password     = password,
            ssh_key_file = key_file,
        )

    @staticmethod
    def _build_tunnels(session_id: str) -> list:
        """Tạo danh sách tunnel từ session ID."""
        ports = SessionManager.get_session_ports(session_id)
        return [
            TunnelConfig(
                name        = 'SSH',
                type        = ConnectionType.SSH,
                local_port  = ports.ssh_port,
                remote_port = 22,
                vps_port    = ports.ssh_port,
            ),
            TunnelConfig(
                name        = 'RDP',
                type        = ConnectionType.RDP,
                local_port  = ports.rdp_port,
                remote_port = 3389,
                vps_port    = ports.rdp_port,
            ),
        ]

    @staticmethod
    def _set_group_password_interactive() -> str:
        """Hỏi và xác nhận group password mới."""
        print('\n  Đặt Group Password cho nhóm của bạn:')
        print('  Password này dùng chung cho cả nhóm — thông báo qua Zalo/gặp trực tiếp.')
        while True:
            pwd = ConfigManager._read_password('  Nhập Group Password  : ')
            if len(pwd) < 6:
                print(f'{Color.RED}  ✘ Password phải có ít nhất 6 ký tự.{Color.RESET}')
                continue
            confirm = ConfigManager._read_password('  Xác nhận lại         : ')
            if pwd == confirm:
                return pwd
            print(f'{Color.RED}  ✘ Hai lần nhập không khớp, thử lại.{Color.RESET}')

    @staticmethod
    def _read_password(prompt: str) -> str:
        """Đọc password ẩn ký tự."""
        return getpass.getpass(prompt)

    # ── Serialization ──────────────────────────────────────

    @staticmethod
    def _to_dict(cfg: AppConfig) -> dict:
        return {
            'Role':     cfg.role.value,
            'VpsMode':  cfg.vps_mode.value,
            'SessionId': cfg.session_id,
            'CustomVps': {
                'Host':       cfg.custom_vps.host,
                'Port':       cfg.custom_vps.port,
                'Username':   cfg.custom_vps.username,
                'Password':   cfg.custom_vps.password,
                'SshKeyFile': cfg.custom_vps.ssh_key_file,
            },
            'Tunnels': [
                {
                    'Name':       t.name,
                    'Type':       t.type.value,
                    'LocalPort':  t.local_port,
                    'RemotePort': t.remote_port,
                    'VpsPort':    t.vps_port,
                }
                for t in cfg.tunnels
            ],
            'PlinkPath':          cfg.plink_path,
            'HeartbeatIntervalSec': cfg.heartbeat_interval,
            'ReconnectDelaySec':  cfg.reconnect_delay,
            'AutoReconnect':      cfg.auto_reconnect,
        }

    @staticmethod
    def _from_dict(data: dict) -> AppConfig:
        cfg = AppConfig()
        cfg.role           = MachineRole(data.get('Role', 0))
        cfg.vps_mode       = VpsMode(data.get('VpsMode', 0))
        cfg.session_id     = data.get('SessionId', '')
        cfg.plink_path     = data.get('PlinkPath', 'plink.exe')
        cfg.heartbeat_interval = data.get('HeartbeatIntervalSec', 15)
        cfg.reconnect_delay    = data.get('ReconnectDelaySec', 5)
        cfg.auto_reconnect     = data.get('AutoReconnect', True)

        vps_data = data.get('CustomVps', {})
        cfg.custom_vps = VpsConfig(
            host         = vps_data.get('Host', ''),
            port         = vps_data.get('Port', 22),
            username     = vps_data.get('Username', ''),
            password     = vps_data.get('Password', ''),
            ssh_key_file = vps_data.get('SshKeyFile', ''),
        )

        cfg.tunnels = [
            TunnelConfig(
                name        = t.get('Name', 'custom'),
                type        = ConnectionType(t.get('Type', 0)),
                local_port  = t.get('LocalPort', 0),
                remote_port = t.get('RemotePort', 0),
                vps_port    = t.get('VpsPort', 0),
            )
            for t in data.get('Tunnels', [])
        ]

        return cfg
