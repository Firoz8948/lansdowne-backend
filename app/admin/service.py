import logging
import re
from datetime import datetime, timedelta

import bcrypt
from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.utils import create_access_token
from app.common import (
    serialize_admin,
    serialize_order,
    serialize_payment,
    serialize_product,
    utcnow,
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

    email = (data.get("email") or "").strip().lower()
    if email:
        if "@" not in email:
            raise HTTPException(status_code=400, detail="Enter a valid email")
        existing = await db.execute(
            select(Admin).where(Admin.email == email, Admin.id != admin_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        admin.email = email

    if "name" in data and data["name"] is not None:
        admin.name = str(data["name"]).strip() or admin.name

    if "company_name" in data and data["company_name"] is not None:
        admin.company_name = str(data["company_name"]).strip() or None

    if "phone" in data and data["phone"] is not None:
        raw = str(data["phone"]).strip()
        if not raw:
            admin.phone = None
        else:
            digits = re.sub(r"\D", "", raw)
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
            if len(digits) != 10:
                raise HTTPException(
                    status_code=400,
                    detail="Enter a valid 10-digit mobile number",
                )
            admin.phone = digits

    admin.updated_at = utcnow()
    await db.commit()
    await db.refresh(admin)
    return serialize_admin(admin)


async def dashboard_stats(db: AsyncSession) -> dict:
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    total_products = (await db.execute(select(func.count(Product.id)))).scalar() or 0
    total_shipped = (
        await db.execute(
            select(func.count(Order.id)).where(Order.order_status == "shipped")
        )
    ).scalar() or 0

    rev_result = await db.execute(
        select(func.sum(Order.total)).where(Order.payment_status == "paid")
    )
    total_revenue = rev_result.scalar() or 0.0

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
            {"date": start.strftime("%d %b"), "revenue": result.scalar() or 0}
        )

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_products": total_products,
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
    return {"products": products, "total": total, "page": page, "limit": limit}


async def get_product_by_id(db: AsyncSession, product_id: int) -> dict | None:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
            selectinload(Product.category_rel),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    return serialize_product(product) if product else None


async def create_product(db: AsyncSession, data: dict) -> dict:
    from app.categories import service as category_service

    variants_data = data.pop("variants", []) or []
    category_id = data.pop("category_id", None)
    cat_fields = await category_service.resolve_product_category_fields(db, category_id)
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

    for var_data in variants_data:
        variant = ProductVariant(product_id=product.id, name=var_data["name"])
        db.add(variant)
        await db.flush()
        for opt_data in var_data.get("options", []):
            db.add(ProductVariantOption(variant_id=variant.id, **opt_data))

    await db.commit()
    return await get_product_by_id(db, product.id)


async def duplicate_product(db: AsyncSession, product_id: int) -> dict | None:
    """Clone a product with variants + images. Name becomes '(Copy) <original>'."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.options),
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
        tags=list(source.tags or []),
        metafields=dict(source.metafields or {}),
        seo_title=getattr(source, "seo_title", None) or "",
        seo_description=getattr(source, "seo_description", None) or "",
    )
    db.add(clone)
    await db.flush()

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
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        return None

    variants_data = data.pop("variants", None)
    category_id = data.pop("category_id", None) if "category_id" in data else None
    if category_id is not None:
        cat_fields = await category_service.resolve_product_category_fields(
            db,
            category_id,
        )
        if cat_fields:
            data.update(cat_fields)

    for key, value in data.items():
        if hasattr(product, key) and value is not None:
            setattr(product, key, value)
    if "name" in data and data["name"]:
        product.slug = slugify(data["name"])

    if variants_data is not None:
        for v in list(product.variants):
            await db.delete(v)
        await db.flush()
        for var_data in variants_data:
            variant = ProductVariant(product_id=product.id, name=var_data["name"])
            db.add(variant)
            await db.flush()
            for opt_data in var_data.get("options", []):
                db.add(ProductVariantOption(variant_id=variant.id, **opt_data))

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

    pos_result = await db.execute(
        select(func.max(ProductImage.position)).where(ProductImage.product_id == product_id)
    )
    max_pos = pos_result.scalar() or -1
    for i, url in enumerate(image_urls):
        db.add(ProductImage(product_id=product_id, url=url, position=max_pos + i + 1))
    await db.commit()
    return await get_product_by_id(db, product_id)


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
