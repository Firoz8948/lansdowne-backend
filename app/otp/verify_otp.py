from datetime import timezone
from typing import Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common import utcnow
from app.models import OTP
from app.sms.utils import normalize_phone


async def verify_otp_for_phone(
    db: AsyncSession,
    phone: str,
    otp_code: str,
) -> Tuple[bool, str]:
    """Validate OTP without consuming it.

    Callers must invoke ``consume_otps_for_phone`` only after login/signup
    succeeds, so failed account checks do not burn the OTP.
    """
    normalized = normalize_phone(phone)

    result = await db.execute(
        select(OTP)
        .where(OTP.phone == normalized, OTP.verified == False)  # noqa: E712
        .order_by(OTP.created_at.desc())
        .limit(1)
    )
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        return False, "No OTP found for this number. Please request a new one."

    now = utcnow()
    expires = otp_record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if now > expires:
        await db.delete(otp_record)
        await db.commit()
        return False, "OTP has expired. Please request a new one."

    if otp_record.otp != otp_code.strip():
        return False, "Invalid OTP. Please try again."

    return True, "OTP verified successfully"


async def consume_otps_for_phone(db: AsyncSession, phone: str) -> None:
    """Delete all OTPs for a phone after successful login/signup."""
    normalized = normalize_phone(phone)
    await db.execute(delete(OTP).where(OTP.phone == normalized))
    await db.commit()


async def delete_verified_otps(db: AsyncSession, phone: str) -> None:
    """Backward-compatible alias — clears all OTPs for the phone."""
    await consume_otps_for_phone(db, phone)


async def get_otp_status(db: AsyncSession, phone: str) -> Optional[dict]:
    normalized = normalize_phone(phone)

    result = await db.execute(
        select(OTP)
        .where(OTP.phone == normalized, OTP.verified == False)  # noqa: E712
        .order_by(OTP.created_at.desc())
        .limit(1)
    )
    otp_record = result.scalar_one_or_none()
    if not otp_record:
        return None

    now = utcnow()
    expires = otp_record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if now > expires:
        return None

    return {
        "phone": otp_record.phone,
        "expires_at": expires.isoformat(),
        "created_at": otp_record.created_at.isoformat(),
    }
