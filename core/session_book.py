"""
SessionBook — lưu danh sách session đã dùng.

File lưu: session_book.json (cạnh config.json)
Mỗi entry: { "session_id": "nhom1", "added_at": "2026-05-28 09:00:00" }
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from core.key_manager import KeyManager

BOOK_FILE = 'session_book.json'


@dataclass
class SessionEntry:
    session_id: str
    added_at:   str = ''


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

    # ── Hiển thị bảng ─────────────────────────────────────

    @classmethod
    def print_table(cls, entries: List[SessionEntry], current_session: str = '') -> None:
        """In bảng saved sessions."""
        if not entries:
            print('  (Chưa có session nào được lưu)')
            return

        print()
        print('  ┌─────┬──────────────────────────────────┬─────────────────────┐')
        print('  │  #  │ Session ID                       │ Ngày thêm           │')
        print('  ├─────┼──────────────────────────────────┼─────────────────────┤')
        for i, e in enumerate(entries, 1):
            marker = '▶ ' if e.session_id == current_session else '  '
            sid    = f'{marker}{e.session_id}'
            print(f'  │ {i:<3} │ {sid:<32} │ {e.added_at:<19} │')
        print('  └─────┴──────────────────────────────────┴─────────────────────┘')
