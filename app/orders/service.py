import logging

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common import serialize_order, utcnow
from app.database import AsyncSessionLocal
from app.models import Order, OrderItem
from app.orders.notifications import notify_order_placed

from .models import ORDER_STATUSES, calc_subtotal, generate_order_id, normalize_items, total_cart_weight_grams

logger = logging.getLogger("orders")


def _customer_phone(customer: dict) -> str:
    return customer.get("phone") or customer.get("mobile") or ""


async def _load_order(db: AsyncSession, order_id: str) -> Order | None:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.shipment))
        .where(Order.order_id == order_id)
    )
    order = result.scalar_one_or_none()
    if order:
        return order
    if order_id.isdigit():
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.shipment))
            .where(Order.id == int(order_id))
        )
        return result.scalar_one_or_none()
    return None


async def create_customer_order(
    customer: dict,
    address: dict,
    items: list[dict],
    user_id: int | None = None,
    payment_method: str = "cod",
    payment_status: str = "pending",
    order_status: str = "processing",
    razorpay_payment_id: str | None = None,
    razorpay_order_id: str | None = None,
    promo_code: str | None = None,
    meta_event_id: str | None = None,
    meta_fbp: str | None = None,
    meta_fbc: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    normalized = normalize_items(items)
    subtotal = calc_subtotal(normalized)
    weight = total_cart_weight_grams(normalized)

    async with AsyncSessionLocal() as db:
        from app.promocodes import service as promo_service
        from app.shipping_zones import service as zone_service

        shipping = await zone_service.resolve_shipping_charge(
            db,
            subtotal=subtotal,
            state=address.get("state"),
            pincode=address.get("pincode"),
            weight_grams=weight,
            payment_method=payment_method,
        )

        discount = 0.0
        applied_code = None
        if promo_code:
            discount, shipping, applied_code = await promo_service.resolve_promo_for_order(
                db,
                promo_code,
                subtotal,
                shipping,
                user_id=user_id,
                phone=_customer_phone(customer),
                consume=True,
            )

        order = Order(
            order_id=generate_order_id(),
            customer_name=customer.get("name", "Customer"),
            customer_phone=_customer_phone(customer),
            customer_email=customer.get("email"),
            address_line1=address.get("line1", ""),
            address_line2=address.get("line2"),
            address_landmark=address.get("landmark") or None,
            address_city=address.get("city", ""),
            address_state=address.get("state", ""),
            address_pincode=address.get("pincode", ""),
            subtotal=subtotal,
            shipping_charge=shipping,
            discount_amount=discount,
            promo_code=applied_code,
            total=round(max(subtotal - discount, 0) + shipping, 2),
            payment_method=payment_method,
            payment_status=payment_status,
            order_status=order_status,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            user_id=user_id,
        )
        db.add(order)
        await db.flush()

        for item in normalized:
            pid = item.get("product_id")
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=int(pid) if pid and str(pid).isdigit() else None,
                    name=item["name"],
                    price=item["price"],
                    quantity=item["qty"],
                    image=item.get("image"),
                    variant_info=item.get("variant_info"),
                )
            )

        await db.commit()
        await db.refresh(order, ["items"])

        try:
            await notify_order_placed(
                customer_phone=order.customer_phone,
                customer_name=order.customer_name,
                order_id=order.order_id,
            )
        except Exception as exc:
            logger.warning("Order placement notifications failed: %s", exc)

        shipment_data = None
        try:
            from app.config import settings as app_settings
            from app.shipping import service as shipping_service

            if app_settings.SHIPROCKET_AUTO_PUSH and shipping_service.shiprocket_configured():
                shipment_data = await shipping_service.push_order_to_shiprocket(
                    order.order_id, raise_on_error=False
                )
        except Exception as exc:
            logger.warning("Shiprocket auto-push failed: %s", exc)

        payload = serialize_order(order)
        if shipment_data:
            payload["shipment"] = shipment_data

        try:
            from app.meta import capi

            await capi.track_purchase(
                order=payload,
                event_id=meta_event_id or order.order_id,
                fbp=meta_fbp,
                fbc=meta_fbc,
                client_ip=client_ip,
                user_agent=user_agent,
            )
        except Exception as exc:
            logger.warning("Meta CAPI Purchase failed: %s", exc)

        return payload


async def create_guest_order(*args, **kwargs) -> dict:
    """Backward-compatible alias."""
    return await create_customer_order(*args, **kwargs)


async def create_order_from_checkout(
    checkout: dict,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    user_id: int | None = None,
    payment_method: str = "razorpay",
) -> dict:
    method = (payment_method or checkout.get("payment_method") or "razorpay").lower()
    if method not in {"razorpay", "payu"}:
        method = "razorpay"
    return await create_customer_order(
        customer=checkout["customer"],
        address=checkout["address"],
        items=checkout["items"],
        user_id=user_id,
        payment_method=method,
        payment_status="paid",
        order_status="processing",
        razorpay_payment_id=razorpay_payment_id,
        razorpay_order_id=razorpay_order_id,
        promo_code=checkout.get("promo_code"),
        meta_event_id=checkout.get("meta_event_id"),
        meta_fbp=checkout.get("meta_fbp"),
        meta_fbc=checkout.get("meta_fbc"),
    )


async def get_order(order_id: str, is_admin: bool = False) -> dict:
    async with AsyncSessionLocal() as db:
        order = await _load_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return serialize_order(order)


async def update_status(order_id: str, status: str) -> dict:
    if not status:
        raise HTTPException(status_code=400, detail="Status is required")
    if status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    async with AsyncSessionLocal() as db:
        order = await _load_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order.order_status = status
        order.updated_at = utcnow()
        await db.commit()
        await db.refresh(order, ["items"])
        return serialize_order(order)


async def list_user_orders(db: AsyncSession, user_id: int, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.shipment))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return [serialize_order(o) for o in result.scalars().all()]


async def list_orders_paginated(
    page: int = 1, limit: int = 20, status: str | None = None
) -> dict:
    async with AsyncSessionLocal() as db:
        query = select(Order).options(
            selectinload(Order.items), selectinload(Order.shipment)
        )
        count_query = select(func.count(Order.id))
        if status:
            query = query.where(Order.order_status == status)
            count_query = count_query.where(Order.order_status == status)
        total = (await db.execute(count_query)).scalar() or 0
        result = await db.execute(
            query.order_by(Order.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        orders = [serialize_order(o) for o in result.scalars().all()]
        return {"orders": orders, "total": total, "page": page, "limit": limit}


async def count_orders() -> int:
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(func.count(Order.id)))).scalar() or 0
