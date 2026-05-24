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
        """
        Hash session ID → port number trong range 10000-19999.
        Dùng SHA256 để phân phối đều, collision cực kỳ hiếm.
        """
        if not session_id or not session_id.strip():
            raise ValueError('Session ID cannot be empty.')

        digest = hashlib.sha256(session_id.strip().lower().encode('utf-8')).digest()
        # Lấy 4 bytes đầu làm uint32, mod vào range
        value = int.from_bytes(digest[:4], 'little') % PORT_RANGE_SIZE
        return PORT_RANGE_START + value

    @staticmethod
    def get_session_ports(session_id: str) -> SessionPorts:
        """
        Trả về 3 port từ session ID:
          SSH    → base port
          RDP    → base port + 1
          Custom → base port + 2
        """
        base = SessionManager.session_id_to_port(session_id)
        # Đảm bảo không overflow range
        if base + 2 > PORT_RANGE_END:
            base -= 2
        return SessionPorts(
            session_id  = session_id,
            ssh_port    = base,
            rdp_port    = base + 1,
            custom_port = base + 2,
        )

    @staticmethod
    def is_valid(session_id: str) -> bool:
        """
        Kiểm tra session ID hợp lệ:
        - 3-32 ký tự
        - Chỉ dùng chữ cái, số, dấu gạch ngang, gạch dưới
        """
        if not session_id:
            return False
        if not (3 <= len(session_id) <= 32):
            return False
        return bool(re.match(r'^[a-zA-Z0-9\-_]+$', session_id))

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
