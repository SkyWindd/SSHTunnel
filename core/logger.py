"""
Logger — tương đương Logger.cs
Ghi log ra file tunnel.log và console với màu sắc.
"""

import threading
import sys
from datetime import datetime
from pathlib import Path

# ANSI color codes
class Color:
    GRAY    = '\033[90m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    CYAN    = '\033[96m'
    RESET   = '\033[0m'

# Windows không hỗ trợ ANSI mặc định — enable nếu cần
import platform
if platform.system() == 'Windows':
    import os
    os.system('')  # Enable ANSI escape codes trên Windows 10+


class Logger:
    _lock = threading.Lock()
    _log_file = Path('tunnel.log')
    verbose_console: bool = True

    @classmethod
    def info(cls, msg: str) -> None:
        cls._write('INFO ', Color.GRAY, msg)

    @classmethod
    def success(cls, msg: str) -> None:
        cls._write('OK   ', Color.GREEN, msg)

    @classmethod
    def warn(cls, msg: str) -> None:
        cls._write('WARN ', Color.YELLOW, msg)

    @classmethod
    def error(cls, msg: str) -> None:
        cls._write('ERROR', Color.RED, msg)

    @classmethod
    def tunnel(cls, msg: str) -> None:
        cls._write('TUNL ', Color.CYAN, msg)

    @classmethod
    def _write(cls, level: str, color: str, msg: str) -> None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f'[{timestamp}] [{level}] {msg}'

        with cls._lock:
            # Ghi ra file log
            try:
                with open(cls._log_file, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            except Exception:
                pass  # Bỏ qua lỗi ghi file

            # In ra console
            if cls.verbose_console:
                print(f'{color}{line}{Color.RESET}', flush=True)

    @classmethod
    def print_last_lines(cls, n: int = 30) -> None:
        if not cls._log_file.exists():
            print('(no log file yet)')
            return
        lines = cls._log_file.read_text(encoding='utf-8').splitlines()
        for line in lines[-n:]:
            print(line)
