from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.config import settings
from app.database import get_db
from app.otp import send_otp as send_otp_service
from app.otp import verify_otp as verify_otp_service
from app.otp.schemas import SendOTPRequest, SendOTPResponse, VerifyOTPRequest
from app.sms.utils import normalize_phone

router = APIRouter(prefix="/otp", tags=["OTP"])


@router.post("/send", response_model=SendOTPResponse)
async def send_otp(
    body: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    return await send_otp_service.send_otp_to_phone(db, body.phone, body.name or "")


@router.post("/verify")
async def verify_otp(
    body: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    phone = normalize_phone(body.phone)
    otp_code = body.otp.strip()

    if len(otp_code) != settings.OTP_LENGTH or not otp_code.isdigit():
        raise HTTPException(
            status_code=400,
            detail=f"OTP must be {settings.OTP_LENGTH} digits.",
        )

    success, message = await verify_otp_service.verify_otp_for_phone(
        db, phone, otp_code
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)

    user = await auth_service.get_or_create_user_by_phone(
        db, phone, body.name or ""
    )
    await verify_otp_service.delete_verified_otps(db, phone)

    token_data = {
        "sub": str(user["id"]),
        "phone": user.get("phone"),
        "email": user.get("email"),
        "role": user["role"],
    }
    access_token = auth_service.create_access_token(token_data)
    refresh_token = auth_service.create_refresh_token(token_data)

    response = JSONResponse(
        {
            "message": "Login successful.",
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
        }
    )

    secure = settings.ENVIRONMENT != "development"
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return response


@router.get("/status")
async def otp_status(phone: str, db: AsyncSession = Depends(get_db)):
    normalized = normalize_phone(phone)
    status = await verify_otp_service.get_otp_status(db, normalized)

    if not status:
        return {"has_valid_otp": False, "phone": normalized}

    return {
        "has_valid_otp": True,
        "phone": normalized,
        "expires_at": status["expires_at"],
        "created_at": status["created_at"],
    }
