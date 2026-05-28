"""
SessionManager — tương đương SessionManager.cs
Chuyển Session ID thành port number dùng SHA256.
Đảm bảo cả 2 máy dùng cùng Session ID sẽ có cùng port.
"""

import hashlib
import re
from core.models import SessionPorts

PORT_RANGE_START = 10000
PORT_RANGE_END   = 19999
PORT_RANGE_SIZE  = PORT_RANGE_END - PORT_RANGE_START + 1  # 10000 slots


class SessionManager:

    @staticmethod
    def session_id_to_port(session_id: str) -> int:
        """Hash session ID → port number trong range 10000-19999."""
        if not session_id or not session_id.strip():
            raise ValueError('Session ID cannot be empty.')
        # Luôn dùng cleaned version để đảm bảo consistency
        clean = SessionManager.clean_session_id(session_id.strip().lower())
        digest = hashlib.sha256(clean.encode('utf-8')).digest()
        value = int.from_bytes(digest[:4], 'little') % PORT_RANGE_SIZE
        return PORT_RANGE_START + value

    @staticmethod
    def get_session_ports(session_id: str) -> SessionPorts:
        """Trả về 3 port từ session ID."""
        # Normalize session_id trước khi tính port
        clean_id = SessionManager.clean_session_id(session_id.strip())
        base = SessionManager.session_id_to_port(clean_id)
        if base + 2 > PORT_RANGE_END:
            base -= 2
        return SessionPorts(
            session_id  = clean_id,
            ssh_port    = base,
            rdp_port    = base + 1,
            custom_port = base + 2,
        )

    @staticmethod
    def clean_session_id(session_id: str) -> str:
        """
        Làm sạch session ID:
        - NFKD normalize → tách combining diacritics
        - Giữ lại chỉ ASCII printable, bỏ tất cả whitespace
        """
        import unicodedata
        normalized = unicodedata.normalize('NFKD', session_id)
        return ''.join(c for c in normalized if ord(c) < 128 and c.isprintable() and not c.isspace())

    @staticmethod
    def is_valid(session_id: str) -> bool:
        """
        Kiểm tra session ID hợp lệ:
        - 3-32 ký tự
        - Chỉ dùng chữ cái, số, dấu gạch ngang, gạch dưới
        - Tự động loại bỏ ký tự ẩn / non-ASCII trước khi kiểm tra
        """
        if not session_id:
            return False
        cleaned = SessionManager.clean_session_id(session_id)
        if not (3 <= len(cleaned) <= 32):
            return False
        # Sau khi clean, chỉ cho phép a-z A-Z 0-9 - _
        return bool(re.fullmatch(r'[a-zA-Z0-9\-_]+', cleaned))

    @staticmethod
    def print_session_info(session_id: str) -> None:
        ports = SessionManager.get_session_ports(session_id)
        print(f'\n  Session ID : "{session_id}"')
        print(f'  ┌──────────────────────────────────────┐')
        print(f'  │  Service │ VPS relay port │ Use for  │')
        print(f'  ├──────────────────────────────────────┤')
        print(f'  │  SSH     │   {ports.ssh_port:<13} │ port 22  │')
        print(f'  │  RDP     │   {ports.rdp_port:<13} │ port 3389│')
        print(f'  │  Custom  │   {ports.custom_port:<13} │ any port │')
        print(f'  └──────────────────────────────────────┘')
        print(f'\n  ⚠  Share this Session ID with your partner.')
        print(f'     Both machines MUST use the same Session ID.')
