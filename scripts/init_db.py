"""Create database if missing, create all tables, and seed default admin user."""

import asyncio
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import connect_db, disconnect_db


async def ensure_database():
    url = settings.DATABASE_URL
    # strip driver prefix like postgresql+asyncpg:// -> postgresql://
    if "+" in url.split("://")[0]:
        driver, rest = url.split("://", 1)
        url_clean = f"postgresql://{rest}"
    else:
        url_clean = url

    parsed = urlparse(url_clean)
    db_name = parsed.path.lstrip("/")
    user = unquote(parsed.username or "postgres")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    # Connect to default 'postgres' database
    conn = await asyncpg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database: {db_name}")
        else:
            print(f"Database '{db_name}' already exists.")
    finally:
        await conn.close()


async def main():
    print("Checking database existence...")
    await ensure_database()
    print("Connecting to DB, migrating schema, and seeding admin...")
    await connect_db()
    await disconnect_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
