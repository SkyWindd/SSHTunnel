"""
KeyManager — tương đương KeyManager.cs
Mã hóa / giải mã file key VPS bằng AES-256-GCM với group password.

Layout file .enc: [salt 16B][nonce 12B][tag 16B][ciphertext]
Hoàn toàn tương thích với C# version — file .enc tạo từ C# đọc được bằng Python và ngược lại.
"""

import os
import platform
import subprocess
import tempfile
from enum import Enum, auto
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.logger import Logger

# ── Constants — phải giống hệt C# ─────────────────────────
ENCRYPTED_FILE   = 'default_vps.ppk.enc'
PLAIN_FILE_WIN   = 'default_vps.ppk'
PLAIN_FILE_LINUX = 'default_vps.pem'
PBKDF2_ITERATIONS = 200_000
SALT_SIZE         = 16
NONCE_SIZE        = 12
TAG_SIZE          = 16


class KeyMode(Enum):
    Plain     = auto()
    Encrypted = auto()
    Missing   = auto()


class KeyManager:

    # ── Public API ─────────────────────────────────────────

    @staticmethod
    def app_dir() -> Path:
        """Thư mục chứa executable / script."""
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstaller binary
            return Path(sys.executable).parent
        return Path(__file__).parent.parent

    @staticmethod
    def detect_mode() -> KeyMode:
        """
        Kiểm tra trạng thái file key.
        Linux: ưu tiên .pem trước — nếu có .pem dùng luôn.
        Windows: kiểm tra .enc rồi .ppk.
        """
        d = KeyManager.app_dir()

        # Linux: ưu tiên .pem trực tiếp
        if platform.system() != 'Windows':
            if (d / PLAIN_FILE_LINUX).exists():
                return KeyMode.Plain

        # Windows hoặc Linux không có .pem
        if (d / ENCRYPTED_FILE).exists():
            return KeyMode.Encrypted
        if (d / PLAIN_FILE_WIN).exists():
            return KeyMode.Plain

        return KeyMode.Missing

    @staticmethod
    def decrypt_to_memory(password: str) -> bytes:
        """
        Giải mã file .enc bằng password → trả về bytes trong RAM.
        KHÔNG ghi file ra đĩa.
        Tương thích hoàn toàn với C# version.
        """
        path = KeyManager.app_dir() / ENCRYPTED_FILE
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy '{ENCRYPTED_FILE}'")

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
            aesgcm = AESGCM(key)
            # AESGCM của Python expect ciphertext + tag ghép lại
            plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
            return plaintext
        except Exception:
            raise PermissionError('Sai mật khẩu nhóm hoặc file bị hỏng.')
        finally:
            # Zero out key trong memory
            key = b'\x00' * len(key)

    @staticmethod
    def encrypt_plain_key(password: str) -> None:
        """
        Mã hóa file .ppk thành .ppk.enc bằng password.
        Dùng khi setup lần đầu (người quản lý chạy).
        """
        d         = KeyManager.app_dir()
        plain_path = d / PLAIN_FILE_WIN
        enc_path   = d / ENCRYPTED_FILE

        if not plain_path.exists():
            raise FileNotFoundError(f"Không tìm thấy '{PLAIN_FILE_WIN}' để mã hóa.")

        plaintext = plain_path.read_bytes()
        salt  = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        key   = KeyManager._derive_key(password, salt)

        try:
            aesgcm = AESGCM(key)
            # Python AESGCM trả về ciphertext + tag ghép lại (16 bytes tag ở cuối)
            ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
            ciphertext  = ct_with_tag[:-TAG_SIZE]
            tag         = ct_with_tag[-TAG_SIZE:]

            # Ghi: [salt][nonce][tag][ciphertext] — giống hệt C#
            with open(enc_path, 'wb') as f:
                f.write(salt)
                f.write(nonce)
                f.write(tag)
                f.write(ciphertext)

            Logger.success(f"Đã mã hóa → '{ENCRYPTED_FILE}' ({enc_path.stat().st_size} bytes)")
            Logger.info('File này có thể upload GitHub an toàn.')
        finally:
            key = b'\x00' * len(key)

    @staticmethod
    def write_temp_key(key_bytes: bytes) -> str:
        """
        Ghi bytes key ra file tạm, trả về đường dẫn.
        Linux: dùng .pem, Windows: dùng .ppk
        File tạm sẽ bị xóa khi gọi delete_temp_key().
        """
        ext  = 'ppk' if platform.system() == 'Windows' else 'pem'
        tmp  = tempfile.NamedTemporaryFile(
            prefix='stm_', suffix=f'.{ext}',
            delete=False
        )
        tmp.write(key_bytes)
        tmp.close()
        path = tmp.name

        if platform.system() != 'Windows':
            # Linux: chmod 600
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
        return path

    @staticmethod
    def delete_temp_key(path: str) -> None:
        """
        Xóa file key tạm khỏi đĩa an toàn.
        Ghi đè bằng 0 trước khi xóa.
        """
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
        """
        Tìm đường dẫn file key theo OS.
        Linux: ưu tiên .pem trước.
        Windows: tìm .ppk.
        """
        d = KeyManager.app_dir()

        if platform.system() != 'Windows':
            pem = d / PLAIN_FILE_LINUX
            if pem.exists():
                return str(pem)

        ppk = d / PLAIN_FILE_WIN
        if ppk.exists():
            return str(ppk)

        # Fallback
        return str(d / (PLAIN_FILE_LINUX if platform.system() != 'Windows' else PLAIN_FILE_WIN))

    @staticmethod
    def print_key_status() -> None:
        """Hiển thị trạng thái key và hướng dẫn."""
        mode = KeyManager.detect_mode()
        plain_name = PLAIN_FILE_LINUX if platform.system() != 'Windows' else PLAIN_FILE_WIN

        from core.logger import Color
        if mode == KeyMode.Encrypted:
            print(f'\n{Color.GREEN}  Key status: ✔  \'{ENCRYPTED_FILE}\' (đã mã hóa — an toàn){Color.RESET}')
            print('     Nhập group password để sử dụng.')
        elif mode == KeyMode.Plain:
            print(f'\n{Color.YELLOW}  Key status: ⚠  \'{plain_name}\' (chưa mã hóa — KHÔNG nên upload GitHub){Color.RESET}')
            print('     Dùng menu [8] Setup → mã hóa key để bảo vệ.')
        else:
            print(f'\n{Color.RED}  Key status: ✘  Không tìm thấy \'{plain_name}\' hoặc \'{ENCRYPTED_FILE}\'{Color.RESET}')
            print(f'     Đặt file {plain_name} vào cùng thư mục với SshTunnelManager')

    # ── Private helpers ────────────────────────────────────

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """
        PBKDF2-SHA256, 200000 vòng, 32 bytes.
        Giống hệt C# Rfc2898DeriveBytes.Pbkdf2.
        """
        kdf = PBKDF2HMAC(
            algorithm  = hashes.SHA256(),
            length     = 32,
            salt       = salt,
            iterations = PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode('utf-8'))
