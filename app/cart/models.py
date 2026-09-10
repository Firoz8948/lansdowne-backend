from app.common import utcnow


def new_cart_doc(user_id: str) -> dict:
    now = utcnow()
    return {
        "user_id": user_id,
        "items": [],
        "created_at": now,
        "updated_at": now,
    }
