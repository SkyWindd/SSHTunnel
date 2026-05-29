"""
SessionBook — lưu danh sách session đã dùng và probe trạng thái máy B.

File lưu: session_book.json (cạnh config.json)
Mỗi entry: { "session_id": "nhom1", "added_at": "2026-05-28 09:00:00" }

Probe: thử connect tới VPS:ssh_port của session đó.
  - Nếu thông  → máy B đang giữ tunnel  → Online
  - Nếu không  → máy B offline hoặc chưa start
"""

import json
import socket
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from core.key_manager import KeyManager
from core.session_manager import SessionManager

BOOK_FILE = 'session_book.json'
PROBE_TIMEOUT = 1.5   # giây
PROBE_WORKERS = 8     # probe song song tối đa


@dataclass
class SessionEntry:
    session_id: str
    added_at:   str = ''

    # Trạng thái probe — không lưu vào file
    status: str = '…'   # '● Online', '○ Offline', '…'


class SessionBook:

    # ── Đọc / ghi ─────────────────────────────────────────

    @staticmethod
    def _path() -> Path:
        return KeyManager.app_dir() / BOOK_FILE

    @classmethod
    def load(cls) -> List[SessionEntry]:
        path = cls._path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return [
                SessionEntry(
                    session_id = e.get('session_id', ''),
                    added_at   = e.get('added_at', ''),
                )
                for e in data
                if e.get('session_id')
            ]
        except Exception:
            return []

    @classmethod
    def save(cls, entries: List[SessionEntry]) -> None:
        path = cls._path()
        try:
            data = [
                {'session_id': e.session_id, 'added_at': e.added_at}
                for e in entries
            ]
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception:
            pass

    @classmethod
    def add(cls, session_id: str) -> None:
        """Thêm session vào book nếu chưa có."""
        entries = cls.load()
        if any(e.session_id == session_id for e in entries):
            return
        entries.append(SessionEntry(
            session_id = session_id,
            added_at   = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ))
        cls.save(entries)

    @classmethod
    def remove(cls, session_id: str) -> None:
        entries = [e for e in cls.load() if e.session_id != session_id]
        cls.save(entries)

    @classmethod
    def exists(cls, session_id: str) -> bool:
        return any(e.session_id == session_id for e in cls.load())

    # ── Probe ──────────────────────────────────────────────

    @classmethod
    def probe_all(cls, entries: List[SessionEntry], vps_host: str) -> None:
        """
        Probe song song tất cả entries, cập nhật .status trực tiếp.
        Dùng ssh_port của mỗi session để kiểm tra máy B có online không.
        """
        sem = threading.Semaphore(PROBE_WORKERS)
        threads = []

        def _probe(entry: SessionEntry) -> None:
            with sem:
                port = SessionManager.get_session_ports(entry.session_id).ssh_port
                entry.status = cls._check_port(vps_host, port)

        for e in entries:
            t = threading.Thread(target=_probe, args=(e,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=PROBE_TIMEOUT + 1)

    @staticmethod
    def _check_port(host: str, port: int) -> str:
        try:
            with socket.create_connection((host, port), timeout=PROBE_TIMEOUT):
                return '● Online'
        except (socket.timeout, ConnectionRefusedError, OSError):
            return '○ Offline'

    # ── Hiển thị bảng ─────────────────────────────────────

    @classmethod
    def print_table(cls, entries: List[SessionEntry], current_session: str = '') -> None:
        """In bảng saved sessions với status đã probe."""
        if not entries:
            print('  (Chưa có session nào được lưu)')
            return

        print()
        print('  ┌─────┬──────────────────────────────────┬────────────┐')
        print('  │  #  │ Session ID                       │ Máy B      │')
        print('  ├─────┼──────────────────────────────────┼────────────┤')
        for i, e in enumerate(entries, 1):
            marker = '▶ ' if e.session_id == current_session else '  '
            sid    = f'{marker}{e.session_id}'
            print(f'  │ {i:<3} │ {sid:<32} │ {e.status:<10} │')
        print('  └─────┴──────────────────────────────────┴────────────┘')
