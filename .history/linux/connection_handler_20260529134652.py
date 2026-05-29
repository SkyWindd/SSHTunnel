"""
LinuxConnectionHandler — tương đương LinuxConnectionHandler.cs
SSH command trực tiếp trong terminal, hướng dẫn Remmina/xfreerdp.
"""

import subprocess
from core.connection_handler_base import ConnectionHandlerBase
from core.models import AppConfig, MachineRole, ConnectionType
from core.logger import Logger, Color


class LinuxConnectionHandler(ConnectionHandlerBase):

    # ── Launch helpers ─────────────────────────────────────

    @staticmethod
    def print_ssh_command(cfg: AppConfig) -> None:
        ssh = next((t for t in cfg.tunnels if t.type == ConnectionType.SSH), None)
        if not ssh:
            Logger.warn('No SSH tunnel configured.')
            return

        print(f'\n{Color.CYAN}  Kết nối SSH vào Máy B qua tunnel:{Color.RESET}')
        username = input('  Nhập username Máy B (Enter để hủy): ').strip()

        if not username:
            print('  Đã hủy. Lệnh để tự chạy:')
            print(f'{Color.CYAN}    ssh <username>@127.0.0.1 -p {ssh.local_port}{Color.RESET}')
            return

        print(f'\n{Color.YELLOW}  Đang kết nối: ssh {username}@127.0.0.1 -p {ssh.local_port}')
        print(f'  (Nhấn Ctrl+D hoặc gõ exit để quay lại app){Color.RESET}\n')

        try:
            proc = subprocess.Popen(
    ['ssh', f'{username}@127.0.0.1', '-p', str(ssh.local_port),
     '-o', 'StrictHostKeyChecking=no',
     '-o', 'UserKnownHostsFile=/dev/null'],
                stdin=None,
                stdout=None,
                stderr=None,
            )
            proc.wait()
            print('\n  SSH session đã kết thúc. Quay lại menu...')
        except Exception as e:
            Logger.error(f'Không thể chạy ssh: {e}')
            print(f'{Color.CYAN}  Tự chạy lệnh: ssh {username}@127.0.0.1 -p {ssh.local_port}{Color.RESET}')

    @staticmethod
    def print_rdp_guide(cfg: AppConfig) -> None:
        rdp = next((t for t in cfg.tunnels if t.type == ConnectionType.RDP), None)
        if not rdp:
            Logger.warn('No RDP tunnel configured.')
            return

        print(f'\n{Color.CYAN}  Kết nối Remote Desktop từ Linux:{Color.RESET}')
        print(f'\n  Cách 1 — Remmina (GUI):')
        print(f'    sudo apt install remmina')
        print(f'    Protocol: RDP  |  Server: 127.0.0.1:{rdp.local_port}')
        print(f'\n  Cách 2 — xfreerdp (command line):')
        print(f'    sudo apt install freerdp2-x11')
        print(f'{Color.CYAN}    xfreerdp /v:127.0.0.1:{rdp.local_port} /u:<username_may_b>{Color.RESET}')
        print(f'\n  Lưu ý: Máy B phải bật Remote Desktop (Windows Pro/Enterprise).')
        print(f'         Nếu Máy B dùng Windows Home → dùng VNC thay thế.')

    # ── Usage guide ────────────────────────────────────────

    @staticmethod
    def print_tunnel_usage_guide(cfg: AppConfig) -> None:
        import os; os.system('clear')

        LinuxConnectionHandler._print_header(cfg, 'Linux')

        if cfg.role == MachineRole.MachineB:
            LinuxConnectionHandler._print_guide_machine_b(cfg)
        else:
            LinuxConnectionHandler._print_guide_machine_a(cfg)

        LinuxConnectionHandler._print_troubleshooting([
            "• 'connect_to localhost failed'→ Máy B chưa bật SSH Server:",
            "      Linux:   sudo service ssh start",
            "      Windows: Start-Service sshd (PowerShell Admin)",
            "• 'Permission denied'          → Sai username/password hoặc sai file .pem",
            "• 'Bad permissions'            → chmod 600 default_vps.pem",
            "• 'Host key verification'      → ssh-keygen -R 127.0.0.1",
            "• CRLF error (.sh files)       → sed -i 's/\\r//' run.sh build.sh",
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
                print('           Máy A sẽ Remote Desktop / VNC vào cổng này')
            else:
                print('           Máy A sẽ kết nối ứng dụng tùy chỉnh vào cổng này')

        print(f'\n{Color.YELLOW}  ⚠  YÊU CẦU TRÊN MÁY B (Linux):')
        print('    • OpenSSH Server phải đang chạy:')
        print('      Kiểm tra: sudo service ssh status')
        print('      Bật:      sudo service ssh start')
        print('    • Firewall phải cho phép port 22: sudo ufw allow 22')
        print(f'    • File key .pem phải có permission 600: chmod 600 default_vps.pem{Color.RESET}')
        print(f'\n{Color.CYAN}  ℹ  Chia sẻ cho Máy A:')
        print(f'    Session ID : {cfg.session_id}')
        print('    Username   : (username Linux — chạy: whoami)')
        print(f'    Password   : (password Linux của máy này){Color.RESET}')

    @staticmethod
    def _print_guide_machine_a(cfg: AppConfig) -> None:
        print(f'\n{Color.GREEN}  ' + '─' * 65)
        print('  ✅ CÁCH KẾT NỐI TỪ MÁY A (máy này — Linux)')
        print('  ' + '─' * 65 + Color.RESET)
        print('\n  Các cổng local dưới đây được forward xuyên VPS tới Máy B:\n')

        for t in cfg.tunnels:
            bar = '─' * (48 - len(t.name))
            print(f'{Color.CYAN}  ┌─── [{t.name}] {bar}┐{Color.RESET}')
            print(f'  │  Luồng: localhost:{t.local_port} → VPS:{t.vps_port} → MáyB:{t.remote_port}')

            if t.type == ConnectionType.SSH:
                print('  │')
                print('  │  Cách kết nối bằng ssh:')
                print(f'{Color.CYAN}  │    ssh <username_may_b>@127.0.0.1 -p {t.local_port}{Color.RESET}')
                print('  │')
                print('  │  Hoặc chọn [5] → [1] trong menu để kết nối tự động')
            elif t.type == ConnectionType.RDP:
                print('  │')
                print('  │  Cách kết nối bằng Remmina (GUI):')
                print(f'  │    Protocol: RDP  |  Server: 127.0.0.1:{t.local_port}')
                print('  │  Hoặc xfreerdp (command line):')
                print(f'{Color.CYAN}  │    xfreerdp /v:127.0.0.1:{t.local_port} /u:<username_may_b>{Color.RESET}')
                print('  │  Hoặc chọn [5] → [2] trong menu để xem hướng dẫn')
            else:
                print(f'  │  Kết nối tới: localhost:{t.local_port}')
                print(f'{Color.CYAN}  │    vncviewer 127.0.0.1:{t.local_port}{Color.RESET}')

            print(f'{Color.CYAN}  └' + '─' * 62 + f'┘{Color.RESET}\n')

        print(f'{Color.YELLOW}  ⚠  ĐIỀU KIỆN KẾT NỐI THÀNH CÔNG:')
        print(f'    • Máy B RUNNING với Session ID: "{cfg.session_id}"')
        print('    • Máy A (máy này) phải đang RUNNING')
        print('    • Cả 2 máy có internet (dù khác mạng đều được)')
        print(f'    • Cùng Session ID: "{cfg.session_id}"{Color.RESET}')
