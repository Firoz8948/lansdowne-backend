"""Meta Conversions API (server-side event tracking)."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("meta.capi")


def _sha256(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().lower()
    # Digits-only for phone
    if normalized.startswith("+"):
        normalized = "".join(ch for ch in normalized if ch.isdigit())
    elif "@" not in normalized:
        digits = "".join(ch for ch in normalized if ch.isdigit())
        if digits:
            # India: ensure country code 91 when 10-digit mobile
            if len(digits) == 10:
                digits = "91" + digits
            normalized = digits
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def meta_configured() -> bool:
    return bool(settings.META_PIXEL_ID and settings.META_ACCESS_TOKEN)


def build_user_data(
    *,
    email: str | None = None,
    phone: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip_code: str | None = None,
    country: str = "in",
    client_ip: str | None = None,
    user_agent: str | None = None,
    fbp: str | None = None,
    fbc: str | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {}
    em = _sha256(email)
    ph = _sha256(phone)
    fn = _sha256(first_name)
    ln = _sha256(last_name)
    ct = _sha256(city)
    st = _sha256(state)
    zp = _sha256(zip_code)
    country_hash = _sha256(country)

    if em:
        data["em"] = [em]
    if ph:
        data["ph"] = [ph]
    if fn:
        data["fn"] = [fn]
    if ln:
        data["ln"] = [ln]
    if ct:
        data["ct"] = [ct]
    if st:
        data["st"] = [st]
    if zp:
        data["zp"] = [zp]
    if country_hash:
        data["country"] = [country_hash]
    if client_ip:
        data["client_ip_address"] = client_ip
    if user_agent:
        data["client_user_agent"] = user_agent
    if fbp:
        data["fbp"] = fbp
    if fbc:
        data["fbc"] = fbc
    return data


async def send_event(
    event_name: str,
    *,
    event_id: str | None = None,
    event_source_url: str | None = None,
    user_data: dict | None = None,
    custom_data: dict | None = None,
    action_source: str = "website",
) -> dict | None:
    if not meta_configured():
        return None

    pixel_id = settings.META_PIXEL_ID.strip()
    token = settings.META_ACCESS_TOKEN.strip()
    version = (settings.META_API_VERSION or "v21.0").strip()
    url = f"https://graph.facebook.com/{version}/{pixel_id}/events"

    event: dict[str, Any] = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "action_source": action_source,
        "user_data": user_data or {},
    }
    if event_id:
        event["event_id"] = event_id
    if event_source_url:
        event["event_source_url"] = event_source_url
    if custom_data:
        event["custom_data"] = custom_data

    payload: dict[str, Any] = {
        "data": [event],
        "access_token": token,
    }
    if settings.META_TEST_EVENT_CODE:
        payload["test_event_code"] = settings.META_TEST_EVENT_CODE.strip()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code >= 400:
                logger.warning(
                    "Meta CAPI %s failed: %s %s",
                    event_name,
                    res.status_code,
                    res.text[:500],
                )
                return None
            return res.json()
    except Exception as exc:
        logger.warning("Meta CAPI %s error: %s", event_name, exc)
        return None


async def track_purchase(
    *,
    order: dict,
    event_id: str | None = None,
    event_source_url: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    fbp: str | None = None,
    fbc: str | None = None,
) -> None:
    name = order.get("customer_name") or ""
    parts = name.strip().split(None, 1)
    first = parts[0] if parts else None
    last = parts[1] if len(parts) > 1 else None

    contents = []
    for item in order.get("items") or []:
        contents.append(
            {
                "id": str(item.get("product_id") or item.get("id") or item.get("name")),
                "quantity": int(item.get("quantity") or item.get("qty") or 1),
                "item_price": float(item.get("price") or 0),
            }
        )

    user_data = build_user_data(
        email=order.get("customer_email"),
        phone=order.get("customer_phone"),
        first_name=first,
        last_name=last,
        city=order.get("address_city"),
        state=order.get("address_state"),
        zip_code=order.get("address_pincode"),
        client_ip=client_ip,
        user_agent=user_agent,
        fbp=fbp,
        fbc=fbc,
    )

    custom_data = {
        "currency": "INR",
        "value": float(order.get("total") or 0),
        "content_type": "product",
        "contents": contents,
        "order_id": order.get("order_id"),
        "num_items": sum(c["quantity"] for c in contents) or len(contents),
    }

    await send_event(
        "Purchase",
        event_id=event_id or order.get("order_id"),
        event_source_url=event_source_url
        or f"{(settings.FRONTEND_URL or '').rstrip('/')}/orders",
        user_data=user_data,
        custom_data=custom_data,
    )


async def track_generic(
    event_name: str,
    *,
    event_id: str | None = None,
    event_source_url: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    fbp: str | None = None,
    fbc: str | None = None,
    custom_data: dict | None = None,
) -> None:
    user_data = build_user_data(
        email=email,
        phone=phone,
        client_ip=client_ip,
        user_agent=user_agent,
        fbp=fbp,
        fbc=fbc,
    )
    await send_event(
        event_name,
        event_id=event_id,
        event_source_url=event_source_url,
        user_data=user_data,
        custom_data=custom_data,
    )
