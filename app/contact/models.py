from app.common import utcnow


def new_contact_doc(data: dict) -> dict:
    return {
        **data,
        "is_read": False,
        "created_at": utcnow(),
    }
