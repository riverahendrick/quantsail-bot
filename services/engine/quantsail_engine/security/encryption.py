"""AES-GCM encryption helpers for engine-side key decryption."""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class DecryptedCredentials:
    api_key: str
    secret_key: str


class EncryptionService:
    """AES-GCM decryption service for exchange keys."""

    def __init__(self) -> None:
        key_hex = os.environ.get("MASTER_KEY")
        if not key_hex:
            raise RuntimeError("MASTER_KEY environment variable is required.")
        try:
            key = bytes.fromhex(key_hex)
        except ValueError as exc:
            raise RuntimeError("MASTER_KEY must be a valid hex string.") from exc
        if len(key) != 32:
            raise RuntimeError("MASTER_KEY must be 32 bytes (64 hex chars).")
        self._aesgcm = AESGCM(key)

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> DecryptedCredentials:
        """Decrypt ciphertext into API key + secret key pair."""
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
        if ":" not in plaintext:
            raise RuntimeError("Invalid key payload format.")
        api_key, secret_key = plaintext.split(":", maxsplit=1)
        return DecryptedCredentials(api_key=api_key, secret_key=secret_key)
