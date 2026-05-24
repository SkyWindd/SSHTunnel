"""
TunnelMonitor — tương đương TunnelMonitor.cs + LinuxTunnelMonitor.cs
Dùng chung cho cả Windows và Linux — sự khác biệt nằm ở TunnelProcess
(PlinkProcess cho Windows, SshProcess cho Linux).

Quản lý nhiều tunnel, monitor liveness, auto-reconnect khi tunnel chết.
"""

import platform
import socket
import threading
from dataclasses import dataclass
from typing import List

from core.logger import Logger, Color
from core.models import AppConfig, MachineRole, VpsMode
from core.tunnel_process import TunnelProcess
from core.config_manager import DefaultVpsProvider


@dataclass
class ManagedTunnel:
    config:          object
    process:         TunnelProcess
    reconnect_count: int = 0


class TunnelMonitor:
    def __init__(self, cfg: AppConfig):
        self._cfg      = cfg
        self._tunnels: List[ManagedTunnel] = []
        self._running  = False
        self._stop_evt = threading.Event()
        self._monitor_thread = None
        self._lock     = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def start_all(self) -> None:
        if self._running:
            return
        Logger.info('TunnelMonitor: starting all tunnels...')
        self._stop_evt.clear()
        vps = self._resolve_vps()
        for t in self._cfg.tunnels:
            process = self._create_process(t, vps)
            managed = ManagedTunnel(config=t, process=process)
            self._tunnels.append(managed)
            process.start()
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name='TunnelMonitor'
        )
        self._monitor_thread.start()

    def stop_all(self) -> None:
        if not self._running:
            return
        Logger.info('TunnelMonitor: stopping all tunnels...')
        self._stop_evt.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        with self._lock:
            for mt in self._tunnels:
                mt.process.stop()
            self._tunnels.clear()
        self._running = False

    def print_status(self) -> None:
        vps = self._resolve_vps()
        print(f'\n{Color.CYAN}  Role: {self._cfg.role.name}   AutoReconnect: {self._cfg.auto_reconnect}')
        print(f'  VPS : {vps.username}@{vps.host}:{vps.port}')
        if platform.system() != 'Windows':
            from linux.ssh_wrapper import SshWrapper
            print(f'  SSH : {SshWrapper.find_ssh_path()}')
        print()
        print(f'  {"Tunnel":<12} {"Type":<8} {"Ports":<28} {"Status":<10} Reconnects')
        print('  ' + '-' * 72)
        print(Color.RESET, end='')
        with self._lock:
            tunnels = list(self._tunnels)
        for mt in tunnels:
            t = mt.config
            is_b = self._cfg.role == MachineRole.MachineB
            port_info = (
                f'VPS:{t.vps_port} <- local:{t.remote_port}'
                if is_b
                else f'local:{t.local_port} -> VPS:{t.vps_port}'
            )
            status = 'UP  ' if mt.process.is_running else 'DOWN'
            color  = Color.GREEN if mt.process.is_running else Color.RED
            print(f'  {t.name:<12} {t.type.name:<8} {port_info:<28} {color}{status:<10}{Color.RESET} {mt.reconnect_count}x')
        print()

    def _monitor_loop(self) -> None:
        while not self._stop_evt.wait(timeout=self._cfg.heartbeat_interval):
            with self._lock:
                tunnels = list(self._tunnels)
            for mt in tunnels:
                if self._stop_evt.is_set():
                    break
                if mt.process.is_running:
                    if (
                        self._cfg.role == MachineRole.MachineA
                        and not self._is_port_open('127.0.0.1', mt.config.local_port)
                    ):
                        Logger.warn(f'[{mt.config.name}] Port {mt.config.local_port} not responding — treating as dead.')
                        mt.process.stop()
                    else:
                        continue
                if not self._cfg.auto_reconnect:
                    continue
                Logger.warn(f'[{mt.config.name}] Tunnel down. Reconnecting in {self._cfg.reconnect_delay}s...')
                if self._stop_evt.wait(timeout=self._cfg.reconnect_delay):
                    break
                mt.reconnect_count += 1
                mt.process.start()

    def _resolve_vps(self):
        if self._cfg.vps_mode == VpsMode.Default:
            return DefaultVpsProvider.get_vps_config()
        return self._cfg.custom_vps

    def _create_process(self, tunnel_config, vps) -> TunnelProcess:
        is_b = self._cfg.role == MachineRole.MachineB
        if platform.system() == 'Windows':
            from windows.plink_wrapper import PlinkWrapper
            return PlinkWrapper.create_process(
                tunnel_name=tunnel_config.name,
                plink_path=self._cfg.plink_path,
                vps=vps,
                tunnel=tunnel_config,
                is_machine_b=is_b,
            )
        else:
            from linux.ssh_wrapper import SshWrapper
            return SshWrapper.create_process(
                tunnel_name=tunnel_config.name,
                vps=vps,
                tunnel=tunnel_config,
                is_machine_b=is_b,
            )

    @staticmethod
    def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop_all()
