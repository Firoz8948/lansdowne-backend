import random
import string
from datetime import timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common import utcnow
from app.config import settings
from app.models import OTP
from app.sms.send_otp import send_otp_sms
from app.sms.utils import normalize_phone


def _generate_otp_code(length: int = 4) -> str:
    return "".join(random.choices(string.digits, k=length))


async def send_otp_to_phone(db: AsyncSession, phone: str, name: str = "") -> dict:
    """Generate a 4-digit OTP, store it, and send via Renflair SMS."""
    normalized = normalize_phone(phone)
    _ = name  # reserved for future personalization

    await db.execute(delete(OTP).where(OTP.phone == normalized))

    if settings.OTP_DEBUG:
        otp_code = "1234"
    else:
        otp_code = _generate_otp_code(settings.OTP_LENGTH)

    expires_at = utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    db.add(
        OTP(
            phone=normalized,
            otp=otp_code,
            verified=False,
            expires_at=expires_at,
        )
    )
    await db.commit()

    if not settings.OTP_DEBUG:
        try:
            await send_otp_sms(normalized, otp_code)
        except Exception as exc:
            await db.execute(delete(OTP).where(OTP.phone == normalized))
            await db.commit()
            raise HTTPException(
                status_code=502,
                detail="Failed to send OTP. Please try again.",
            ) from exc

    response = {
        "message": "OTP sent to your mobile number.",
        "phone": normalized,
    }
    if settings.OTP_DEBUG:
        response["otp"] = otp_code
        response["debug"] = True

    return response
