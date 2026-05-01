"""Security helpers: Fernet credential encryption + JWT auth + argon2 password hashing."""

import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import settings

# --- Credential encryption (Fernet) ---

# Lazily-initialised so tests can patch settings.FERNET_KEY before first use.
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.FERNET_KEY.encode())
    return _fernet


def encrypt_credential(plaintext: str) -> bytes:
    """Encrypt a plaintext credential string for storage in credential_blob."""
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_credential(ciphertext: bytes) -> str:
    """Decrypt a credential_blob back to plaintext. Raises InvalidToken on tamper."""
    return _get_fernet().decrypt(ciphertext).decode()


# --- Password hashing (argon2) ---

_ph = PasswordHasher()


def hash_password(plaintext: str) -> str:
    return _ph.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plaintext)
    except VerifyMismatchError:
        return False


# --- JWT (access tokens) ---

def create_access_token(sub: str, tenant_id: str, is_superuser: bool) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": sub, "tenant_id": tenant_id, "is_superuser": is_superuser, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises ValueError on failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


# --- Refresh tokens (opaque UUIDs stored in Redis) ---

REFRESH_KEY_PREFIX = "sniper:refresh:"


def make_refresh_token() -> str:
    return str(uuid.uuid4())


def refresh_token_key(token: str) -> str:
    return f"{REFRESH_KEY_PREFIX}{token}"
