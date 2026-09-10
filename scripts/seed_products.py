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
        "name": "Wooden Chakla (12 inch)",
        "description": "Smooth wooden chakla for rolling rotis, parathas, and puris. Stable base and even surface for everyday kitchen use.",
        "price": 449.0,
        "mrp": 699.0,
        "category_name": "Chakla",
        "stock": 80,
        "unit": "piece",
        "weight": 1.2,
        "is_featured": True,
        "tags": ["chakla", "wooden", "roti", "kitchen"],
        "image_url": "/uploads/products/wooden_chakla.webp",
    },
    {
        "name": "Iron Roti Tawa (10 inch)",
        "description": "Traditional iron tawa for soft rotis and crisp parathas. Even heat distribution for daily cooking.",
        "price": 549.0,
        "mrp": 849.0,
        "category_name": "Tawa",
        "stock": 70,
        "unit": "piece",
        "weight": 1.6,
        "is_featured": True,
        "tags": ["tawa", "roti", "iron", "kitchen"],
        "image_url": "/uploads/products/iron_roti_tawa.webp",
    },
    {
        "name": "Wooden Belan / Rolling Pin",
        "description": "Handcrafted wooden belan with a comfortable grip. Ideal for rolling dough evenly on a chakla.",
        "price": 199.0,
        "mrp": 349.0,
        "category_name": "Belan / Rolling Pin",
        "stock": 120,
        "unit": "piece",
        "weight": 0.4,
        "is_featured": True,
        "tags": ["belan", "rolling pin", "wooden", "kitchen"],
        "image_url": "/uploads/products/wooden_belan.webp",
    },
    {
        "name": "Serving Spoon Set (3 pcs)",
        "description": "Set of 3 durable serving spoons for dal, sabzi, and rice. Comfortable handles for everyday serving.",
        "price": 299.0,
        "mrp": 499.0,
        "category_name": "Serving Spoon",
        "stock": 100,
        "unit": "set",
        "weight": 0.5,
        "is_featured": True,
        "tags": ["serving spoon", "kitchen", "utensils"],
        "image_url": "/uploads/products/serving_spoons.webp",
    },
    {
        "name": "Wooden Spatula Set (4 pcs)",
        "description": "Eco-friendly wooden spatulas for flipping, stirring, and sautéing. Gentle on cookware surfaces.",
        "price": 349.0,
        "mrp": 549.0,
        "category_name": "Spatula",
        "stock": 90,
        "unit": "set",
        "weight": 0.45,
        "is_featured": True,
        "tags": ["spatula", "wooden", "kitchen"],
        "image_url": "/uploads/products/wooden_spatulas.webp",
    },
    {
        "name": "Stone Mortar and Pestle",
        "description": "Classic mortar and pestle for grinding spices, chutneys, and pastes the traditional way.",
        "price": 599.0,
        "mrp": 899.0,
        "category_name": "Mortar and Pestle",
        "stock": 50,
        "unit": "set",
        "weight": 2.5,
        "is_featured": True,
        "tags": ["mortar", "pestle", "spices", "kitchen"],
        "image_url": "/uploads/products/mortar_pestle.webp",
    },
]

def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s

async def seed_products():
    async with AsyncSessionLocal() as session:
        # First, ensure all categories exist
        category_names = set(p["category_name"] for p in PRODUCTS_DATA)
        for cat_name in category_names:
            cat_slug = slugify(cat_name)
            existing_cat = (
                await session.execute(select(Category).where(Category.slug == cat_slug))
            ).scalar_one_or_none()
            if not existing_cat:
                new_cat = Category(
                    name=cat_name,
                    slug=cat_slug,
                    is_active=True,
                    position=10 # general position
                )
                session.add(new_cat)
                print(f"Created category: {cat_name}")
        
        await session.commit()
        
        # Load categories into a mapping dict by slug
        cat_result = await session.execute(select(Category))
        categories = {c.slug: c for c in cat_result.scalars().all()}
        
        # Clear existing products to avoid duplicates in seeding
        # This makes it easy to run the script multiple times
        existing_products = (await session.execute(select(Product))).scalars().all()
        for ep in existing_products:
            await session.delete(ep)
        await session.commit()
        print("Cleared old products.")

        # Seed products
        for p_data in PRODUCTS_DATA:
            cat = categories[slugify(p_data["category_name"])]
            product = Product(
                name=p_data["name"],
                slug=slugify(p_data["name"]),
                description=p_data["description"],
                price=p_data["price"],
                mrp=p_data["mrp"],
                category_id=cat.id,
                category=cat.name,
                stock=p_data["stock"],
                unit=p_data["unit"],
                weight=p_data["weight"],
                is_featured=p_data["is_featured"],
                is_active=True,
                tags=p_data["tags"],
                metafields={}
            )
            session.add(product)
            await session.flush() # flush to get product.id

            # Add product image
            product_image = ProductImage(
                product_id=product.id,
                url=p_data["image_url"],
                position=0
            )
            session.add(product_image)
            print(f"Seeded product: {product.name}")
        
        await session.commit()
        print("All products seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_products())
