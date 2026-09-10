import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger("sms")

RENFLAIR_OTP_URL = "https://sms.renflair.in/V1.php"


async def send_otp_sms(phone: str, otp: str) -> dict:
    """Send login OTP via Renflair V1 API.

    Message template: "{OTP} is your verification code for {domain}"
    """
    if not settings.RENFLAIR_API_KEY:
        logger.error("RENFLAIR_API_KEY is not configured")
        raise RuntimeError("SMS service is not configured")

    url = (
        f"{RENFLAIR_OTP_URL}"
        f"?API={quote(settings.RENFLAIR_API_KEY, safe='')}"
        f"&PHONE={quote(str(phone), safe='')}"
        f"&OTP={quote(str(otp), safe='')}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)

    if resp.status_code >= 400:
        logger.error("Renflair OTP SMS failed: %s %s", resp.status_code, resp.text)
        raise RuntimeError("Failed to send OTP SMS")

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    logger.info("OTP SMS sent to %s", phone[-4:].rjust(10, "*"))
    return data
