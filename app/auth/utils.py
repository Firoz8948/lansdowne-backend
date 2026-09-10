import bcrypt
import random
from datetime import timedelta

from jose import JWTError, jwt

from app.common import utcnow
from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_otp(length: int | None = None) -> str:
    length = length or settings.OTP_LENGTH
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode.update({"exp": utcnow() + timedelta(minutes=minutes), "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "type": "refresh",
        }
    )
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None
