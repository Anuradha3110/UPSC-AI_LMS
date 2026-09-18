"""
Password hashing + JWT issuing/decoding for MOD-01 (Identity & Access).

Calls the bcrypt package directly rather than going through passlib's
CryptContext — passlib (unmaintained since 2020) reads
`bcrypt.__about__.__version__`, which bcrypt 4.1+ removed, and its
fallback path is broken. Fewer moving parts this way.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

_MAX_BCRYPT_BYTES = 72  # bcrypt's own hard limit — truncate rather than error


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:_MAX_BCRYPT_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")[:_MAX_BCRYPT_BYTES]
    return bcrypt.checkpw(raw, password_hash.encode("utf-8"))


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
