import re

from fastapi import HTTPException


def normalize_phone(phone: str) -> str:
    """Normalize Indian mobile numbers to 10 digits."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid 10-digit mobile number.",
        )
    if digits[0] not in "6789":
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid Indian mobile number.",
        )
    return digits
