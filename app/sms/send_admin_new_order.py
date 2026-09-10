import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger("sms")

RENFLAIR_ADMIN_ORDER_URL = "https://sms.renflair.in/V4.php"


async def send_admin_new_order_sms(phone: str, order_id: str) -> dict:
    """Notify admin of a new order via Renflair V4 API.

    Message template:
    "Received a new order with ID {OID}, please check and proceed with the order."
    """
    if not settings.RENFLAIR_API_KEY:
        logger.warning("RENFLAIR_API_KEY missing — skipping admin order SMS")
        return {"skipped": True}

    if not phone:
        logger.warning("Admin phone missing — skipping admin order SMS")
        return {"skipped": True}

    oid = str(order_id)
    url = (
        f"{RENFLAIR_ADMIN_ORDER_URL}"
        f"?API={quote(settings.RENFLAIR_API_KEY, safe='')}"
        f"&PHONE={quote(str(phone), safe='')}"
        f"&OID={quote(oid, safe='')}"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)

        if resp.status_code >= 400:
            logger.error(
                "Renflair admin order SMS failed: %s %s",
                resp.status_code,
                resp.text,
            )
            return {"success": False, "status_code": resp.status_code}

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        logger.info(
            "Admin new-order SMS sent for %s to %s",
            oid,
            str(phone)[-4:].rjust(10, "*"),
        )
        return {"success": True, "data": data}
    except Exception as exc:
        logger.exception("Admin order SMS error: %s", exc)
        return {"success": False, "error": str(exc)}
