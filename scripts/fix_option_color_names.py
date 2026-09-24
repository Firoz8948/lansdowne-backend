import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import ProductVariantOption


async def fix():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ProductVariantOption))
        rows = result.scalars().all()
        fixed = 0
        for o in rows:
            colors = list(o.colors or [])
            if not colors or not o.name:
                continue
            if len(colors) == 1 and (colors[0].get("name") or "") != o.name:
                print(
                    f"fix id={o.id} option={o.name!r} "
                    f"colors_name={colors[0].get('name')!r}"
                )
                colors[0] = {**colors[0], "name": o.name}
                o.colors = colors
                fixed += 1
        await db.commit()
        print("fixed", fixed)


if __name__ == "__main__":
    asyncio.run(fix())
