"""
SshWrapper — tương đương SshWrapper.cs
Build ssh native command-line args và tạo SshProcess.
"""

import os
import subprocess
from pathlib import Path

from core.tunnel_process import TunnelProcess
from core.models import VpsConfig, TunnelConfig
from core.logger import Logger

DEFAULT_SSH_PATH = '/usr/bin/ssh'


class SshProcess(TunnelProcess):
    """Tương đương SshProcess trong C#."""

    @property
    def _executable_label(self) -> str:
        return 'ssh'


class SshWrapper:

    @staticmethod
    def build_reverse_args(vps: VpsConfig, tunnel: TunnelConfig) -> str:
        """
        Machine B — Reverse Tunnel:
        ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15
            -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes
            -i key.pem -R VpsPort:localhost:RemotePort -N -p port user@host
        """
        auth = SshWrapper._build_auth(vps)
        return (
            f'-o StrictHostKeyChecking=no '
            f'-o ServerAliveInterval=15 '
            f'-o ServerAliveCountMax=3 '
            f'-o ExitOnForwardFailure=yes '
            f'-o GatewayPorts=yes '
            f'{auth} '
            f'-R {tunnel.vps_port}:localhost:{tunnel.remote_port} '
            f'-N '
            f'-p {vps.port} '
            f'{vps.username}@{vps.host}'
        )

    @staticmethod
    def build_forward_args(vps: VpsConfig, tunnel: TunnelConfig) -> str:
        """
        Machine A — Forward Tunnel:
        ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15
            -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes
            -i key.pem -L LocalPort:localhost:VpsPort -N -p port user@host
        """
        auth = SshWrapper._build_auth(vps)
        return (
            f'-o StrictHostKeyChecking=no '
            f'-o ServerAliveInterval=15 '
            f'-o ServerAliveCountMax=3 '
            f'-o ExitOnForwardFailure=yes '
            f'{auth} '
            f'-L {tunnel.local_port}:localhost:{tunnel.vps_port} '
            f'-N '
            f'-p {vps.port} '
            f'{vps.username}@{vps.host}'
        )

    @staticmethod
    def _build_auth(vps: VpsConfig) -> str:
        """Tìm file key .pem và trả về -i flag."""
        if vps.ssh_key_file:
            key_file = SshWrapper._resolve_pem_path(vps.ssh_key_file)
            if Path(key_file).exists():
                SshWrapper._ensure_key_permissions(key_file)
                return f'-i "{key_file}"'
            Logger.warn(f'Key file không tìm thấy: {key_file}')

        if vps.password:
            if SshWrapper._is_sshpass_available():
                return ''  # SshProcess sẽ wrap bằng sshpass
            Logger.warn("Password auth cần 'sshpass'. Cài: sudo apt install sshpass")

        return ''  # Dùng ssh-agent hoặc default key

    @staticmethod
    def _resolve_pem_path(key_file: str) -> str:
        """
        Nếu config trỏ đến .ppk → tự tìm file .pem cùng thư mục.
        Ví dụ: default_vps.ppk → default_vps.pem
        """
        if key_file.lower().endswith('.ppk'):
            pem = Path(key_file).with_suffix('.pem')
            if pem.exists():
                return str(pem)
            # Thử tìm trong thư mục app
            from core.key_manager import KeyManager
            app_dir  = KeyManager.app_dir()
            pem_name = Path(key_file).stem + '.pem'
            return str(app_dir / pem_name)
        return key_file

    @staticmethod
    def _ensure_key_permissions(key_file: str) -> None:
        """chmod 600 file .pem — ssh từ chối nếu permission quá mở."""
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass

    @staticmethod
    def _is_sshpass_available() -> bool:
        try:
            result = subprocess.run(
                ['which', 'sshpass'],
                capture_output=True,
                timeout=1,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def find_ssh_path() -> str:
        """Tìm đường dẫn ssh trên hệ thống."""
        if Path(DEFAULT_SSH_PATH).exists():
            return DEFAULT_SSH_PATH
        # Tìm trong PATH
        for d in os.environ.get('PATH', '').split(os.pathsep):
            full = Path(d) / 'ssh'
            if full.exists():
                return str(full)
        return 'ssh'  # Fallback — để OS tự resolve

    @staticmethod
    def validate_ssh_path() -> bool:
        """Kiểm tra ssh có sẵn và chạy được không."""
        try:
            result = subprocess.run(
                [SshWrapper.find_ssh_path(), '-V'],
                capture_output=True,
                timeout=3,
            )
            return result.returncode in (0, 1)  # ssh -V exit 1 nhưng vẫn in version
        except Exception:
            return False

    @staticmethod
    def validate_pem_key(vps: VpsConfig) -> bool:
        """Kiểm tra file .pem có sẵn không."""
        if not vps.ssh_key_file:
            return False
        pem = SshWrapper._resolve_pem_path(vps.ssh_key_file)
        return Path(pem).exists()

    @staticmethod
    def create_process(
        tunnel_name: str,
        vps: VpsConfig,
        tunnel: TunnelConfig,
        is_machine_b: bool,
    ) -> SshProcess:
        """Factory method — tạo SshProcess với args đúng."""
        ssh_path = SshWrapper.find_ssh_path()
        args = (
            SshWrapper.build_reverse_args(vps, tunnel)
            if is_machine_b
            else SshWrapper.build_forward_args(vps, tunnel)
        )
        return SshProcess(tunnel_name, ssh_path, args)
