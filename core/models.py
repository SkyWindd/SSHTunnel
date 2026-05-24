"""
Models — tương đương các enum và class config trong C#:
  MachineRole, VpsMode, ConnectionType
  VpsConfig, TunnelConfig, AppConfig, SessionPorts
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List


class MachineRole(IntEnum):
    MachineA = 0  # Client — kết nối vào máy bạn
    MachineB = 1  # Server — máy được kết nối vào


class VpsMode(IntEnum):
    Default = 0   # Default AWS VPS (built-in)
    Custom  = 1   # Custom VPS của user


class ConnectionType(IntEnum):
    SSH    = 22    # SSH tunnel → port 22
    RDP    = 3389  # RDP tunnel → port 3389
    Custom = 0     # Custom port forward


@dataclass
class VpsConfig:
    host:         str = ''
    port:         int = 22
    username:     str = 'ubuntu'
    password:     str = ''
    ssh_key_file: str = ''


@dataclass
class TunnelConfig:
    name:        str            = 'custom'
    type:        ConnectionType = ConnectionType.Custom
    local_port:  int            = 0
    remote_port: int            = 0
    vps_port:    int            = 0


@dataclass
class AppConfig:
    role:                MachineRole  = MachineRole.MachineA
    vps_mode:            VpsMode      = VpsMode.Default
    session_id:          str          = ''
    custom_vps:          VpsConfig    = field(default_factory=VpsConfig)
    tunnels:             List[TunnelConfig] = field(default_factory=list)
    plink_path:          str          = 'plink.exe'
    heartbeat_interval:  int          = 15   # seconds
    reconnect_delay:     int          = 5    # seconds
    auto_reconnect:      bool         = True

    @property
    def vps(self) -> VpsConfig:
        """Trả về VpsConfig đang dùng (Default hoặc Custom)."""
        if self.vps_mode == VpsMode.Default:
            return _DEFAULT_VPS
        return self.custom_vps


# Default AWS VPS — giống DefaultVpsProvider trong C#
_DEFAULT_VPS = VpsConfig(
    host     = '13.229.239.111',
    port     = 22,
    username = 'ubuntu',
)


@dataclass
class SessionPorts:
    session_id:   str
    ssh_port:     int
    rdp_port:     int
    custom_port:  int
