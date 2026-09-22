import asyncio
import sys
from pathlib import Path
import re

# Add backend to python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import AsyncSessionLocal
from app.models import Product, Category, ProductImage
from sqlalchemy import select

PRODUCTS_DATA = [
    {
        "name": "Premium Black Textured Leather Belt",
        "description": "Upgrade your everyday style with this premium black leather belt, featuring a textured finish, durable construction, and a sleek metal buckle.",
        "price": 699.0,
        "mrp": 1199.0,
        "category_name": "Belts",
        "stock": 80,
        "unit": "piece",
        "weight": 0.25,
        "is_featured": True,
        "tags": ["belt", "leather", "black", "formal"],
        "image_url": "/uploads/products/black_leather_belt.webp",
    },
    {
        "name": "Classic Brown Leather Wallet",
        "description": "Handcrafted brown leather bifold wallet with multiple card slots and a secure cash compartment. Built for daily carry.",
        "price": 899.0,
        "mrp": 1499.0,
        "category_name": "Wallets",
        "stock": 70,
        "unit": "piece",
        "weight": 0.15,
        "is_featured": True,
        "tags": ["wallet", "leather", "brown", "bifold"],
        "image_url": "/uploads/products/brown_leather_wallet.webp",
    },
    {
        "name": "Minimal Leather Card Holder",
        "description": "Slim leather card holder designed for essential cards only. Clean edges and a soft hand-feel.",
        "price": 449.0,
        "mrp": 799.0,
        "category_name": "Card Holders",
        "stock": 120,
        "unit": "piece",
        "weight": 0.08,
        "is_featured": True,
        "tags": ["card holder", "leather", "minimal", "slim"],
        "image_url": "/uploads/products/leather_card_holder.webp",
    },
    {
        "name": "Everyday Leather Crossbody Bag",
        "description": "Compact leather crossbody bag with an adjustable strap and secure zip closure. Ideal for travel and daily errands.",
        "price": 2499.0,
        "mrp": 3999.0,
        "category_name": "Bags",
        "stock": 40,
        "unit": "piece",
        "weight": 0.6,
        "is_featured": True,
        "tags": ["bag", "leather", "crossbody", "travel"],
        "image_url": "/uploads/products/leather_crossbody.webp",
    },
    {
        "name": "Leather Key Fob",
        "description": "Premium leather key fob with solid hardware. A small accessory with lasting craftsmanship.",
        "price": 299.0,
        "mrp": 499.0,
        "category_name": "Accessories",
        "stock": 150,
        "unit": "piece",
        "weight": 0.05,
        "is_featured": False,
        "tags": ["key fob", "leather", "accessory"],
        "image_url": "/uploads/products/leather_key_fob.webp",
    },
]

def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s

async def seed_products():
    async with AsyncSessionLocal() as session:
        for data in PRODUCTS_DATA:
            cat_result = await session.execute(
                select(Category).where(Category.name == data["category_name"])
            )
            category = cat_result.scalar_one_or_none()
            if not category:
                category = Category(
                    name=data["category_name"],
                    slug=slugify(data["category_name"]),
                    is_active=True,
                )
                session.add(category)
                await session.flush()

            existing = await session.execute(
                select(Product).where(Product.slug == slugify(data["name"]))
            )
            if existing.scalar_one_or_none():
                continue

            product = Product(
                name=data["name"],
                slug=slugify(data["name"]),
                description=data["description"],
                price=data["price"],
                mrp=data["mrp"],
                category=data["category_name"],
                category_id=category.id,
                stock=data["stock"],
                unit=data["unit"],
                weight=data["weight"],
                is_featured=data["is_featured"],
                is_active=True,
                tags=data["tags"],
            )
            session.add(product)
            await session.flush()

            if data.get("image_url"):
                session.add(
                    ProductImage(
                        product_id=product.id,
                        url=data["image_url"],
                        position=0,
                    )
                )

        await session.commit()
        print("Lansdowne sample products seeded")


if __name__ == "__main__":
    asyncio.run(seed_products())
