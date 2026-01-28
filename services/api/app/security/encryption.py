from __future__ import annotations

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionService:
    """
    AES-GCM encryption service for sensitive data (API keys).
    Requires 'MASTER_KEY' env var (hex-encoded 32 bytes).
    """

    def __init__(self) -> None:
        key_hex = os.environ.get("MASTER_KEY")
        if not key_hex:
            # Fallback for dev/test ONLY if explicit flag not set, 
            # but per GLOBAL_RULES we shouldn't fail silently or use mocks in prod.
            # We'll raise error if missing.
            raise RuntimeError("MASTER_KEY environment variable is required.")
        
        try:
            self.key = bytes.fromhex(key_hex)
        except ValueError:
             raise RuntimeError("MASTER_KEY must be a valid hex string.")

        if len(self.key) != 32: # 256 bits
             raise RuntimeError("MASTER_KEY must be 32 bytes (64 hex chars).")

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-GCM.
        Returns (ciphertext, nonce).
        """
        nonce = os.urandom(12) # NIST recommended 96-bit nonce
        data = plaintext.encode("utf-8")
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return ciphertext, nonce

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> str:
        """
        Decrypt ciphertext using AES-GCM.
        """
        plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")

_service: EncryptionService | None = None

def get_encryption_service() -> EncryptionService:
    """Singleton accessor."""
    global _service
    if _service is None:
        _service = EncryptionService()
    return _service
