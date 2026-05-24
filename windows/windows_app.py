"""
WindowsApp — tương đương WindowsApp.cs
CLI menu shell cho Windows, dùng plink.exe.
"""

from core.app_base import AppBase
from core.logger import Logger, Color
from core.models import MachineRole
from windows.plink_wrapper import PlinkWrapper
from windows.connection_handler import WindowsConnectionHandler


class WindowsApp(AppBase):

    @property
    def _client_app_label(self) -> str:
        return 'Open PuTTY / RDP'

    def _print_banner(self) -> None:
        print(f'{Color.CYAN}')
        print('  ╔═══════════════════════════════════════════════════════╗')
        print('  ║         SSH Tunnel Manager  v2.0  (Windows)           ║')
        print('  ║   Connect two private-IP machines via VPS relay       ║')
        print(f'  ╚═══════════════════════════════════════════════════════╝{Color.RESET}')

    def _print_menu(self) -> None:
        self._print_menu_common()

    def _validate_tool(self) -> None:
        if not PlinkWrapper.validate_plink_path(self._cfg.plink_path):
            print(f"\n{Color.YELLOW}  ⚠  plink.exe not found at '{self._cfg.plink_path}'.")
            print(f"     Place plink.exe next to SshTunnelManager.exe.{Color.RESET}")

    def _print_usage_guide(self) -> None:
        WindowsConnectionHandler.print_tunnel_usage_guide(self._cfg)

    def _open_client_app(self) -> None:
        if self._cfg.role != MachineRole.MachineA:
            Logger.warn('This option is only available on Machine A (client side).')
            return
        print('\n  Open client app:')
        print('  [1] PuTTY  (SSH)')
        print('  [2] mstsc  (RDP)')
        choice = input('Choice: ').strip()
        if choice == '1':
            WindowsConnectionHandler.launch_putty(self._cfg)
        elif choice == '2':
            WindowsConnectionHandler.launch_rdp(self._cfg)
        else:
            print('  Cancelled.')
