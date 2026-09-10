from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_optional_user
from app.database import get_db
from app.promocodes import service
from app.promocodes.schemas import (
    PromoCodeCreateRequest,
    PromoCodeUpdateRequest,
    PromoValidateRequest,
)

router = APIRouter()


@router.get("/admin/all")
async def admin_list_promos(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_promos(db)


@router.get("/admin/{promo_id}/usage")
async def admin_promo_usage(
    promo_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_promo_usage(db, promo_id)
    if not data:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return data


@router.post("/", status_code=201)
async def create_promo(
    body: PromoCodeCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_promo(db, body.model_dump())


@router.put("/{promo_id}")
async def update_promo(
    promo_id: int,
    body: PromoCodeUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # Allow explicitly clearing max_uses by sending null — exclude_unset keeps omitted fields out
    data = body.model_dump(exclude_unset=True)
    updated = await service.update_promo(db, promo_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return updated


@router.delete("/{promo_id}")
async def delete_promo(
    promo_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_promo(db, promo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return {"message": "Promo code deleted"}


@router.post("/validate")
async def validate_promo(
    body: PromoValidateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_user),
):
    user_id = None
    if user and user.get("role") != "admin":
        try:
            user_id = int(user["id"])
        except (TypeError, ValueError, KeyError):
            user_id = None
    phone = body.phone or (user.get("phone") if user else None)
    return await service.validate_promo(
        db,
        body.code,
        body.subtotal,
        body.shipping_charge,
        user_id=user_id,
        phone=phone,
    )
