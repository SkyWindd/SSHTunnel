"""
AppBase — base class dùng chung cho WindowsApp và LinuxApp.
"""

import signal
import sys
import getpass
import os
from abc import ABC, abstractmethod

from core.logger import Logger, Color
from core.models import AppConfig, MachineRole, VpsMode
from core.config_manager import ConfigManager, DefaultVpsProvider
from core.tunnel_monitor import TunnelMonitor
from core.key_manager import KeyManager, KeyMode
from core.connection_handler_base import ConnectionHandlerBase


class AppBase(ABC):

    def __init__(self):
        self._cfg: AppConfig = None
        self._monitor: TunnelMonitor = None

    def run(self, args: list) -> None:
        signal.signal(signal.SIGINT, self._handle_sigint)
        self._print_banner()

        if '--setup' in args:
            self._cfg = ConfigManager.run_setup_wizard()
        else:
            self._cfg = ConfigManager.load()

        if '--encrypt-key' in args:
            self._run_encrypt_key_tool()
            return

        self._validate_tool()

        if self._cfg.vps_mode == VpsMode.Default and not DefaultVpsProvider.is_unlocked():
            self._handle_key_unlock()

        self._monitor = TunnelMonitor(self._cfg)
        self._run_menu()
        self._shutdown()

    def _run_menu(self) -> None:
        while True:
            self._print_menu()
            choice = input('Choice: ').strip().lower()
            if choice == '1':   self._start_tunnels()
            elif choice == '2': self._stop_tunnels()
            elif choice == '3': self._monitor.print_status()
            elif choice == '4': self._print_usage_guide()
            elif choice == '5': self._open_client_app()
            elif choice == '6': self._manage_custom_tunnels()
            elif choice == '7': self._show_log()
            elif choice == '8': self._run_setup()
            elif choice == '9': self._toggle_auto_reconnect()
            elif choice in ('0', 'q', 'quit', 'exit'): break
            else: print('  Unknown option — try again.')

    def _start_tunnels(self) -> None:
        if self._monitor.is_running:
            Logger.warn('Tunnels already running. Stop them first (option 2).')
            return
        self._monitor.start_all()
        Logger.success('All tunnels started. Use option 3 to check status.')

    def _stop_tunnels(self) -> None:
        if not self._monitor.is_running:
            Logger.warn('No tunnels running.')
            return
        self._monitor.stop_all()
        Logger.success('All tunnels stopped.')

    def _manage_custom_tunnels(self) -> None:
        print('\n  Custom tunnel management:')
        print('  [1] Add new custom port forward')
        print('  [2] Remove a tunnel')
        choice = input('Choice: ').strip()
        if choice == '1':   ConnectionHandlerBase.add_custom_tunnel(self._cfg)
        elif choice == '2': ConnectionHandlerBase.remove_tunnel(self._cfg)
        else:               print('  Cancelled.')

    def _show_log(self) -> None:
        val = input('Show last how many lines? [30]: ').strip()
        Logger.print_last_lines(int(val) if val.isdigit() else 30)

    def _run_setup(self) -> None:
        if self._monitor.is_running:
            if input('Tunnels are running. Stop them first? (y/N): ').strip().lower() != 'y':
                return
            self._monitor.stop_all()
        self._cfg     = ConfigManager.run_setup_wizard()
        self._monitor = TunnelMonitor(self._cfg)

    def _toggle_auto_reconnect(self) -> None:
        self._cfg.auto_reconnect = not self._cfg.auto_reconnect
        ConfigManager.save(self._cfg)
        Logger.info(f'AutoReconnect is now: {"ON" if self._cfg.auto_reconnect else "OFF"}')

    def _shutdown(self) -> None:
        if self._monitor and self._monitor.is_running:
            Logger.info('Stopping all tunnels on exit...')
            self._monitor.stop_all()
        DefaultVpsProvider.cleanup()

    def _handle_sigint(self, sig, frame) -> None:
        Logger.warn('Ctrl+C received — shutting down...')
        self._shutdown()
        sys.exit(0)

    def _handle_key_unlock(self) -> None:
        mode = KeyManager.detect_mode()
        if mode == KeyMode.Encrypted:
            self._unlock_key_interactive()
        elif mode == KeyMode.Plain:
            import platform
            if platform.system() != 'Windows':
                Logger.info('Dùng file key .pem trực tiếp.')
            else:
                print(f'{Color.YELLOW}\n  ⚠  File key chưa mã hóa.{Color.RESET}')
        elif mode == KeyMode.Missing:
            print(f'{Color.RED}\n  ✘ Không tìm thấy file key VPS.{Color.RESET}')

    def _unlock_key_interactive(self) -> None:
        print(f'\n{Color.CYAN}  🔐 Key VPS đã được mã hóa — cần nhập Group Password.{Color.RESET}')
        for attempt in range(1, 4):
            password = getpass.getpass(f'  Nhập Group Password (lần {attempt}/3): ')
            if DefaultVpsProvider.unlock_with_password(password):
                print(f'{Color.GREEN}  ✔  Key đã được mở khóa thành công!\n{Color.RESET}')
                return
            if attempt < 3:
                print(f'{Color.RED}  ✘  Sai mật khẩu, thử lại...{Color.RESET}')
        print(f'{Color.RED}\n  ✘  Sai mật khẩu 3 lần.{Color.RESET}')

    def _run_encrypt_key_tool(self) -> None:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f'{Color.CYAN}  ╔══════════════════════════════════════════════════╗')
        print(  '  ║         Công cụ Mã hóa File Key VPS             ║')
        print(  f'  ╚══════════════════════════════════════════════════╝\n{Color.RESET}')

        mode = KeyManager.detect_mode()
        if mode == KeyMode.Missing:
            print(f"{Color.RED}  ✘ Không tìm thấy file key cần mã hóa.{Color.RESET}")
            input()
            return
        if mode == KeyMode.Encrypted:
            print(f'{Color.YELLOW}  ℹ  File đã tồn tại.{Color.RESET}')
            if input('     Mã hóa lại? (y/N): ').strip().lower() != 'y':
                return

        while True:
            pwd = getpass.getpass('  Nhập Group Password  : ')
            if len(pwd) < 6:
                print(f'{Color.RED}  ✘ Password phải có ít nhất 6 ký tự.{Color.RESET}')
                continue
            if getpass.getpass('  Xác nhận lại         : ') == pwd:
                break
            print(f'{Color.RED}  ✘ Hai lần nhập không khớp.{Color.RESET}')

        try:
            import platform
            if platform.system() != 'Windows':
                KeyManager.encrypt_plain_key_linux(pwd)
                plain_name = 'default_vps.pem'
                enc_name   = 'default_vps.pem.enc'
            else:
                KeyManager.encrypt_plain_key(pwd)
                plain_name = 'default_vps.ppk'
                enc_name   = 'default_vps.ppk.enc'
            print(f'{Color.GREEN}\n  ✔  Mã hóa thành công!{Color.RESET}')
            print(f"{Color.YELLOW}  ⚠  XÓA file '{plain_name}' gốc.")
            print(f"     Chỉ giữ lại '{enc_name}' — an toàn khi upload GitHub.{Color.RESET}")
        except Exception as e:
            Logger.error(f'Mã hóa thất bại: {e}')
        input('\n  Nhấn Enter để thoát...')

    def _print_menu_common(self) -> None:
        """In header status + menu items dùng chung cho Windows và Linux."""
        running = self._monitor and self._monitor.is_running
        status  = '● RUNNING' if running else '○ STOPPED'
        color   = Color.GREEN if running else Color.RED
        vps_tag = 'Default AWS' if self._cfg.vps_mode == VpsMode.Default else f'Custom ({self._cfg.vps.host})'
        session = f'"{self._cfg.session_id}"' if self._cfg.session_id else '(none)'

        print(f'\n{Color.GRAY}  ┌─────────────────────────────────────────────────────┐')
        print(f'  │  {color}{status:<10}{Color.GRAY}  Role: {self._cfg.role.name:<10}  Session: {session:<14}│')
        print(f'  │  VPS: {vps_tag:<46}│')
        print(f'  └─────────────────────────────────────────────────────┘{Color.RESET}')
        print('  [1] Start tunnels')
        print('  [2] Stop tunnels')
        print('  [3] Status / liveness')
        print('  [4] Usage guide (how to connect)')
        if self._cfg.role == MachineRole.MachineA:
            print(f'  [5] {self._client_app_label}')
        print('  [6] Manage custom port forwards')
        print('  [7] View log')
        print('  [8] Setup wizard (change session / VPS / role)')
        print(f'  [9] Toggle auto-reconnect (currently: {"ON" if self._cfg.auto_reconnect else "OFF"})')
        print('  [0] Quit')

    @property
    @abstractmethod
    def _client_app_label(self) -> str: ...

    @abstractmethod
    def _print_banner(self) -> None: ...

    @abstractmethod
    def _print_menu(self) -> None: ...

    @abstractmethod
    def _validate_tool(self) -> None: ...

    @abstractmethod
    def _print_usage_guide(self) -> None: ...

    @abstractmethod
    def _open_client_app(self) -> None: ...
