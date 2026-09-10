from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order, PromoCode
from app.orders.models import calc_shipping

CANCELLED_STATUSES = {"cancelled", "failed"}
FAILED_PAYMENTS = {"failed", "refunded"}


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) >= 10:
        return digits[-10:]
    return digits or None


def remaining_uses(promo: PromoCode) -> int | None:
    max_uses = getattr(promo, "max_uses", None)
    if max_uses is None:
        return None
    used = int(getattr(promo, "uses_count", 0) or 0)
    return max(max_uses - used, 0)


def serialize_promo(promo: PromoCode) -> dict:
    remaining = remaining_uses(promo)
    max_uses = getattr(promo, "max_uses", None)
    uses_count = int(getattr(promo, "uses_count", 0) or 0)
    exhausted = max_uses is not None and uses_count >= max_uses
    return {
        "id": promo.id,
        "code": promo.code,
        "action_type": promo.action_type,
        "percent_value": promo.percent_value,
        "valid_from": promo.valid_from.isoformat() if promo.valid_from else None,
        "valid_to": promo.valid_to.isoformat() if promo.valid_to else None,
        "audience": getattr(promo, "audience", None) or "all",
        "max_uses": max_uses,
        "uses_count": uses_count,
        "remaining_uses": remaining,
        "is_active": bool(promo.is_active) and not exhausted,
        "created_at": promo.created_at.isoformat() if promo.created_at else None,
        "updated_at": promo.updated_at.isoformat() if promo.updated_at else None,
    }


def action_label(promo: PromoCode | dict) -> str:
    if isinstance(promo, dict):
        action = promo.get("action_type")
        percent = promo.get("percent_value")
    else:
        action = promo.action_type
        percent = promo.percent_value
    if action == "free_shipping":
        return "Free shipping"
    if action == "percent_off":
        return f"{int(percent) if percent else 0}% off"
    return action or ""


async def is_new_customer(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    phone: str | None = None,
) -> bool:
    """True when this buyer has no prior non-cancelled order."""
    phone = _normalize_phone(phone)
    clauses = []
    if user_id is not None:
        try:
            clauses.append(Order.user_id == int(user_id))
        except (TypeError, ValueError):
            pass
    if phone:
        # Match last-10 digits regardless of stored country prefix formatting
        clauses.append(Order.customer_phone.endswith(phone))
        clauses.append(Order.customer_phone == phone)

    if not clauses:
        # Cannot prove new without identity — require phone at checkout for new_users promos
        return False

    result = await db.execute(
        select(func.count(Order.id)).where(
            or_(*clauses),
            Order.order_status.notin_(tuple(CANCELLED_STATUSES)),
            Order.payment_status.notin_(tuple(FAILED_PAYMENTS)),
        )
    )
    return int(result.scalar() or 0) == 0


async def list_promos(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(PromoCode).order_by(PromoCode.created_at.desc()))
    items = []
    for promo in result.scalars().all():
        data = serialize_promo(promo)
        data["action_label"] = action_label(promo)
        items.append(data)
    return items


async def create_promo(db: AsyncSession, data: dict) -> dict:
    if data.get("action_type") == "percent_off" and not data.get("percent_value"):
        raise HTTPException(status_code=400, detail="percent_value is required for percent_off")
    if data.get("action_type") == "free_shipping":
        data["percent_value"] = None

    data.setdefault("audience", "all")
    data.setdefault("uses_count", 0)

    existing = await db.execute(
        select(PromoCode).where(PromoCode.code == data["code"])
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Promo code already exists")

    promo = PromoCode(**data)
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    out = serialize_promo(promo)
    out["action_label"] = action_label(promo)
    return out


async def update_promo(db: AsyncSession, promo_id: int, data: dict) -> dict | None:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        return None

    if "code" in data and data["code"] != promo.code:
        clash = await db.execute(
            select(PromoCode).where(PromoCode.code == data["code"])
        )
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Promo code already exists")

    for key, value in data.items():
        setattr(promo, key, value)

    if promo.action_type == "free_shipping":
        promo.percent_value = None
    elif promo.action_type == "percent_off" and not promo.percent_value:
        raise HTTPException(status_code=400, detail="percent_value is required for percent_off")

    await db.commit()
    await db.refresh(promo)
    out = serialize_promo(promo)
    out["action_label"] = action_label(promo)
    return out


async def delete_promo(db: AsyncSession, promo_id: int) -> bool:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        return False
    await db.delete(promo)
    await db.commit()
    return True


async def get_valid_promo(
    db: AsyncSession,
    code: str,
    *,
    user_id: int | None = None,
    phone: str | None = None,
    for_update: bool = False,
) -> PromoCode:
    query = select(PromoCode).where(PromoCode.code == code.strip().upper())
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    promo = result.scalar_one_or_none()
    if not promo or not promo.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")

    today = date.today()
    if today < promo.valid_from or today > promo.valid_to:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")

    max_uses = getattr(promo, "max_uses", None)
    uses_count = int(getattr(promo, "uses_count", 0) or 0)
    if max_uses is not None and uses_count >= max_uses:
        if promo.is_active:
            promo.is_active = False
            await db.flush()
        raise HTTPException(
            status_code=400,
            detail="This promo code has reached its usage limit",
        )

    audience = getattr(promo, "audience", None) or "all"
    if audience == "new_users":
        phone_norm = _normalize_phone(phone)
        if not phone_norm and user_id is None:
            raise HTTPException(
                status_code=400,
                detail="Enter your phone number to apply this new-customer promo",
            )
        if not await is_new_customer(db, user_id=user_id, phone=phone_norm):
            raise HTTPException(
                status_code=400,
                detail="This promo is for new customers only",
            )

    return promo


def apply_promo_to_totals(
    promo: PromoCode,
    subtotal: float,
    shipping_charge: float | None = None,
) -> dict:
    shipping = (
        float(shipping_charge)
        if shipping_charge is not None
        else calc_shipping(subtotal)
    )
    discount = 0.0

    if promo.action_type == "free_shipping":
        shipping = 0.0
    elif promo.action_type == "percent_off":
        pct = float(promo.percent_value or 0)
        discount = round(subtotal * pct / 100, 2)

    total = round(max(subtotal - discount, 0) + shipping, 2)
    remaining = remaining_uses(promo)
    return {
        "valid": True,
        "code": promo.code,
        "action_type": promo.action_type,
        "percent_value": promo.percent_value,
        "audience": getattr(promo, "audience", None) or "all",
        "max_uses": getattr(promo, "max_uses", None),
        "uses_count": int(getattr(promo, "uses_count", 0) or 0),
        "remaining_uses": remaining,
        "action_label": action_label(promo),
        "discount_amount": discount,
        "shipping_charge": shipping,
        "subtotal": subtotal,
        "total": total,
        "message": f"Promo applied: {action_label(promo)}",
    }


async def validate_promo(
    db: AsyncSession,
    code: str,
    subtotal: float,
    shipping_charge: float | None = None,
    *,
    user_id: int | None = None,
    phone: str | None = None,
) -> dict:
    promo = await get_valid_promo(db, code, user_id=user_id, phone=phone)
    return apply_promo_to_totals(promo, subtotal, shipping_charge)


async def resolve_promo_for_order(
    db: AsyncSession,
    code: str | None,
    subtotal: float,
    shipping_charge: float,
    *,
    user_id: int | None = None,
    phone: str | None = None,
    consume: bool = False,
) -> tuple[float, float, str | None]:
    """Returns (discount_amount, shipping_charge, promo_code)."""
    if not code:
        return 0.0, shipping_charge, None

    promo = await get_valid_promo(
        db,
        code,
        user_id=user_id,
        phone=phone,
        for_update=consume,
    )
    applied = apply_promo_to_totals(promo, subtotal, shipping_charge)

    if consume:
        promo.uses_count = int(getattr(promo, "uses_count", 0) or 0) + 1
        max_uses = getattr(promo, "max_uses", None)
        if max_uses is not None and promo.uses_count >= max_uses:
            promo.is_active = False
        await db.flush()

    return applied["discount_amount"], applied["shipping_charge"], promo.code


async def get_promo_usage(db: AsyncSession, promo_id: int) -> dict | None:
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if not promo:
        return None

    orders_result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.promo_code == promo.code)
        .order_by(Order.created_at.desc())
    )
    orders = orders_result.scalars().all()
    usages = []
    for order in orders:
        usages.append(
            {
                "order_id": order.order_id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_email": order.customer_email,
                "user_id": order.user_id,
                "total": order.total,
                "discount_amount": getattr(order, "discount_amount", 0) or 0,
                "payment_status": order.payment_status,
                "order_status": order.order_status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "products": [
                    {
                        "name": item.name,
                        "quantity": item.quantity,
                        "price": item.price,
                        "product_id": item.product_id,
                    }
                    for item in (order.items or [])
                ],
            }
        )

    data = serialize_promo(promo)
    data["action_label"] = action_label(promo)
    data["usages"] = usages
    data["usage_count_from_orders"] = len(usages)
    return data
