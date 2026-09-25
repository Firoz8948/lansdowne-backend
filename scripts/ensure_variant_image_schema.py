"""Ensure product color/variant image columns exist (safe to re-run).

Usage on EC2:
  cd /path/to/backend
  ./venv/bin/python scripts/ensure_variant_image_schema.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database import engine


STATEMENTS = [
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS colors JSONB DEFAULT '[]'",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS color_group_id VARCHAR(36)",
    "CREATE INDEX IF NOT EXISTS ix_products_color_group_id ON products(color_group_id)",
    "ALTER TABLE product_variant_options ADD COLUMN IF NOT EXISTS hex VARCHAR(7)",
    "ALTER TABLE product_variant_options ADD COLUMN IF NOT EXISTS colors JSONB DEFAULT '[]'",
    "ALTER TABLE product_variant_options ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
    "ALTER TABLE product_variant_options ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'",
    """
    UPDATE product_variant_options
    SET images = jsonb_build_array(image_url)
    WHERE image_url IS NOT NULL
      AND image_url <> ''
      AND (images IS NULL OR images = '[]'::jsonb)
    """,
]


async def main() -> None:
    async with engine.begin() as conn:
        for stmt in STATEMENTS:
            await conn.execute(text(stmt))
            print("OK:", " ".join(stmt.split())[:80])
    print("Schema ensure complete.")


if __name__ == "__main__":
    asyncio.run(main())
