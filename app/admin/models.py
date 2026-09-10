from app.common import utcnow


def new_admin_doc(email: str, hashed_password: str, name: str = "Administrator") -> dict:
    now = utcnow()
    return {
        "email": email,
        "password": hashed_password,
        "name": name,
        "role": "admin",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
