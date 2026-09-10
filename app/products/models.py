import re

from app.common import utcnow


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def new_product_doc(data: dict, slug: str) -> dict:
    now = utcnow()
    doc = {**data, "slug": slug, "created_at": now, "updated_at": now}
    if "images" not in doc:
        doc["images"] = []
    if "variants" not in doc:
        doc["variants"] = []
    if "tags" not in doc:
        doc["tags"] = []
    return doc


def new_category_doc(data: dict, slug: str) -> dict:
    now = utcnow()
    return {
        **data,
        "slug": slug,
        "created_at": now,
        "updated_at": now,
    }
