"""Order placement notification helpers (customer + admin SMS)."""

import logging
import re

from app.config import settings
from app.sms.send_admin_new_order import send_admin_new_order_sms
from app.sms.send_order_success import send_order_success_sms

logger = logging.getLogger("orders.notifications")


def _digits_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10:
        return digits
    return None


def get_admin_notify_phone() -> str | None:
    """Admin order-alert number from locked settings (env)."""
    return _digits_phone(settings.ADMIN_NOTIFY_PHONE)


async def notify_order_placed(
    *,
    customer_phone: str | None,
    customer_name: str | None,
    order_id: str,
) -> dict:
    """Send customer confirmation (V3) + admin alert (V4) after order placement."""
    results = {"customer": None, "admin": None}

    cust_phone = _digits_phone(customer_phone)
    if cust_phone:
        try:
            results["customer"] = await send_order_success_sms(
                cust_phone,
                customer_name or "Customer",
                order_id,
            )
        except Exception as exc:
            logger.warning("Customer order SMS failed: %s", exc)
            results["customer"] = {"success": False, "error": str(exc)}
    else:
        results["customer"] = {"skipped": True, "reason": "invalid_customer_phone"}

    admin_phone = get_admin_notify_phone()
    if admin_phone:
        try:
            results["admin"] = await send_admin_new_order_sms(admin_phone, order_id)
        except Exception as exc:
            logger.warning("Admin order SMS failed: %s", exc)
            results["admin"] = {"success": False, "error": str(exc)}
    else:
        results["admin"] = {"skipped": True, "reason": "admin_phone_not_set"}
        logger.info(
            "Admin order SMS skipped — set ADMIN_NOTIFY_PHONE in backend .env"
        )

    return results
