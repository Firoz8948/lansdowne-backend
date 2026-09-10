from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from . import service
from .schemas import CreateOrderRequest, OrderResponse

router = APIRouter()


@router.post("/create", response_model=OrderResponse)
async def create_order(
    payload: CreateOrderRequest,
    user=Depends(get_current_user),
):
    """Place a COD order (requires mobile OTP login). Prepaid uses /payments/*."""
    from fastapi import HTTPException

    if payload.payment_method != "cod":
        raise HTTPException(
            status_code=400,
            detail="Online payments must use /payments/create-order and /payments/verify",
        )

    customer = payload.customer.model_dump()
    if not customer.get("mobile") and user.get("phone"):
        customer["mobile"] = user["phone"]
    if not customer.get("name") and user.get("name"):
        customer["name"] = user["name"]

    return await service.create_customer_order(
        customer=customer,
        address=payload.address.model_dump(),
        items=[item.model_dump() for item in payload.items],
        user_id=int(user["id"]),
        payment_method="cod",
        payment_status="pending",
        order_status="processing",
        promo_code=payload.promo_code,
        meta_event_id=payload.meta_event_id,
        meta_fbp=payload.meta_fbp,
        meta_fbc=payload.meta_fbc,
    )


@router.get("/my")
async def my_orders(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orders = await service.list_user_orders(db, int(user["id"]))
    return {"orders": orders}
