"""Product catalog feeds for Meta Commerce Manager and Google Merchant Center."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Product


def _site_url() -> str:
    """Canonical storefront URL for feed product links (must match Merchant claimed URL)."""
    url = (settings.FRONTEND_URL or "https://www.chakladekho.com").rstrip("/")
    # Prefer www — Merchant Center is claimed as https://www.chakladekho.com
    if url in {"https://chakladekho.com", "http://chakladekho.com"}:
        return "https://www.chakladekho.com"
    return url


def _cdn_base() -> str:
    return (settings.BUNNY_CDN_URL or "").rstrip("/")


def _abs_image(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    cdn = _cdn_base()
    if cdn:
        return f"{cdn}/{url.lstrip('/')}"
    # Legacy local uploads — expose via frontend rewrite or absolute API later
    return url


def _clean_text(value: str | None, limit: int = 5000) -> str:
    if not value:
        return ""
    text = (
        str(value)
        .replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _price(amount: float | None) -> str:
    return f"{float(amount or 0):.2f} INR"


async def load_active_products(db: AsyncSession) -> list[Product]:
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.images))
        .where(Product.is_active == True)  # noqa: E712
        .order_by(Product.id.asc())
    )
    return list(result.scalars().all())


def product_to_feed_row(product: Product) -> dict:
    images = sorted(product.images or [], key=lambda i: i.position or 0)
    primary = _abs_image(images[0].url) if images else ""
    extra = [_abs_image(img.url) for img in images[1:5] if img.url]
    availability = "in stock" if (product.stock or 0) > 0 else "out of stock"
    description = _clean_text(product.description) or _clean_text(
        f"{product.name} — premium iron cookware from {settings.APP_NAME}"
    )
    link = f"{_site_url()}/product/{product.slug}"
    row = {
        "id": str(product.id),
        "title": _clean_text(product.name, 150),
        "description": description or product.name,
        "availability": availability,
        "condition": "new",
        "price": _price(product.mrp if product.mrp and product.mrp > 0 else product.price),
        "sale_price": None,
        "link": link,
        "image_link": primary,
        "additional_image_link": extra,
        "brand": settings.APP_NAME,
        "product_type": _clean_text(product.category, 200) or "Cookware",
        "google_product_category": "Home & Garden > Kitchen & Dining > Cookware",
    }
    if product.mrp and product.price and product.mrp > product.price:
        row["price"] = _price(product.mrp)
        row["sale_price"] = _price(product.price)
    else:
        row["price"] = _price(product.price)
    return row


def build_facebook_rss(products: list[Product]) -> str:
    site = _site_url()
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for p in products:
        row = product_to_feed_row(p)
        if not row["image_link"] or not row["title"]:
            continue
        extra_xml = "".join(
            f"<g:additional_image_link>{escape(u)}</g:additional_image_link>"
            for u in row["additional_image_link"]
            if u
        )
        sale = (
            f"<g:sale_price>{escape(row['sale_price'])}</g:sale_price>"
            if row.get("sale_price")
            else ""
        )
        items.append(
            f"""
    <item>
      <g:id>{escape(row['id'])}</g:id>
      <g:title>{escape(row['title'])}</g:title>
      <g:description>{escape(row['description'])}</g:description>
      <g:availability>{escape(row['availability'])}</g:availability>
      <g:condition>{escape(row['condition'])}</g:condition>
      <g:price>{escape(row['price'])}</g:price>
      {sale}
      <g:link>{escape(row['link'])}</g:link>
      <g:image_link>{escape(row['image_link'])}</g:image_link>
      {extra_xml}
      <g:brand>{escape(row['brand'])}</g:brand>
      <g:identifier_exists>false</g:identifier_exists>
      <g:product_type>{escape(row['product_type'])}</g:product_type>
      <g:google_product_category>{escape(row['google_product_category'])}</g:google_product_category>
    </item>"""
        )

    body = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>{escape(settings.APP_NAME)} Product Feed</title>
    <link>{escape(site)}</link>
    <description>Product catalog feed for Meta Commerce / Google Merchant</description>
    <lastBuildDate>{now}</lastBuildDate>
{body}
  </channel>
</rss>
"""


def build_google_merchant_rss(products: list[Product]) -> str:
    # Same Google namespace format; Meta and Google both accept g: fields
    return build_facebook_rss(products)
