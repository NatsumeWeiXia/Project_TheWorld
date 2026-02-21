from __future__ import annotations

import base64
import hashlib
import hmac
import os
from secrets import token_bytes


class SecretCipher:
    def __init__(self, secret_key: str):
        if not secret_key or len(secret_key.strip()) < 16:
            raise ValueError("secret key must be at least 16 characters")
        self._secret = secret_key.encode("utf-8")

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        out = bytearray()
        counter = 0
        while len(out) < length:
            block = hashlib.sha256(self._secret + nonce + counter.to_bytes(4, "big")).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:length])

    def encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = token_bytes(12)
        stream = self._keystream(nonce, len(raw))
        ciphertext = bytes(a ^ b for a, b in zip(raw, stream))
        tag = hmac.new(self._secret, nonce + ciphertext, hashlib.sha256).digest()[:16]
        packed = nonce + tag + ciphertext
        return base64.urlsafe_b64encode(packed).decode("ascii")

    def decrypt(self, token: str) -> str:
        packed = base64.urlsafe_b64decode(token.encode("ascii"))
        nonce = packed[:12]
        tag = packed[12:28]
        ciphertext = packed[28:]
        expected_tag = hmac.new(self._secret, nonce + ciphertext, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("invalid secret token")
        stream = self._keystream(nonce, len(ciphertext))
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, stream))
        return plaintext.decode("utf-8")


def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"
