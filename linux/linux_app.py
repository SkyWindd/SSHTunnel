"""
LinuxApp — tương đương LinuxApp.cs
CLI menu shell cho Linux, dùng ssh native.
"""

from core.app_base import AppBase
from core.logger import Logger, Color
from core.models import MachineRole
from linux.ssh_wrapper import SshWrapper
from linux.connection_handler import LinuxConnectionHandler


class LinuxApp(AppBase):

    @property
    def _client_app_label(self) -> str:
        return 'Open SSH / RDP'

    def _print_banner(self) -> None:
        print(f'{Color.CYAN}')
        print('  ╔═══════════════════════════════════════════════════════╗')
        print('  ║         SSH Tunnel Manager  v2.0  (Linux)             ║')
        print('  ║   Connect two private-IP machines via VPS relay       ║')
        print(f'  ╚═══════════════════════════════════════════════════════╝{Color.RESET}')

    def _print_menu(self) -> None:
        self._print_menu_common()

    def _validate_tool(self) -> None:
        if not SshWrapper.validate_ssh_path():
            print(f'{Color.RED}\n  ✘ Không tìm thấy ssh trên hệ thống.')
            print(f'    Cài: sudo apt install openssh-client{Color.RESET}')

    def _print_usage_guide(self) -> None:
        LinuxConnectionHandler.print_tunnel_usage_guide(self._cfg)

    def _open_client_app(self) -> None:
        if self._cfg.role != MachineRole.MachineA:
            Logger.warn('This option is only available on Machine A (client side).')
            return
        print('\n  Open client app:')
        print('  [1] SSH  (mở terminal với lệnh ssh)')
        print('  [2] RDP  (hướng dẫn Remmina / xfreerdp)')
        choice = input('Choice: ').strip()
        if choice == '1':
            LinuxConnectionHandler.print_ssh_command(self._cfg)
        elif choice == '2':
            LinuxConnectionHandler.print_rdp_guide(self._cfg)
        else:
            print('  Cancelled.')
