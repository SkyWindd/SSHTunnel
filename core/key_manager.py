"""
KeyManager — tương đương KeyManager.cs
Mã hóa / giải mã file key VPS bằng AES-256-GCM với group password.

Layout file .enc: [salt 16B][nonce 12B][tag 16B][ciphertext]
Tương thích hoàn toàn với C# version.

Windows: default_vps.ppk  → default_vps.ppk.enc
Linux:   default_vps.pem  → default_vps.pem.enc
"""

import os
import platform
import tempfile
from enum import Enum, auto
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.logger import Logger

# ── Constants ──────────────────────────────────────────────
PBKDF2_ITERATIONS = 200_000
SALT_SIZE         = 16
NONCE_SIZE        = 12
TAG_SIZE          = 16

# File names theo OS
def _plain_file() -> str:
    return 'default_vps.ppk' if platform.system() == 'Windows' else 'default_vps.pem'

def _encrypted_file() -> str:
    return 'default_vps.ppk.enc' if platform.system() == 'Windows' else 'default_vps.pem.enc'

# Backward compat: C# dùng .ppk.enc — Linux cũng check file này
_LEGACY_ENC = 'default_vps.ppk.enc'


class KeyMode(Enum):
    Plain     = auto()
    Encrypted = auto()
    Missing   = auto()


class KeyManager:

    # ── Public API ─────────────────────────────────────────

    @staticmethod
    def app_dir() -> Path:
        import sys
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent

    @staticmethod
    def detect_mode() -> KeyMode:
        """
        Kiểm tra trạng thái file key.

        Thứ tự ưu tiên:
          Linux:   .pem.enc > .ppk.enc (legacy) > .pem (plain)
          Windows: .ppk.enc > .ppk (plain)

        NOTE: Encrypted luôn ưu tiên hơn Plain —
        tránh trường hợp vừa mã hóa xong nhưng chưa xóa file gốc
        lại bị hỏi mã hóa lần nữa.
        """
        d = KeyManager.app_dir()

        if platform.system() != 'Windows':
            # Linux: kiểm tra encrypted TRƯỚC plain
            if (d / 'default_vps.pem.enc').exists():
                return KeyMode.Encrypted
            if (d / _LEGACY_ENC).exists():
                return KeyMode.Encrypted
            if (d / 'default_vps.pem').exists():
                return KeyMode.Plain
        else:
            # Windows
            if (d / 'default_vps.ppk.enc').exists():
                return KeyMode.Encrypted
            if (d / 'default_vps.ppk').exists():
                return KeyMode.Plain

        return KeyMode.Missing

    @staticmethod
    def decrypt_to_memory(password: str) -> bytes:
        """
        Giải mã file .enc → bytes trong RAM.
        Tự tìm đúng file .enc theo OS.
        """
        d    = KeyManager.app_dir()
        path = None

        if platform.system() != 'Windows':
            # Linux: thử .pem.enc trước, rồi legacy .ppk.enc
            if (d / 'default_vps.pem.enc').exists():
                path = d / 'default_vps.pem.enc'
            elif (d / _LEGACY_ENC).exists():
                path = d / _LEGACY_ENC
        else:
            path = d / 'default_vps.ppk.enc'

        if not path or not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file .enc")

        data = path.read_bytes()
        min_size = SALT_SIZE + NONCE_SIZE + TAG_SIZE
        if len(data) < min_size:
            raise ValueError('File .enc bị lỗi hoặc không hợp lệ.')

        salt       = data[:SALT_SIZE]
        nonce      = data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
        tag        = data[SALT_SIZE + NONCE_SIZE:SALT_SIZE + NONCE_SIZE + TAG_SIZE]
        ciphertext = data[SALT_SIZE + NONCE_SIZE + TAG_SIZE:]

        key = KeyManager._derive_key(password, salt)
        try:
            aesgcm      = AESGCM(key)
            plaintext   = aesgcm.decrypt(nonce, ciphertext + tag, None)
            return plaintext
        except Exception:
            raise PermissionError('Sai mật khẩu nhóm hoặc file bị hỏng.')
        finally:
            key = b'\x00' * len(key)

    @staticmethod
    def encrypt_plain_key(password: str) -> None:
        """
        Mã hóa file key gốc thành .enc.
        Windows: default_vps.ppk  → default_vps.ppk.enc
        Linux:   default_vps.pem  → default_vps.pem.enc
        """
        d          = KeyManager.app_dir()
        plain_name = _plain_file()
        enc_name   = _encrypted_file()
        plain_path = d / plain_name
        enc_path   = d / enc_name

        if not plain_path.exists():
            raise FileNotFoundError(f"Không tìm thấy '{plain_name}' để mã hóa.")

        plaintext = plain_path.read_bytes()
        salt  = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        key   = KeyManager._derive_key(password, salt)

        try:
            aesgcm      = AESGCM(key)
            ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
            ciphertext  = ct_with_tag[:-TAG_SIZE]
            tag         = ct_with_tag[-TAG_SIZE:]

            with open(enc_path, 'wb') as f:
                f.write(salt + nonce + tag + ciphertext)

            Logger.success(f"Đã mã hóa '{plain_name}' → '{enc_name}' ({enc_path.stat().st_size} bytes)")
            Logger.info('File .enc có thể upload GitHub an toàn.')
        finally:
            key = b'\x00' * len(key)

    @staticmethod
    def write_temp_key(key_bytes: bytes) -> str:
        """Ghi bytes key ra file tạm, trả về đường dẫn."""
        ext  = 'ppk' if platform.system() == 'Windows' else 'pem'
        tmp  = tempfile.NamedTemporaryFile(
            prefix='stm_', suffix=f'.{ext}', delete=False
        )
        tmp.write(key_bytes)
        tmp.close()
        path = tmp.name

        if platform.system() != 'Windows':
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
        return path

    @staticmethod
    def delete_temp_key(path: str) -> None:
        """Xóa file key tạm an toàn."""
        if not path or not Path(path).exists():
            return
        try:
            size = Path(path).stat().st_size
            with open(path, 'wb') as f:
                f.write(b'\x00' * size)
            Path(path).unlink()
            Logger.info('File key tạm đã được xóa an toàn.')
        except Exception as e:
            Logger.warn(f'File key tạm chưa xóa được: {path} — {e}')

    @staticmethod
    def resolve_key_path() -> str:
        """Tìm đường dẫn file key plain theo OS."""
        d = KeyManager.app_dir()

        if platform.system() != 'Windows':
            pem = d / 'default_vps.pem'
            if pem.exists():
                return str(pem)
        else:
            ppk = d / 'default_vps.ppk'
            if ppk.exists():
                return str(ppk)

        plain_name = _plain_file()
        return str(d / plain_name)

    @staticmethod
    def print_key_status() -> None:
        """Hiển thị trạng thái key."""
        mode       = KeyManager.detect_mode()
        plain_name = _plain_file()
        enc_name   = _encrypted_file()

        from core.logger import Color
        if mode == KeyMode.Encrypted:
            print(f'\n{Color.GREEN}  Key status: ✔  \'{enc_name}\' (đã mã hóa — an toàn){Color.RESET}')
            print('     Nhập group password để sử dụng.')
        elif mode == KeyMode.Plain:
            print(f'\n{Color.YELLOW}  Key status: ⚠  \'{plain_name}\' (chưa mã hóa — KHÔNG nên upload GitHub){Color.RESET}')
            print('     Dùng menu [8] Setup hoặc flag --encrypt-key để mã hóa.')
        else:
            print(f'\n{Color.RED}  Key status: ✘  Không tìm thấy \'{plain_name}\' hoặc \'{enc_name}\'{Color.RESET}')
            print(f'     Đặt file {plain_name} vào cùng thư mục với SshTunnelManager')

    # ── Private helpers ────────────────────────────────────

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm  = hashes.SHA256(),
            length     = 32,
            salt       = salt,
            iterations = PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode('utf-8'))
