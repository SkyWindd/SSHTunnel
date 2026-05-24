"""
WindowsConnectionHandler — tương đương ConnectionHandler.cs
Mở PuTTY, mstsc và hiển thị usage guide cho Windows.
"""

import subprocess
from core.connection_handler_base import ConnectionHandlerBase
from core.models import AppConfig, MachineRole, ConnectionType
from core.logger import Logger, Color


class WindowsConnectionHandler(ConnectionHandlerBase):

    # ── Launch helpers ─────────────────────────────────────

    @staticmethod
    def launch_putty(cfg: AppConfig) -> None:
        ssh = next((t for t in cfg.tunnels if t.type == ConnectionType.SSH), None)
        if not ssh:
            Logger.warn('No SSH tunnel configured.')
            return
        WindowsConnectionHandler._launch_app(
            exe   = 'putty.exe',
            args  = [f'-P', str(ssh.local_port), '127.0.0.1'],
            label = 'PuTTY',
            msg   = f'Connect PuTTY to localhost:{ssh.local_port}',
        )

    @staticmethod
    def launch_rdp(cfg: AppConfig) -> None:
        rdp = next((t for t in cfg.tunnels if t.type == ConnectionType.RDP), None)
        if not rdp:
            Logger.warn('No RDP tunnel configured.')
            return
        WindowsConnectionHandler._launch_app(
            exe   = 'mstsc',
            args  = [f'/v:127.0.0.1:{rdp.local_port}'],
            label = 'mstsc (RDP)',
            msg   = f'Connect RDP to localhost:{rdp.local_port}',
        )

    @staticmethod
    def _launch_app(exe: str, args: list, label: str, msg: str) -> None:
        Logger.info(msg)
        try:
            subprocess.Popen([exe] + args, shell=True)
            Logger.success(f'{label} launched.')
        except Exception as e:
            Logger.error(f'Cannot launch {label}: {e}')

    # ── Usage guide ────────────────────────────────────────

    @staticmethod
    def print_tunnel_usage_guide(cfg: AppConfig) -> None:
        import os; os.system('cls' if os.name == 'nt' else 'clear')

        WindowsConnectionHandler._print_header(cfg, 'Windows')

        if cfg.role == MachineRole.MachineB:
            WindowsConnectionHandler._print_guide_machine_b(cfg)
        else:
            WindowsConnectionHandler._print_guide_machine_a(cfg)

        WindowsConnectionHandler._print_troubleshooting([
            "• PuTTY 'Connection refused'  → Máy B chưa bật OpenSSH Server",
            "      Start-Service sshd  (PowerShell Admin)",
            "• 'Access denied'             → Sai username/password Windows của Máy B",
            "• Host key warning            → Chạy plink.exe thủ công 1 lần để accept key",
        ])

    @staticmethod
    def _print_guide_machine_b(cfg: AppConfig) -> None:
        print(f'\n{Color.GREEN}  ' + '─' * 65)
        print('  ✅ NHIỆM VỤ CỦA MÁY B (máy này)')
        print('  ' + '─' * 65 + Color.RESET)
        print('\n  Máy B đẩy Reverse Tunnel lên VPS để Máy A có thể kết nối vào.')
        print('  Bạn CHỈ CẦN giữ app này đang chạy — không cần làm gì thêm.\n')

        for t in cfg.tunnels:
            print(f'\n{Color.CYAN}    [{t.name}]{Color.RESET} Máy này (port {t.remote_port}) → VPS relay port {t.vps_port}')
            if t.type == ConnectionType.SSH:
                print('           Máy A sẽ SSH vào cổng này để điều khiển máy bạn')
            elif t.type == ConnectionType.RDP:
                print('           Máy A sẽ Remote Desktop vào cổng này')
            else:
                print('           Máy A sẽ kết nối ứng dụng tùy chỉnh vào cổng này')

        print(f'\n{Color.YELLOW}  ⚠  YÊU CẦU TRÊN MÁY B (Windows):')
        print('    • OpenSSH Server phải đang chạy:')
        print('      Kiểm tra: Get-Service sshd  (phải thấy Running)')
        print('      Bật:      Start-Service sshd  (PowerShell Admin)')
        print('    • Tường lửa Windows phải cho phép port 22')
        print(f'    • Máy B phải có username + password{Color.RESET}')
        print(f'\n{Color.CYAN}  ℹ  Chia sẻ cho Máy A:')
        print(f'    Session ID : {cfg.session_id}')
        print('    Username   : (username Windows của máy này)')
        print(f'    Password   : (password Windows của máy này){Color.RESET}')

    @staticmethod
    def _print_guide_machine_a(cfg: AppConfig) -> None:
        print(f'\n{Color.GREEN}  ' + '─' * 65)
        print('  ✅ CÁCH KẾT NỐI TỪ MÁY A (máy này — Windows)')
        print('  ' + '─' * 65 + Color.RESET)
        print('\n  Các cổng local dưới đây được forward xuyên VPS tới Máy B:\n')

        for t in cfg.tunnels:
            bar = '─' * (48 - len(t.name))
            print(f'{Color.CYAN}  ┌─── [{t.name}] {bar}┐{Color.RESET}')
            print(f'  │  Luồng: localhost:{t.local_port} → VPS:{t.vps_port} → MáyB:{t.remote_port}')

            if t.type == ConnectionType.SSH:
                print('  │')
                print('  │  Cách kết nối bằng PuTTY:')
                print('  │    1. Mở PuTTY')
                print('  │    2. Host Name : 127.0.0.1')
                print(f'  │    3. Port      : {t.local_port}')
                print('  │    4. Connection type: SSH')
                print('  │    5. Click Open → đăng nhập bằng user/pass Windows của Máy B')
                print('  │')
                print('  │  Hoặc chọn [5] → [1] trong menu để mở PuTTY tự động')
            elif t.type == ConnectionType.RDP:
                print('  │')
                print('  │  Cách kết nối bằng Remote Desktop:')
                print('  │    1. Nhấn Win+R → gõ: mstsc')
                print(f'  │    2. Computer: 127.0.0.1:{t.local_port}')
                print('  │    3. Click Connect → đăng nhập user/pass Windows Máy B')
                print('  │')
                print('  │  Hoặc chọn [5] → [2] trong menu để mở mstsc tự động')
            else:
                print(f'  │  Kết nối tới: localhost:{t.local_port}')

            print(f'{Color.CYAN}  └' + '─' * 62 + f'┘{Color.RESET}\n')

        print(f'{Color.YELLOW}  ⚠  ĐIỀU KIỆN KẾT NỐI THÀNH CÔNG:')
        print(f'    • Máy B RUNNING với Session ID: "{cfg.session_id}"')
        print('    • Máy A (máy này) phải đang RUNNING')
        print(f'    • Cả 2 máy dùng cùng Session ID: "{cfg.session_id}"{Color.RESET}')
