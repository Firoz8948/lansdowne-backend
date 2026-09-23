"""Shared Renflair SMS helpers."""

from __future__ import annotations

from typing import Any, Optional


def renflair_failure_message(data: Any) -> Optional[str]:
    """Return an error string if Renflair JSON/text indicates failure."""
    if data is None:
        return "Empty response from SMS provider"

    if isinstance(data, dict):
        status = str(data.get("status") or data.get("Status") or "").strip().upper()
        message = str(
            data.get("message") or data.get("Message") or data.get("msg") or ""
        ).strip()
        if status in {"FAILED", "FAIL", "ERROR", "FALSE", "0"}:
            return message or f"SMS provider status: {status}"
        if message.upper() in {
            "INCORRECT API KEY",
            "INVALID API KEY",
            "INSUFFICIENT BALANCE",
        }:
            return message
        if data.get("success") is False or data.get("error"):
            return message or str(data.get("error") or "SMS send failed")
        return None

    if isinstance(data, str):
        upper = data.upper()
        if "INCORRECT API KEY" in upper or '"STATUS":"FAILED"' in upper:
            return data.strip()
    return None
