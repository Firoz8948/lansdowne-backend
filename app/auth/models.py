"""Document shapes for the auth module (users, otps collections)."""
from app.common import utcnow


def new_user_doc(phone: str, name: str | None = None) -> dict:
    now = utcnow()
    return {
        "phone": phone,
        "name": name,
        "email": None,
        "role": "user",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


def new_otp_doc(phone: str, otp: str, expires_at) -> dict:
    return {
        "phone": phone,
        "otp": otp,
        "verified": False,
        "created_at": utcnow(),
        "expires_at": expires_at,
    }
