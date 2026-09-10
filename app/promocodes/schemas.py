from datetime import date

from pydantic import BaseModel, Field, field_validator


class PromoCodeCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    action_type: str = Field(..., pattern="^(free_shipping|percent_off)$")
    percent_value: float | None = Field(None, ge=1, le=100)
    valid_from: date
    valid_to: date
    audience: str = Field("all", pattern="^(all|new_users)$")
    max_uses: int | None = Field(None, ge=1)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("valid_to")
    @classmethod
    def check_dates(cls, v: date, info) -> date:
        valid_from = info.data.get("valid_from")
        if valid_from and v < valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        return v


class PromoCodeUpdateRequest(BaseModel):
    code: str | None = Field(None, min_length=2, max_length=50)
    action_type: str | None = Field(None, pattern="^(free_shipping|percent_off)$")
    percent_value: float | None = Field(None, ge=1, le=100)
    valid_from: date | None = None
    valid_to: date | None = None
    audience: str | None = Field(None, pattern="^(all|new_users)$")
    max_uses: int | None = Field(None, ge=1)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v


class PromoValidateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    subtotal: float = Field(..., ge=0)
    shipping_charge: float | None = Field(None, ge=0)
    phone: str | None = Field(None, max_length=20)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str | None) -> str | None:
        if not v:
            return None
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) >= 10:
            return digits[-10:]
        return digits or None
