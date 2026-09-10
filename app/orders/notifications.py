"""Order placement notification helpers (customer + admin SMS)."""

import logging
import re

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Admin
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


async def get_admin_notify_phone() -> str | None:
    """Return the first active admin phone configured for order alerts."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Admin)
            .where(Admin.is_active == True)  # noqa: E712
            .order_by(Admin.id.asc())
        )
        for admin in result.scalars().all():
            phone = _digits_phone(getattr(admin, "phone", None))
            if phone:
                return phone
    return None


async def notify_order_placed(
    *,
    customer_phone: str | None,
    customer_name: str | None,
    order_id: str,
) -> dict:
    """Send customer confirmation + admin alert SMS after order placement."""
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

    admin_phone = await get_admin_notify_phone()
    if admin_phone:
        try:
            results["admin"] = await send_admin_new_order_sms(admin_phone, order_id)
        except Exception as exc:
            logger.warning("Admin order SMS failed: %s", exc)
            results["admin"] = {"success": False, "error": str(exc)}
    else:
        results["admin"] = {"skipped": True, "reason": "admin_phone_not_set"}
        logger.info("Admin order SMS skipped — set phone in Admin Profile")

    return results
