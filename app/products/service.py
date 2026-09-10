import math
import re

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common import serialize_product, utcnow
from app.database import AsyncSessionLocal
from app.models import Category, Product, ProductImage, ProductVariant, ProductVariantOption


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def _unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    counter = 1
    while True:
        result = await db.execute(select(Product).where(Product.slug == slug))
        if not result.scalar_one_or_none():
            return slug
        counter += 1
        slug = f"{base}-{counter}"


async def create_product(data: dict) -> dict:
    async with AsyncSessionLocal() as db:
        slug = await _unique_slug(db, data["name"])
        variants_data = data.pop("variants", []) or []
        product = Product(slug=slug, **data)
        db.add(product)
        await db.flush()
        for var_data in variants_data:
            variant = ProductVariant(product_id=product.id, name=var_data["name"])
            db.add(variant)
            await db.flush()
            for opt_data in var_data.get("options", []):
                db.add(ProductVariantOption(variant_id=variant.id, **opt_data))
        await db.commit()
        return await get_product_by_id(product.id)


async def list_products(
    page: int = 1,
    page_size: int = 12,
    category: str | None = None,
    category_slug: str | None = None,
    search: str | None = None,
    featured: bool | None = None,
    sort: str | None = None,
    include_inactive: bool = False,
) -> dict:
    async with AsyncSessionLocal() as db:
        query = select(Product).options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
            selectinload(Product.category_rel),
        )
        count_query = select(func.count(Product.id))

        if not include_inactive:
            query = query.where(Product.is_active == True)  # noqa: E712
            count_query = count_query.where(Product.is_active == True)  # noqa: E712

        if category_slug:
            cat_result = await db.execute(
                select(Category).where(Category.slug == category_slug)
            )
            cat = cat_result.scalar_one_or_none()
            if cat:
                filt = Product.category_id == cat.id
                query = query.where(filt)
                count_query = count_query.where(filt)
            else:
                query = query.where(Product.id == -1)
                count_query = count_query.where(Product.id == -1)
        elif category:
            query = query.where(Product.category.ilike(f"%{category}%"))
            count_query = count_query.where(Product.category.ilike(f"%{category}%"))

        if featured is not None:
            query = query.where(Product.is_featured == featured)
            count_query = count_query.where(Product.is_featured == featured)
        if search:
            pattern = f"%{search}%"
            filt = or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                Product.category.ilike(pattern),
            )
            query = query.where(filt)
            count_query = count_query.where(filt)

        sort_map = {
            "price_asc": Product.price.asc(),
            "price_desc": Product.price.desc(),
            "newest": Product.created_at.desc(),
            "name_asc": Product.name.asc(),
        }
        order_col = sort_map.get(sort or "newest", Product.created_at.desc())

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size

        total = (await db.execute(count_query)).scalar() or 0
        result = await db.execute(
            query.order_by(order_col).offset(skip).limit(page_size)
        )
        items = [serialize_product(p) for p in result.scalars().all()]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total else 0,
        }


async def get_product_by_slug(slug: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.options),
                selectinload(Product.category_rel),
            )
            .where(Product.slug == slug, Product.is_active == True)  # noqa: E712
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return serialize_product(product)


async def get_product_by_id(product_id: int | str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.options),
                selectinload(Product.category_rel),
            )
            .where(Product.id == int(product_id))
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return serialize_product(product)


async def update_product(product_id: int | str, updates: dict) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.options),
                selectinload(Product.category_rel),
            )
            .where(Product.id == int(product_id))
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        updates = {k: v for k, v in updates.items() if v is not None}
        if "name" in updates and updates["name"] != product.name:
            updates["slug"] = await _unique_slug(db, updates["name"])
        for key, value in updates.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.updated_at = utcnow()
        await db.commit()
        return serialize_product(product)


async def delete_product(product_id: int | str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Product).where(Product.id == int(product_id)))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        await db.delete(product)
        await db.commit()
        return {"message": "Product deleted"}


async def add_product_images(product_id: int | str, image_urls: list[str]) -> dict:
    async with AsyncSessionLocal() as db:
        pid = int(product_id)
        result = await db.execute(select(Product).where(Product.id == pid))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Product not found")
        pos_result = await db.execute(
            select(func.max(ProductImage.position)).where(ProductImage.product_id == pid)
        )
        max_pos = pos_result.scalar() or -1
        for i, url in enumerate(image_urls):
            db.add(ProductImage(product_id=pid, url=url, position=max_pos + i + 1))
        await db.commit()
        return await get_product_by_id(pid)


async def remove_product_image(product_id: int | str, image_url: str) -> dict:
    async with AsyncSessionLocal() as db:
        pid = int(product_id)
        result = await db.execute(
            select(ProductImage).where(
                ProductImage.product_id == pid, ProductImage.url == image_url
            )
        )
        img = result.scalar_one_or_none()
        if img:
            await db.delete(img)
            await db.commit()
        return await get_product_by_id(pid)


async def list_categories() -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product.category)
            .where(Product.is_active == True)  # noqa: E712
            .distinct()
            .order_by(Product.category)
        )
        return [
            {"name": row[0], "slug": slugify(row[0])}
            for row in result.all()
            if row[0]
        ]
