import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common import serialize_product
from app.models import Category, Product, ProductVariant


def slugify(name: str) -> str:
    value = name.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[\s_-]+", "-", value)


async def _unique_slug(
    db: AsyncSession,
    base: str,
    exclude_id: int | None = None,
) -> str:
    slug = slugify(base) or "category"
    query = select(Category).where(Category.slug == slug)
    if exclude_id is not None:
        query = query.where(Category.id != exclude_id)
    if (await db.execute(query)).scalar_one_or_none() is None:
        return slug
    return f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"


def serialize_category(category: Category, product_count: int = 0) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "image_url": category.image_url,
        "seo_title": getattr(category, "seo_title", None) or "",
        "seo_description": getattr(category, "seo_description", None) or "",
        "is_active": category.is_active,
        "position": category.position,
        "is_reels": bool(category.is_reels),
        "product_count": product_count,
        "created_at": category.created_at.isoformat() if category.created_at else None,
        "updated_at": category.updated_at.isoformat() if category.updated_at else None,
    }


async def _product_counts(db: AsyncSession) -> dict[int, int]:
    rows = await db.execute(
        select(Product.category_id, func.count(Product.id))
        .where(Product.category_id.is_not(None))
        .group_by(Product.category_id)
    )
    return {category_id: count for category_id, count in rows.all()}


async def get_all_categories(
    db: AsyncSession,
    include_inactive: bool = False,
) -> list:
    query = select(Category).order_by(Category.position, Category.name)
    if not include_inactive:
        query = query.where(Category.is_active == True)  # noqa: E712
    categories = (await db.execute(query)).scalars().all()
    counts = await _product_counts(db)
    return [serialize_category(cat, counts.get(cat.id, 0)) for cat in categories]


async def get_category_by_id(
    db: AsyncSession,
    category_id: int,
) -> Optional[dict]:
    category = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if category is None:
        return None
    count = (
        await db.execute(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
    ).scalar() or 0
    return serialize_category(category, count)


async def get_category_by_slug(db: AsyncSession, slug: str) -> Optional[dict]:
    category = (
        await db.execute(
            select(Category).where(
                Category.slug == slug,
                Category.is_active == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if category is None:
        return None
    count = (
        await db.execute(
            select(func.count(Product.id)).where(Product.category_id == category.id)
        )
    ).scalar() or 0
    return serialize_category(category, count)


async def create_category(db: AsyncSession, data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Category name is required")
    data["name"] = name

    existing = (
        await db.execute(
            select(Category).where(func.lower(Category.name) == func.lower(name))
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Category '{name}' already exists")

    category = Category(
        slug=await _unique_slug(db, name),
        **data,
    )
    db.add(category)
    await db.commit()
    return await get_category_by_id(db, category.id)


async def update_category(
    db: AsyncSession,
    category_id: int,
    data: dict,
) -> Optional[dict]:
    category = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if category is None:
        return None

    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        if not name:
            raise ValueError("Category name cannot be empty")
        existing = (
            await db.execute(
                select(Category).where(
                    func.lower(Category.name) == func.lower(name),
                    Category.id != category_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Category '{name}' already exists")
        data["name"] = name

    data = {key: value for key, value in data.items() if key not in ("is_reels", "slug")}
    for key, value in data.items():
        if hasattr(category, key) and value is not None:
            setattr(category, key, value)

    if category.is_reels:
        category.slug = "reels"
    elif data.get("name"):
        category.slug = await _unique_slug(
            db,
            data["name"],
            exclude_id=category.id,
        )

    await db.execute(
        update(Product)
        .where(Product.category_id == category.id)
        .values(category=category.name)
    )
    await db.commit()
    return await get_category_by_id(db, category_id)


async def delete_category(db: AsyncSession, category_id: int) -> bool:
    category = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if category is None:
        return False
    if category.is_reels:
        raise ValueError("Reels category cannot be deleted")

    await db.execute(
        update(Product)
        .where(Product.category_id == category_id)
        .values(category_id=None)
    )
    await db.delete(category)
    await db.commit()
    return True


async def set_category_image(
    db: AsyncSession,
    category_id: int,
    image_url: str,
) -> Optional[dict]:
    category = (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()
    if category is None:
        return None
    category.image_url = image_url
    await db.commit()
    return await get_category_by_id(db, category_id)


async def get_category_products(
    db: AsyncSession,
    category_id: int,
    page: int = 1,
    limit: int = 20,
) -> dict:
    filter_by_category = Product.category_id == category_id
    total = (
        await db.execute(select(func.count(Product.id)).where(filter_by_category))
    ).scalar() or 0
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
            selectinload(Product.category_rel),
        )
        .where(filter_by_category)
        .order_by(Product.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    products = [serialize_product(product) for product in result.scalars().all()]
    return {"products": products, "total": total, "page": page, "limit": limit}


async def resolve_product_category_fields(
    db: AsyncSession,
    category_id: int | None,
) -> dict:
    if not category_id:
        return {}
    category = (
        await db.execute(select(Category).where(Category.id == int(category_id)))
    ).scalar_one_or_none()
    if category is None:
        return {}
    return {
        "category_id": category.id,
        "category": category.name[:100],
    }
