"""
ConnectionHandlerBase — base class dùng chung cho Windows và Linux.
Chứa logic Add/Remove custom tunnel và Usage Guide skeleton.
"""

from core.logger import Logger, Color
from core.models import AppConfig, TunnelConfig, ConnectionType, MachineRole
from core.config_manager import ConfigManager


class ConnectionHandlerBase:

    # ── Custom tunnel management (giống hệt 2 OS) ─────────

    @staticmethod
    def add_custom_tunnel(cfg: AppConfig) -> None:
        print('\n--- Add Custom Port Forward ---')
        name = input('  Tunnel name           : ').strip() or 'custom'

        local_str = input('  Local port (MachineA) : ').strip()
        if not local_str.isdigit():
            Logger.warn('Invalid port.')
            return
        local = int(local_str)

        vps_str = input('  VPS relay port        : ').strip()
        if not vps_str.isdigit():
            Logger.warn('Invalid port.')
            return
        vps_port = int(vps_str)

        remote_str = input('  Remote port (MachineB): ').strip()
        if not remote_str.isdigit():
            Logger.warn('Invalid port.')
            return
        remote = int(remote_str)

        cfg.tunnels.append(TunnelConfig(
            name        = name,
            type        = ConnectionType.Custom,
            local_port  = local,
            vps_port    = vps_port,
            remote_port = remote,
        ))
        ConfigManager.save(cfg)
        Logger.success(f"Custom tunnel '{name}' added. Restart tunnels to apply.")

    @staticmethod
    def remove_tunnel(cfg: AppConfig) -> None:
        if not cfg.tunnels:
            print('No tunnels configured.')
            return

        print('\n--- Remove Tunnel ---')
        for i, t in enumerate(cfg.tunnels):
            print(f'  [{i + 1}] {t.name}')

        val = input('Select number to remove (0 = cancel): ').strip()
        if not val.isdigit():
            return
        idx = int(val)
        if idx < 1 or idx > len(cfg.tunnels):
            return

        removed = cfg.tunnels.pop(idx - 1)
        ConfigManager.save(cfg)
        Logger.success(f"Tunnel '{removed.name}' removed.")

    # ── Usage guide header/footer (dùng chung) ────────────

    @staticmethod
    def _print_header(cfg: AppConfig, os_label: str) -> None:
        sep = '  ' + '═' * 65
        print(f'\n{Color.CYAN}{sep}')
        print('  ║          HƯỚNG DẪN SỬ DỤNG SSH TUNNEL MANAGER              ║')
        print(f'{sep}{Color.RESET}')

        print(f'\n{Color.YELLOW}  📋 Session ID : "{cfg.session_id}"')
        role_label = (
            'Máy A — CLIENT (kết nối vào máy bạn bè)'
            if cfg.role == MachineRole.MachineA
            else 'Máy B — SERVER (máy đích, được kết nối vào)'
        )
        from core.config_manager import DEFAULT_VPS_HOST, DEFAULT_VPS_USERNAME
        from core.models import VpsMode
        vps = cfg.vps if cfg.vps_mode == VpsMode.Default else cfg.custom_vps
        print(f'  🖥  Vai trò    : {role_label}')
        print(f'  🌐 VPS        : {vps.username}@{vps.host}')
        print(f'  💻 OS         : {os_label}{Color.RESET}')

    @staticmethod
    def _print_troubleshooting(extra_lines: list = None) -> None:
        print(f'\n{Color.GRAY}  ' + '─' * 65)
        print('  ❓ XỬ LÝ SỰ CỐ THƯỜNG GẶP')
        print('  ' + '─' * 65)
        print(Color.RESET, end='')
        print('  • Tunnel DOWN liên tục         → Kiểm tra internet, VPS hoạt động không')
        print('  • connect_to localhost failed  → Máy B chưa bật SSH Server')
        if extra_lines:
            for line in extra_lines:
                print(f'  {line}')
        print()
        print(f'{Color.GRAY}  Nhấn Enter để quay lại menu...{Color.RESET}')
        input()
