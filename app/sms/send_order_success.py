import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger("sms")

RENFLAIR_ORDER_URL = "https://sms.renflair.in/V3.php"


async def send_order_success_sms(
    phone: str,
    customer_name: str,
    order_id: str,
) -> dict:
    """Send order confirmation SMS via Renflair V3 API.

    Message template:
    "Hi, {CNAME}, Your order ID {OID} has been placed Successfully.
     It will be delivered soon."
    """
    if not settings.RENFLAIR_API_KEY:
        logger.warning("RENFLAIR_API_KEY missing — skipping order SMS")
        return {"skipped": True}

    cname = (customer_name or "Customer").strip()[:50] or "Customer"
    oid = str(order_id)

    url = (
        f"{RENFLAIR_ORDER_URL}"
        f"?API={quote(settings.RENFLAIR_API_KEY, safe='')}"
        f"&PHONE={quote(str(phone), safe='')}"
        f"&OID={quote(oid, safe='')}"
        f"&CNAME={quote(cname, safe='')}"
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)

        if resp.status_code >= 400:
            logger.error("Renflair order SMS failed: %s %s", resp.status_code, resp.text)
            return {"success": False, "status_code": resp.status_code}

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        logger.info("Order SMS sent for %s to %s", oid, phone[-4:].rjust(10, "*"))
        return {"success": True, "data": data}
    except Exception as exc:
        logger.exception("Order SMS error: %s", exc)
        return {"success": False, "error": str(exc)}
