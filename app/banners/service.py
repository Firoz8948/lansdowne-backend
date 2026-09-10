from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BannerSlide


def serialize_banner(slide: BannerSlide) -> dict:
    return {
        "id": slide.id,
        "device": slide.device,
        "image_url": slide.image_url,
        "title": slide.title,
        "title_highlight": slide.title_highlight,
        "subtitle": slide.subtitle,
        "link_url": slide.link_url,
        "position": slide.position,
        "is_active": slide.is_active,
        "created_at": slide.created_at.isoformat() if slide.created_at else None,
        "updated_at": slide.updated_at.isoformat() if slide.updated_at else None,
    }


async def list_banners(
    db: AsyncSession,
    device: str | None = None,
    active_only: bool = False,
) -> list[dict]:
    q = select(BannerSlide)
    if device:
        q = q.where(BannerSlide.device == device)
    if active_only:
        q = q.where(BannerSlide.is_active == True)  # noqa: E712
    q = q.order_by(BannerSlide.position.asc(), BannerSlide.id.asc())
    result = await db.execute(q)
    return [serialize_banner(s) for s in result.scalars().all()]


async def create_banner(db: AsyncSession, data: dict) -> dict:
    slide = BannerSlide(**data)
    db.add(slide)
    await db.commit()
    await db.refresh(slide)
    return serialize_banner(slide)


async def update_banner(db: AsyncSession, banner_id: int, data: dict) -> dict | None:
    result = await db.execute(select(BannerSlide).where(BannerSlide.id == banner_id))
    slide = result.scalar_one_or_none()
    if not slide:
        return None
    for key, value in data.items():
        setattr(slide, key, value)
    await db.commit()
    await db.refresh(slide)
    return serialize_banner(slide)


async def delete_banner(db: AsyncSession, banner_id: int) -> bool:
    result = await db.execute(select(BannerSlide).where(BannerSlide.id == banner_id))
    slide = result.scalar_one_or_none()
    if not slide:
        return False
    await db.delete(slide)
    await db.commit()
    return True


async def set_banner_image(
    db: AsyncSession, banner_id: int, image_url: str
) -> dict | None:
    return await update_banner(db, banner_id, {"image_url": image_url})
