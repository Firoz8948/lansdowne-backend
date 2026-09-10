"""PayU Biz hosted checkout helpers (hash + verify API)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("payments.payu")

PAYU_LIVE_PAYMENT_URL = "https://secure.payu.in/_payment"
PAYU_TEST_PAYMENT_URL = "https://test.payu.in/_payment"
PAYU_LIVE_INFO_URL = "https://info.payu.in/merchant/postservice.php?form=2"
PAYU_TEST_INFO_URL = "https://test.payu.in/merchant/postservice.php?form=2"


def payu_configured() -> bool:
    return bool(settings.PAYU_KEY and settings.PAYU_SALT)


def payment_url() -> str:
    mode = (settings.PAYU_MODE or "live").strip().lower()
    if mode in {"test", "sandbox"}:
        return PAYU_TEST_PAYMENT_URL
    return PAYU_LIVE_PAYMENT_URL


def info_url() -> str:
    mode = (settings.PAYU_MODE or "live").strip().lower()
    if mode in {"test", "sandbox"}:
        return PAYU_TEST_INFO_URL
    return PAYU_LIVE_INFO_URL


def format_amount(amount: float) -> str:
    return f"{float(amount):.2f}"


def request_hash(
    *,
    key: str,
    txnid: str,
    amount: str,
    productinfo: str,
    firstname: str,
    email: str,
    salt: str,
    udf1: str = "",
    udf2: str = "",
    udf3: str = "",
    udf4: str = "",
    udf5: str = "",
) -> str:
    # key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||SALT
    raw = (
        f"{key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|"
        f"{udf1}|{udf2}|{udf3}|{udf4}|{udf5}||||||{salt}"
    )
    return hashlib.sha512(raw.encode("utf-8")).hexdigest().lower()


def response_hash(params: dict[str, Any], salt: str | None = None) -> str:
    """Reverse hash for PayU browser/s2s callback validation."""
    salt = salt or settings.PAYU_SALT
    status = str(params.get("status") or "")
    email = str(params.get("email") or "")
    firstname = str(params.get("firstname") or "")
    productinfo = str(params.get("productinfo") or "")
    amount = str(params.get("amount") or "")
    txnid = str(params.get("txnid") or "")
    key = str(params.get("key") or settings.PAYU_KEY)
    udf1 = str(params.get("udf1") or "")
    udf2 = str(params.get("udf2") or "")
    udf3 = str(params.get("udf3") or "")
    udf4 = str(params.get("udf4") or "")
    udf5 = str(params.get("udf5") or "")

    # salt|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key
    raw = (
        f"{salt}|{status}||||||{udf5}|{udf4}|{udf3}|{udf2}|{udf1}|"
        f"{email}|{firstname}|{productinfo}|{amount}|{txnid}|{key}"
    )
    additional = str(params.get("additionalCharges") or "").strip()
    if additional:
        raw = f"{additional}|{raw}"
    return hashlib.sha512(raw.encode("utf-8")).hexdigest().lower()


def verify_response_hash(params: dict[str, Any]) -> bool:
    received = str(params.get("hash") or "").lower()
    if not received or not settings.PAYU_SALT:
        return False
    return received == response_hash(params)


def command_hash(command: str, var1: str = "") -> str:
    raw = f"{settings.PAYU_KEY}|{command}|{var1}|{settings.PAYU_SALT}"
    return hashlib.sha512(raw.encode("utf-8")).hexdigest().lower()


async def verify_payment_api(txnid: str) -> dict:
    """Server-to-server verify_payment (extra confirmation after redirect)."""
    if not payu_configured():
        raise RuntimeError("PayU is not configured")
    payload = {
        "key": settings.PAYU_KEY,
        "command": "verify_payment",
        "var1": txnid,
        "hash": command_hash("verify_payment", txnid),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(info_url(), data=payload)
        res.raise_for_status()
        try:
            return res.json()
        except Exception:
            logger.warning("PayU verify_payment non-JSON: %s", res.text[:500])
            return {"raw": res.text, "status": res.status_code}


async def probe_credentials() -> dict:
    """
    Lightweight credential check via get_merchant_details / verify_payment.
    Does not charge a customer.
    """
    if not payu_configured():
        return {"ok": False, "error": "PAYU_KEY / PAYU_SALT missing"}

    # verify_payment on a fake txnid still authenticates key+salt+hash
    fake_txn = "cd_probe_000000"
    try:
        data = await verify_payment_api(fake_txn)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    # Wrong key/salt usually returns status=0 with message about hash/key
    status = data.get("status")
    msg = str(data.get("msg") or data.get("message") or "").lower()
    if status == 0 and ("hash" in msg or "key" in msg or "invalid" in msg):
        return {"ok": False, "error": data.get("msg") or data.get("message") or data}

    # status 1 with empty transaction_details, or status 0 "Transaction not found"
    # both mean credentials were accepted by PayU.
    if status in (0, 1, "0", "1") or "transaction_details" in data:
        return {
            "ok": True,
            "mode": settings.PAYU_MODE,
            "key": settings.PAYU_KEY,
            "probe": data,
        }
    return {"ok": False, "error": data}
