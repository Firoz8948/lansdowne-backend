from app.common import serialize_contact
from app.database import AsyncSessionLocal
from app.models import Contact


async def submit(data: dict) -> dict:
    async with AsyncSessionLocal() as db:
        contact = Contact(
            name=data["name"],
            email=data["email"],
            phone=data.get("phone"),
            subject=data.get("subject"),
            message=data["message"],
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return serialize_contact(contact)


async def list_messages() -> list[dict]:
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(select(Contact).order_by(Contact.created_at.desc()))
        return [serialize_contact(c) for c in result.scalars().all()]
