from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common import utcnow
from app.database import AsyncSessionLocal
from app.models import Cart, CartItem
from app.products import service as product_service


def _build_cart_response(user_id: str, cart: Cart | None) -> dict:
    items = cart.items if cart else []
    enriched = []
    total_amount = 0.0
    total_items = 0
    for item in items:
        subtotal = item.price * item.quantity
        total_amount += subtotal
        total_items += item.quantity
        enriched.append(
            {
                "item_id": str(item.id),
                "product_id": str(item.product_id),
                "name": item.name,
                "slug": item.slug,
                "price": item.price,
                "image": item.image,
                "quantity": item.quantity,
                "subtotal": round(subtotal, 2),
            }
        )
    return {
        "id": str(cart.id) if cart else None,
        "user_id": user_id,
        "items": enriched,
        "total_items": total_items,
        "total_amount": round(total_amount, 2),
    }


async def _get_or_create_cart(db, user_id: int) -> Cart:
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id)
    )
    cart = result.scalar_one_or_none()
    if cart:
        return cart
    cart = Cart(user_id=user_id)
    db.add(cart)
    await db.flush()
    return cart


async def get_user_cart(user_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == int(user_id))
        )
        cart = result.scalar_one_or_none()
        return _build_cart_response(user_id, cart)


async def add_to_cart(user_id: str, product_id: str, quantity: int) -> dict:
    product = await product_service.get_product_by_id(product_id)
    if product.get("stock", 0) < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    async with AsyncSessionLocal() as db:
        cart = await _get_or_create_cart(db, int(user_id))
        pid = int(product_id)
        existing_item = next((i for i in cart.items if i.product_id == pid), None)
        if existing_item:
            existing_item.quantity += quantity
        else:
            images = product.get("images") or []
            db.add(
                CartItem(
                    cart_id=cart.id,
                    product_id=pid,
                    name=product["name"],
                    slug=product["slug"],
                    price=product["price"],
                    image=images[0] if images else None,
                    quantity=quantity,
                )
            )
        cart.updated_at = utcnow()
        await db.commit()
        await db.refresh(cart, ["items"])
        return _build_cart_response(user_id, cart)


async def update_item(user_id: str, item_id: str, quantity: int) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == int(user_id))
        )
        cart = result.scalar_one_or_none()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        item = next((i for i in cart.items if str(i.id) == item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found in cart")
        item.quantity = quantity
        cart.updated_at = utcnow()
        await db.commit()
        await db.refresh(cart, ["items"])
        return _build_cart_response(user_id, cart)


async def remove_item(user_id: str, item_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == int(user_id))
        )
        cart = result.scalar_one_or_none()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        item = next((i for i in cart.items if str(i.id) == item_id), None)
        if item:
            await db.delete(item)
        cart.updated_at = utcnow()
        await db.commit()
        await db.refresh(cart, ["items"])
        return _build_cart_response(user_id, cart)


async def clear(user_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(Cart.user_id == int(user_id))
        )
        cart = result.scalar_one_or_none()
        if cart:
            for item in list(cart.items):
                await db.delete(item)
            cart.updated_at = utcnow()
            await db.commit()
        return _build_cart_response(user_id, None)
