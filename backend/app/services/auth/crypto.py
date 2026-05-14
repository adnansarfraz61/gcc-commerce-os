import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


class TokenCipher:
    def __init__(self) -> None:
        settings = get_settings()
        secret = settings.token_encryption_key or settings.secret_key
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
