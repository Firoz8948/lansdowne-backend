from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user

from . import service
from .schemas import (
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    VerifyPaymentRequest,
)

router = APIRouter()


@router.get("/config")
async def payment_config():
    """Public: whether online payment is configured (never returns secrets)."""
    return service.get_public_config()


@router.post("/create-order", response_model=CreatePaymentOrderResponse)
async def create_order(
    payload: CreatePaymentOrderRequest,
    user=Depends(get_current_user),
):
    items = [item.model_dump() for item in payload.items]
    customer = payload.customer.model_dump()
    if not customer.get("mobile") and user.get("phone"):
        customer["mobile"] = user["phone"]
    if not customer.get("name") and user.get("name"):
        customer["name"] = user["name"]
    return await service.create_payment_order(
        customer,
        payload.address.model_dump(),
        items,
        user_id=int(user["id"]),
        promo_code=payload.promo_code,
        meta_event_id=payload.meta_event_id,
        meta_fbp=payload.meta_fbp,
        meta_fbc=payload.meta_fbc,
    )


@router.post("/verify")
async def verify(
    payload: VerifyPaymentRequest,
    user=Depends(get_current_user),
):
    return await service.verify_payment(payload.model_dump(), user_id=int(user["id"]))


@router.post("/payu/success")
async def payu_success(request: Request):
    form = dict(await request.form())
    return await service.handle_payu_callback(form, success_path=True)


@router.post("/payu/failure")
async def payu_failure(request: Request):
    form = dict(await request.form())
    return await service.handle_payu_callback(form, success_path=False)


@router.post("/webhook")
async def webhook(request: Request):
    """
    Razorpay webhook URL: POST {API}/payments/webhook
    Enable events: payment.captured, payment.failed, refund.processed
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    return await service.handle_webhook(body, signature)
