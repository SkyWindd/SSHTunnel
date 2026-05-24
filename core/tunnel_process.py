"""
TunnelProcess — base class cho PlinkProcess và SshProcess.
Quản lý 1 subprocess tunnel: start, stop, is_running.
"""

import shlex
import subprocess
import threading
from abc import ABC, abstractmethod
from core.logger import Logger


class TunnelProcess(ABC):
    """Abstract base class cho tunnel process."""

    def __init__(self, tunnel_name: str, executable: str, arguments: str):
        self.tunnel_name = tunnel_name
        self._executable = executable
        self._arguments  = arguments
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self) -> bool:
        self.stop()  # Kill stale process trước
        try:
            import platform
            # shlex.split xử lý đúng path có dấu cách và dấu ngoặc kép
            # posix=False trên Windows để không strip dấu ngoặc kép
            posix = platform.system() != 'Windows'
            args = shlex.split(self._arguments, posix=posix)
            # Trên Windows: bỏ dấu ngoặc kép thừa bao quanh path
            if not posix:
                args = [a.strip('"') for a in args]
            cmd = [self._executable] + args
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
            # Đọc stdout/stderr trong background threads
            threading.Thread(
                target=self._read_stream,
                args=(self._process.stdout, 'OUT'),
                daemon=True,
            ).start()
            threading.Thread(
                target=self._read_stream,
                args=(self._process.stderr, 'ERR'),
                daemon=True,
            ).start()

            Logger.success(
                f'[{self.tunnel_name}] {self._executable_label} started '
                f'(PID {self._process.pid}) → {self._arguments}'
            )
            return True
        except Exception as e:
            Logger.error(f'[{self.tunnel_name}] Failed to start: {e}')
            return False

    def stop(self) -> None:
        with self._lock:
            if self._process is None:
                return
            try:
                if self._process.poll() is None:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                    Logger.info(f'[{self.tunnel_name}] {self._executable_label} stopped (PID {self._process.pid})')
            except Exception as e:
                Logger.warn(f'[{self.tunnel_name}] Stop error: {e}')
            finally:
                self._process = None

    def _read_stream(self, stream, kind: str) -> None:
        """Đọc stdout/stderr và log ra."""
        try:
            for line in iter(stream.readline, b''):
                text = line.decode('utf-8', errors='replace').rstrip()
                if text:
                    if kind == 'ERR':
                        Logger.warn(f'[{self.tunnel_name}] STDERR: {text}')
                    else:
                        Logger.tunnel(f'[{self.tunnel_name}] {text}')
        except Exception:
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()

    @property
    @abstractmethod
    def _executable_label(self) -> str:
        """Label hiển thị trong log (plink / ssh)."""
        ...
