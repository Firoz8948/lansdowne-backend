import re

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MetafieldDefinition


def slugify_key(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s or "field"


def serialize_definition(defn: MetafieldDefinition) -> dict:
    return {
        "id": str(defn.id),
        "name": defn.name,
        "key": defn.key,
        "position": defn.position,
        "is_active": defn.is_active,
    }


async def list_definitions(db: AsyncSession, active_only: bool = False) -> list[dict]:
    query = select(MetafieldDefinition).order_by(
        MetafieldDefinition.position, MetafieldDefinition.id
    )
    if active_only:
        query = query.where(MetafieldDefinition.is_active.is_(True))
    result = await db.execute(query)
    return [serialize_definition(d) for d in result.scalars().all()]


async def create_definition(db: AsyncSession, name: str) -> dict:
    key = slugify_key(name)
    existing = (
        await db.execute(select(MetafieldDefinition).where(MetafieldDefinition.key == key))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A metafield with this name already exists")

    pos_result = await db.execute(select(func.max(MetafieldDefinition.position)))
    max_pos = pos_result.scalar() or -1

    defn = MetafieldDefinition(name=name.strip(), key=key, position=max_pos + 1)
    db.add(defn)
    await db.commit()
    await db.refresh(defn)
    return serialize_definition(defn)


async def update_definition(
    db: AsyncSession, definition_id: int, data: dict
) -> dict | None:
    result = await db.execute(
        select(MetafieldDefinition).where(MetafieldDefinition.id == definition_id)
    )
    defn = result.scalar_one_or_none()
    if not defn:
        return None

    if "name" in data and data["name"]:
        defn.name = data["name"].strip()
    if data.get("position") is not None:
        defn.position = data["position"]
    if data.get("is_active") is not None:
        defn.is_active = data["is_active"]

    await db.commit()
    await db.refresh(defn)
    return serialize_definition(defn)


async def delete_definition(db: AsyncSession, definition_id: int) -> bool:
    result = await db.execute(
        select(MetafieldDefinition).where(MetafieldDefinition.id == definition_id)
    )
    defn = result.scalar_one_or_none()
    if not defn:
        return False
    await db.delete(defn)
    await db.commit()
    return True
