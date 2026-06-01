# Copyright © 2026 Network Logic Limited. All rights reserved.

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.config import settings

# We use the bcrypt library directly rather than passlib — passlib 1.7.4 is
# unmaintained and crashes on bcrypt >= 4.1 (its internal self-test raises
# "password cannot be longer than 72 bytes"). bcrypt itself is stable.

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24        # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS   = 30


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; truncate to stay within the limit.
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire, "type": "access"},
        settings.SECRET_KEY, algorithm="HS256"
    )

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY, algorithm="HS256"
    )

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
