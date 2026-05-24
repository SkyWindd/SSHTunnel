"""
PlinkWrapper — tương đương PlinkWrapper.cs
Build plink.exe command-line args và tạo PlinkProcess.
"""

import os
from pathlib import Path

from core.tunnel_process import TunnelProcess
from core.models import VpsConfig, TunnelConfig
from core.logger import Logger


class PlinkProcess(TunnelProcess):
    """Tương đương PlinkProcess trong C#."""

    @property
    def _executable_label(self) -> str:
        return 'plink'


class PlinkWrapper:

    @staticmethod
    def build_reverse_args(vps: VpsConfig, tunnel: TunnelConfig) -> str:
        """
        Machine B — Reverse Tunnel:
        plink -ssh user@VPS -P port -R VpsPort:localhost:RemotePort -N -batch -i key.ppk
        """
        auth = PlinkWrapper._build_auth(vps)
        return (
            f'-ssh {vps.username}@{vps.host} -P {vps.port} '
            f'-R {tunnel.vps_port}:localhost:{tunnel.remote_port} '
            f'-N -batch {auth}'
        )

    @staticmethod
    def build_forward_args(vps: VpsConfig, tunnel: TunnelConfig) -> str:
        """
        Machine A — Forward Tunnel:
        plink -ssh user@VPS -P port -L LocalPort:localhost:VpsPort -N -batch -i key.ppk
        """
        auth = PlinkWrapper._build_auth(vps)
        return (
            f'-ssh {vps.username}@{vps.host} -P {vps.port} '
            f'-L {tunnel.local_port}:localhost:{tunnel.vps_port} '
            f'-N -batch {auth}'
        )

    @staticmethod
    def _build_auth(vps: VpsConfig) -> str:
        if vps.ssh_key_file:
            return f'-i "{vps.ssh_key_file}"'
        if vps.password:
            return f'-pw "{vps.password}"'
        return ''  # Dùng ssh-agent / pageant

    @staticmethod
    def validate_plink_path(path: str) -> bool:
        """Kiểm tra plink.exe có tồn tại không."""
        if Path(path).exists():
            return True
        # Tìm trong PATH
        for d in os.environ.get('PATH', '').split(os.pathsep):
            if Path(d) / path:
                full = Path(d) / path
                if full.exists():
                    return True
        return False

    @staticmethod
    def create_process(
        tunnel_name: str,
        plink_path: str,
        vps: VpsConfig,
        tunnel: TunnelConfig,
        is_machine_b: bool,
    ) -> PlinkProcess:
        """Factory method — tạo PlinkProcess với args đúng."""
        args = (
            PlinkWrapper.build_reverse_args(vps, tunnel)
            if is_machine_b
            else PlinkWrapper.build_forward_args(vps, tunnel)
        )
        return PlinkProcess(tunnel_name, plink_path, args)
