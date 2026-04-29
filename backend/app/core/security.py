"""Credential encryption helpers using Fernet symmetric encryption.

All notification channel credentials (Discord webhook URLs, Pushover tokens)
are encrypted at rest in the notification_channels.credential_blob column.

The FERNET_KEY environment variable must be a URL-safe base64-encoded 32-byte
key produced by:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

IMPORTANT: FERNET_KEY rotation (re-encrypting all credential_blob rows) is
deferred to Milestone 3. Changing the key without rotation will invalidate all
existing credentials.
"""

from cryptography.fernet import Fernet

from app.core.config import settings

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
