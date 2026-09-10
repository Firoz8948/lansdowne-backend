"""One-off: replace old cookware categories with ChaklaDekho categories via SQL."""
import asyncio
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

NEW = [
    ("Chakla", "chakla", 0),
    ("Tawa", "tawa", 1),
    ("Belan / Rolling Pin", "belan-rolling-pin", 2),
    ("Serving Spoon", "serving-spoon", 3),
    ("Spatula", "spatula", 4),
    ("Mortar and Pestle", "mortar-and-pestle", 5),
]


async def main():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL not set")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(url)
    conn = await asyncpg.connect(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=(parsed.path or "/").lstrip("/") or "postgres",
    )
    try:
        cols = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'categories'
            """
        )
        col_names = {r["column_name"] for r in cols}
        print("Category columns:", sorted(col_names))

        cats = await conn.fetch("SELECT id, name, slug FROM categories ORDER BY id")
        print("Current:", [(r["id"], r["name"], r["slug"]) for r in cats])

        # Unmap products
        await conn.execute("UPDATE products SET category_id = NULL")

        keep_slugs = {slug for _, slug, _ in NEW} | {"reels"}
        keep_names = {name for name, _, _ in NEW} | {"Reels"}

        for r in cats:
            if r["slug"] in keep_slugs or r["name"] in keep_names:
                continue
            await conn.execute("DELETE FROM categories WHERE id = $1", r["id"])
            print("Removed", r["name"])

        for name, slug, pos in NEW:
            existing = await conn.fetchrow(
                "SELECT id FROM categories WHERE slug = $1 OR name = $2",
                slug,
                name,
            )
            if existing:
                await conn.execute(
                    """
                    UPDATE categories
                    SET name = $1, slug = $2, position = $3, is_active = true
                    WHERE id = $4
                    """,
                    name,
                    slug,
                    pos,
                    existing["id"],
                )
                print("Updated", name)
            else:
                await conn.execute(
                    """
                    INSERT INTO categories (name, slug, position, is_active)
                    VALUES ($1, $2, $3, true)
                    """,
                    name,
                    slug,
                    pos,
                )
                print("Added", name)

        cats = await conn.fetch("SELECT id, name, slug FROM categories ORDER BY position, id")
        print("Final:", [(r["id"], r["name"], r["slug"]) for r in cats])
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
