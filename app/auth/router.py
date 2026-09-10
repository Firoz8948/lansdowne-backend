from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

from . import service
from .dependencies import get_current_user
from .schemas import MessageResponse, TokenResponse, UpdateProfileRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_current_user_profile(current_user["id"], db)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await service.update_user_profile(
        db,
        user_id=current_user["id"],
        name=body.name,
        phone=body.phone,
        address_line1=body.address_line1,
        address_line2=body.address_line2,
        address_landmark=body.address_landmark,
        address_city=body.address_city,
        address_state=body.address_state,
        address_pincode=body.address_pincode,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="No refresh token found. Please log in again.",
        )
    return await service.refresh_access_token(db, refresh_token)


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token_legacy(
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compatible alias for older clients."""
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="No refresh token found. Please log in again.",
        )
    return await service.refresh_access_token(db, refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout():
    response = JSONResponse({"message": "Logged out successfully."})
    response.delete_cookie(key="refresh_token", path="/")
    response.delete_cookie(key="access_token", path="/")
    return response
