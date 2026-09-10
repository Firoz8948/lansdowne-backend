from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

from . import service

router = APIRouter()


@router.get("/facebook.xml")
@router.get("/facebook-feed.xml")
async def facebook_feed(db: AsyncSession = Depends(get_db)):
    products = await service.load_active_products(db)
    xml = service.build_facebook_rss(products)
    return Response(
        content=xml,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=1800"},
    )


@router.get("/google.xml")
@router.get("/google-merchant.xml")
async def google_merchant_feed(db: AsyncSession = Depends(get_db)):
    products = await service.load_active_products(db)
    xml = service.build_google_merchant_rss(products)
    return Response(
        content=xml,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=1800"},
    )
