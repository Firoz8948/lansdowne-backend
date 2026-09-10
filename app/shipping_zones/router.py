from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.shipping_zones import service
from app.shipping_zones.schemas import (
    ShippingQuoteRequest,
    ShippingZoneCreateRequest,
    ShippingZoneUpdateRequest,
)

router = APIRouter()


@router.get("/admin/all")
async def admin_list_zones(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_zones(db, active_only=False)


@router.post("/", status_code=201)
async def create_zone(
    body: ShippingZoneCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_zone(db, body.model_dump())


@router.put("/{zone_id}")
async def update_zone(
    zone_id: int,
    body: ShippingZoneUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    updated = await service.update_zone(db, zone_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Shipping zone not found")
    return updated


@router.delete("/{zone_id}")
async def delete_zone(
    zone_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_zone(db, zone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Shipping zone not found")
    return {"message": "Shipping zone deleted"}


@router.get("/pincode/{pincode}")
async def lookup_pincode(pincode: str):
    """Public pincode → city/state lookup (proxied server-side to avoid CORS)."""
    details = service.lookup_pincode_details(pincode)
    if not details:
        raise HTTPException(status_code=404, detail="Pincode not found")
    return details


@router.post("/quote")
async def quote_shipping(
    body: ShippingQuoteRequest,
    db: AsyncSession = Depends(get_db),
):
    return await service.quote_shipping(
        db,
        subtotal=body.subtotal,
        state=body.state,
        pincode=body.pincode,
        weight_grams=body.weight_grams,
        payment_method=body.payment_method,
    )
