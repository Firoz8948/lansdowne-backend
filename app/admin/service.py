import logging
import re
import uuid
from datetime import datetime, timedelta

import bcrypt
from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.utils import create_access_token
from app.common import (
    serialize_admin,
    serialize_color_sibling,
    serialize_order,
    serialize_payment,
    serialize_product,
    utcnow,
    _normalize_colors,
)
from app.config import settings
from app.models import (
    Admin,
    Order,
    Payment,
    Product,
    ProductImage,
    ProductVariant,
    ProductVariantOption,
    User,
)

logger = logging.getLogger("admin")


def _clean_option_data(opt_data: dict) -> dict:
    from app.common import _normalize_hex

    colors = _normalize_colors(opt_data.get("colors"))
    hex_val = _normalize_hex(opt_data.get("hex"))
    opt_name = (opt_data.get("name") or "").strip()
    if not colors and hex_val:
        colors = [{"name": (opt_name or hex_val)[:80], "hex": hex_val}]
    if colors and not hex_val:
        hex_val = colors[0]["hex"]
    # Keep nested swatch name in sync with the option label (single-color options)
    if colors and opt_name:
        if len(colors) == 1:
            colors[0]["name"] = opt_name[:80]
        elif not (colors[0].get("name") or "").strip():
            colors[0]["name"] = opt_name[:80]

    images: list[str] = []
    raw_images = opt_data.get("images")
    if isinstance(raw_images, list):
        for u in raw_images:
            if isinstance(u, str) and u.strip():
                images.append(u.strip())
            elif isinstance(u, dict) and u.get("url"):
                images.append(str(u["url"]).strip())
    single = opt_data.get("image_url")
    if isinstance(single, str) and single.strip() and single.strip() not in images:
        images.insert(0, single.strip())
    # Dedupe preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for u in images:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    images = deduped[:12]

    return {
        "name": opt_data["name"],
        "price": opt_data["price"],
        "mrp": opt_data["mrp"],
        "stock": opt_data.get("stock", 0) or 0,
        "weight": opt_data.get("weight"),
        "hex": hex_val,
        "colors": colors,
        "image_url": images[0] if images else None,
        "images": images,
    }


async def attach_color_siblings(db: AsyncSession, products: list[dict]) -> list[dict]:
    group_ids = {p.get("color_group_id") for p in products if p.get("color_group_id")}
    if not group_ids:
        return products

    result = await db.execute(
        select(Product)
        .options(selectinload(Product.images))
        .where(
            Product.color_group_id.in_(group_ids),
            Product.is_active == True,  # noqa: E712
        )
    )
    by_group: dict[str, list] = {}
    for p in result.scalars().all():
        by_group.setdefault(p.color_group_id, []).append(serialize_color_sibling(p))

    for item in products:
        gid = item.get("color_group_id")
        if not gid:
            item["color_siblings"] = []
            continue
        siblings = by_group.get(gid, [])
        item["color_siblings"] = [
            {**s, "is_current": str(s["id"]) == str(item["id"])} for s in siblings
        ]
    return products


async def sync_color_group(
    db: AsyncSession,
    product: Product,
    sibling_ids: list | None,
) -> None:
    if sibling_ids is None:
        return

    ids: list[int] = []
    for raw in sibling_ids:
        try:
            cid = int(raw)
        except (TypeError, ValueError):
            continue
        if cid > 0 and cid != product.id and cid not in ids:
            ids.append(cid)

    old_group = product.color_group_id
    if old_group:
        existing = (
            await db.execute(select(Product).where(Product.color_group_id == old_group))
        ).scalars().all()
        keep = set(ids) | {product.id}
        for p in existing:
            if p.id not in keep:
                p.color_group_id = None

    if not ids:
        product.color_group_id = None
        return

    group_id = old_group or str(uuid.uuid4())
    product.color_group_id = group_id
    siblings = (
        await db.execute(select(Product).where(Product.id.in_(ids)))
    ).scalars().all()
    for p in siblings:
        p.color_group_id = group_id


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def login(db: AsyncSession, username: str, password: str) -> dict:
    username = (username or "").strip()
    if username == settings.ADMIN_USERNAME or username == settings.ADMIN_EMAIL:
        lookup_email = settings.ADMIN_EMAIL
    elif "@" in username:
        lookup_email = username
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    result = await db.execute(
        select(Admin).where(Admin.email == lookup_email, Admin.is_active == True)  # noqa: E712
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(password, admin.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    admin_data = serialize_admin(admin)
    token = create_access_token(
        {
            "sub": admin_data["id"],
            "email": admin_data["email"],
            "role": admin_data.get("role", "admin"),
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": admin_data,
    }


async def get_admin_by_id(db: AsyncSession, admin_id: int) -> dict | None:
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    return serialize_admin(admin) if admin else None


async def update_admin_profile(db: AsyncSession, admin_id: int, data: dict) -> dict:
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Brand name, notify phone, and notify email are locked (env-managed).
    locked = {"phone", "company_name", "notify_email", "brand_name", "email"}
    attempted = locked.intersection(data.keys())
    if attempted:
        raise HTTPException(
            status_code=403,
            detail=(
                "Brand name, mobile number, and email are locked. "
                "Update ADMIN_NOTIFY_* / BRAND_NAME in server .env if needed."
            ),
        )

    if "name" in data and data["name"] is not None:
        admin.name = str(data["name"]).strip() or admin.name

    admin.updated_at = utcnow()
    await db.commit()
    await db.refresh(admin)
    return serialize_admin(admin)


async def dashboard_stats(db: AsyncSession) -> dict:
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    total_products = (await db.execute(select(func.count(Product.id)))).scalar() or 0
    active_products = (
        await db.execute(
            select(func.count(Product.id)).where(Product.is_active == True)  # noqa: E712
        )
    ).scalar() or 0
    total_customers = (
        await db.execute(
            select(func.count(User.id)).where(User.role == "customer")
        )
    ).scalar() or 0
    total_shipped = (
        await db.execute(
            select(func.count(Order.id)).where(Order.order_status == "shipped")
        )
    ).scalar() or 0

    rev_result = await db.execute(
        select(func.sum(Order.total)).where(Order.payment_status == "paid")
    )
    total_revenue = float(rev_result.scalar() or 0.0)

    recent_result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(5)
    )
    recent_orders = [serialize_order(o) for o in recent_result.scalars().all()]

    revenue_trend = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        result = await db.execute(
            select(func.sum(Order.total)).where(
                and_(
                    Order.payment_status == "paid",
                    Order.created_at >= start,
                    Order.created_at < end,
                )
            )
        )
        revenue_trend.append(
            {"date": start.strftime("%d %b"), "revenue": float(result.scalar() or 0)}
        )

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_products": total_products,
        "active_products": active_products,
        "total_customers": total_customers,
        "total_shipped": total_shipped,
        "recent_orders": recent_orders,
        "revenue_trend": revenue_trend,
    }


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s


async def get_all_products(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    category: str | None = None,
    search: str | None = None,
) -> dict:
    query = select(Product).options(
        selectinload(Product.images),
        selectinload(Product.variants).selectinload(ProductVariant.options),
        selectinload(Product.category_rel),
        selectinload(Product.categories_m2m),
    )
    count_query = select(func.count(Product.id))

    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    if search:
        pattern = f"%{search}%"
        filt = Product.name.ilike(pattern) | Product.description.ilike(pattern)
        query = query.where(filt)
        count_query = count_query.where(filt)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    products = [serialize_product(p) for p in result.scalars().all()]
    products = await attach_color_siblings(db, products)
    return {"products": products, "total": total, "page": page, "limit": limit}


async def get_product_by_id(db: AsyncSession, product_id: int) -> dict | None:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
            selectinload(Product.category_rel),
            selectinload(Product.categories_m2m),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        return None
    data = serialize_product(product)
    await attach_color_siblings(db, [data])
    return data


async def create_product(db: AsyncSession, data: dict) -> dict:
    from app.categories import service as category_service

    variants_data = data.pop("variants", []) or []
    category_ids = data.pop("category_ids", None)
    category_id = data.pop("category_id", None)
    data.pop("category", None)
    sibling_ids = data.pop("color_sibling_ids", None)
    data.pop("color_group_id", None)
    data["colors"] = _normalize_colors(data.pop("colors", None))

    ids = await category_service.normalize_category_ids(category_ids, category_id)
    primary_id = ids[0] if ids else None
    cat_fields = await category_service.resolve_product_category_fields(db, primary_id)
    if cat_fields:
        data.update(cat_fields)
    elif not data.get("category"):
        data["category"] = "Uncategorised"

    slug = slugify(data["name"])
    existing = (
        await db.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    product = Product(slug=slug, **data)
    db.add(product)
    await db.flush()

    await category_service.sync_product_categories(
        db, product, ids, primary_id=primary_id
    )
    await sync_color_group(db, product, sibling_ids)

    for var_data in variants_data:
        variant = ProductVariant(product_id=product.id, name=var_data["name"])
        db.add(variant)
        await db.flush()
        for opt_data in var_data.get("options", []):
            db.add(
                ProductVariantOption(
                    variant_id=variant.id, **_clean_option_data(opt_data)
                )
            )

    await db.commit()
    return await get_product_by_id(db, product.id)


async def duplicate_product(db: AsyncSession, product_id: int) -> dict | None:
    """Clone a product with variants + images. Name becomes '(Copy) <original>'."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
            selectinload(Product.categories_m2m),
        )
        .where(Product.id == product_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        return None

    name = f"(Copy) {source.name}"
    slug = slugify(name)
    existing = (
        await db.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    clone = Product(
        name=name,
        slug=slug,
        description=source.description,
        price=source.price,
        mrp=source.mrp,
        category_id=source.category_id,
        category=source.category,
        stock=source.stock,
        unit=source.unit,
        weight=source.weight,
        length_cm=getattr(source, "length_cm", None),
        breadth_cm=getattr(source, "breadth_cm", None),
        height_cm=getattr(source, "height_cm", None),
        is_featured=False,
        is_active=False,
        metafields=dict(source.metafields or {}),
        colors=list(source.colors or []),
        color_group_id=None,
    )
    db.add(clone)
    await db.flush()

    from app.categories import service as category_service

    await category_service.sync_product_categories(
        db,
        clone,
        [c.id for c in (source.categories_m2m or [])],
        primary_id=source.category_id,
    )

    for img in source.images or []:
        db.add(
            ProductImage(
                product_id=clone.id,
                url=img.url,
                position=img.position,
            )
        )

    for var in source.variants or []:
        new_var = ProductVariant(product_id=clone.id, name=var.name)
        db.add(new_var)
        await db.flush()
        for opt in var.options or []:
            db.add(
                ProductVariantOption(
                    variant_id=new_var.id,
                    name=opt.name,
                    price=opt.price,
                    mrp=opt.mrp,
                    stock=opt.stock,
                    weight=getattr(opt, "weight", None),
                    hex=getattr(opt, "hex", None),
                    colors=list(getattr(opt, "colors", None) or []),
                    image_url=getattr(opt, "image_url", None),
                    images=list(getattr(opt, "images", None) or [])
                    or (
                        [opt.image_url]
                        if getattr(opt, "image_url", None)
                        else []
                    ),
                )
            )

    await db.commit()
    return await get_product_by_id(db, clone.id)


async def update_product(db: AsyncSession, product_id: int, data: dict) -> dict | None:
    from app.categories import service as category_service

    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
            selectinload(Product.category_rel),
            selectinload(Product.categories_m2m),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        return None

    variants_data = data.pop("variants", None)
    has_category_ids = "category_ids" in data
    has_category_id = "category_id" in data
    category_ids = data.pop("category_ids", None) if has_category_ids else None
    category_id = data.pop("category_id", None) if has_category_id else None
    data.pop("category", None)
    has_siblings = "color_sibling_ids" in data
    sibling_ids = data.pop("color_sibling_ids", None) if has_siblings else None
    data.pop("color_group_id", None)
    if "colors" in data:
        data["colors"] = _normalize_colors(data.get("colors"))

    if has_category_ids or has_category_id:
        ids = await category_service.normalize_category_ids(
            category_ids
            if has_category_ids
            else [c.id for c in (product.categories_m2m or [])],
            category_id if has_category_id else product.category_id,
        )
        await category_service.sync_product_categories(
            db,
            product,
            ids,
            primary_id=ids[0] if ids else None,
        )

    for key, value in data.items():
        if hasattr(product, key) and value is not None:
            setattr(product, key, value)
    if "colors" in data:
        product.colors = data["colors"]
    if "name" in data and data["name"]:
        product.slug = slugify(data["name"])

    if has_siblings:
        await sync_color_group(db, product, sibling_ids)

    if variants_data is not None:
        for v in list(product.variants):
            await db.delete(v)
        await db.flush()
        for var_data in variants_data:
            variant = ProductVariant(product_id=product.id, name=var_data["name"])
            db.add(variant)
            await db.flush()
            for opt_data in var_data.get("options", []):
                db.add(
                    ProductVariantOption(
                        variant_id=variant.id, **_clean_option_data(opt_data)
                    )
                )

    product.updated_at = utcnow()
    await db.commit()
    return await get_product_by_id(db, product_id)


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        return False
    await db.delete(product)
    await db.commit()
    return True


async def add_product_images(
    db: AsyncSession, product_id: int, image_urls: list
) -> dict | None:
    result = await db.execute(select(Product).where(Product.id == product_id))
    if not result.scalar_one_or_none():
        return None

    # Dedupe against existing URLs for this product
    existing = (
        await db.execute(
            select(ProductImage.url).where(ProductImage.product_id == product_id)
        )
    ).scalars().all()
    existing_set = set(existing)

    pos_result = await db.execute(
        select(func.max(ProductImage.position)).where(ProductImage.product_id == product_id)
    )
    max_pos = pos_result.scalar() or -1
    added = 0
    for url in image_urls:
        if not url or url in existing_set:
            continue
        max_pos += 1
        db.add(ProductImage(product_id=product_id, url=url, position=max_pos))
        existing_set.add(url)
        added += 1
    if added:
        await db.commit()
    return await get_product_by_id(db, product_id)


async def list_product_media_library(
    db: AsyncSession,
    product_id: int | None = None,
    limit: int = 200,
) -> dict:
    """Return product images: same product first, then other products."""
    limit = min(max(limit, 1), 500)
    same_product: list[dict] = []
    others: list[dict] = []
    seen: set[str] = set()

    query = (
        select(ProductImage, Product.name, Product.id)
        .join(Product, Product.id == ProductImage.product_id)
        .order_by(ProductImage.id.desc())
        .limit(limit * 2)
    )
    rows = (await db.execute(query)).all()

    for img, product_name, pid in rows:
        if not img.url or img.url in seen:
            continue
        seen.add(img.url)
        entry = {
            "url": img.url,
            "product_id": pid,
            "product_name": product_name,
        }
        if product_id and pid == product_id:
            same_product.append(entry)
        else:
            others.append(entry)

    return {
        "same_product": same_product[:limit],
        "others": others[:limit],
    }


async def remove_product_image(
    db: AsyncSession, product_id: int, image_url: str
) -> dict | None:
    result = await db.execute(
        select(ProductImage).where(
            ProductImage.product_id == product_id, ProductImage.url == image_url
        )
    )
    img = result.scalar_one_or_none()
    if img:
        await db.delete(img)
        await db.commit()
    return await get_product_by_id(db, product_id)


async def get_all_orders(
    db: AsyncSession, page: int = 1, limit: int = 20, status: str | None = None
) -> dict:
    query = select(Order).options(selectinload(Order.items))
    count_query = select(func.count(Order.id))
    if status:
        query = query.where(Order.order_status == status)
        count_query = count_query.where(Order.order_status == status)
    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    orders = [serialize_order(o) for o in result.scalars().all()]
    return {"orders": orders, "total": total, "page": page, "limit": limit}


async def update_order_status(
    db: AsyncSession, order_id: str, status: str
) -> dict | None:
    if not status:
        raise HTTPException(status_code=400, detail="Status is required")
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        return None
    order.order_status = status
    order.updated_at = utcnow()
    await db.commit()
    return serialize_order(order)


async def get_all_payments(
    db: AsyncSession, page: int = 1, limit: int = 20
) -> dict:
    total = (await db.execute(select(func.count(Payment.id)))).scalar() or 0
    result = await db.execute(
        select(Payment)
        .order_by(Payment.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    payments = [serialize_payment(p) for p in result.scalars().all()]
    return {"payments": payments, "total": total, "page": page, "limit": limit}


async def list_users(
    db: AsyncSession, page: int = 1, limit: int = 20
) -> dict:
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    users = result.scalars().all()

    if not users:
        return {"users": [], "total": total, "page": page, "limit": limit}

    user_ids = [u.id for u in users]
    emails = [u.email for u in users if u.email]

    orders_result = await db.execute(
        select(Order)
        .where(
            or_(
                Order.user_id.in_(user_ids),
                Order.customer_email.in_(emails) if emails else False,
            )
        )
        .order_by(Order.created_at.desc())
    )

    order_by_user_id: dict[int, Order] = {}
    order_by_email: dict[str, Order] = {}
    for order in orders_result.scalars().all():
        if order.user_id and order.user_id not in order_by_user_id:
            order_by_user_id[order.user_id] = order
        if order.customer_email and order.customer_email not in order_by_email:
            order_by_email[order.customer_email] = order

    return {
        "users": [
            _serialize_admin_user(
                user,
                order_by_user_id.get(user.id)
                or order_by_email.get(user.email),
            )
            for user in users
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


def _format_profile_address(user: User) -> str:
    parts = []
    if user.address_line1:
        parts.append(user.address_line1)
    if user.address_line2:
        parts.append(user.address_line2)
    if user.address_landmark:
        parts.append(f"Landmark: {user.address_landmark}")
    city_state = ", ".join(
        p for p in [user.address_city, user.address_state] if p
    )
    if city_state:
        if user.address_pincode:
            parts.append(f"{city_state} - {user.address_pincode}")
        else:
            parts.append(city_state)
    elif user.address_pincode:
        parts.append(user.address_pincode)
    return ", ".join(parts)


def _format_order_address(order: Order | None) -> str:
    if not order:
        return ""
    parts = [order.address_line1]
    if order.address_line2:
        parts.append(order.address_line2)
    landmark = getattr(order, "address_landmark", None)
    if landmark:
        parts.append(f"Landmark: {landmark}")
    parts.append(
        f"{order.address_city}, {order.address_state} - {order.address_pincode}"
    )
    return ", ".join(parts)


def _serialize_admin_user(user: User, latest_order: Order | None = None) -> dict:
    phone = user.phone or ""
    if not phone and latest_order:
        phone = latest_order.customer_phone or ""

    address = _format_profile_address(user) or _format_order_address(latest_order)

    return {
        "id": str(user.id),
        "name": user.name or "",
        "email": user.email or "",
        "phone": phone,
        "address": address,
        "registered_at": user.created_at.isoformat() if user.created_at else "",
    }


async def get_user(db: AsyncSession, user_id: int) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    order_result = await db.execute(
        select(Order)
        .where(
            or_(Order.user_id == user.id, Order.customer_email == user.email)
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    latest_order = order_result.scalar_one_or_none()
    return _serialize_admin_user(user, latest_order)
