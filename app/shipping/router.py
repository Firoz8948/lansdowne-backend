from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user

from . import service
from .schemas import CreateShipmentRequest

router = APIRouter()


@router.post("/create-shipment")
async def create_shipment(
    payload: CreateShipmentRequest, user: dict = Depends(get_current_user)
):
    return await service.create_shipment(payload.order_id)


@router.get("/track/{order_id}")
async def track(order_id: str, user: dict = Depends(get_current_user)):
    return await service.track_shipment(order_id)


@router.get("/rates")
async def rates(
    pickup_pincode: str = Query(...),
    delivery_pincode: str = Query(...),
    weight: float = Query(0.5),
    cod: bool = Query(False),
):
    return await service.get_rates(pickup_pincode, delivery_pincode, weight, cod)


@router.post("/cancel/{order_id}")
async def cancel(order_id: str, user: dict = Depends(get_current_user)):
    return await service.cancel_shipment(order_id)
