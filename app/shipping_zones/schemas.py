from pydantic import BaseModel, Field, field_validator, model_validator


class ShippingZoneCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    is_all_india: bool = False
    states: list[str] = Field(default_factory=list)
    rate: float | None = Field(None, ge=0)
    prepaid_rate: float | None = Field(None, ge=0)
    cod_rate: float | None = Field(None, ge=0)
    free_shipping_threshold: float | None = Field(None, ge=0)
    is_active: bool = True
    position: int = 0

    @field_validator("states")
    @classmethod
    def normalize_states(cls, v: list[str], info) -> list[str]:
        is_all = info.data.get("is_all_india")
        cleaned = [s.strip() for s in v if s and str(s).strip()]
        if is_all:
            return []
        return cleaned

    @model_validator(mode="after")
    def normalize_rates(self):
        prepaid = self.prepaid_rate if self.prepaid_rate is not None else self.rate
        cod = self.cod_rate if self.cod_rate is not None else prepaid
        if prepaid is None:
            raise ValueError("prepaid_rate (or rate) is required")
        self.prepaid_rate = float(prepaid)
        self.cod_rate = float(cod if cod is not None else prepaid)
        self.rate = float(self.prepaid_rate)
        return self


class ShippingZoneUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    is_all_india: bool | None = None
    states: list[str] | None = None
    rate: float | None = Field(None, ge=0)
    prepaid_rate: float | None = Field(None, ge=0)
    cod_rate: float | None = Field(None, ge=0)
    free_shipping_threshold: float | None = Field(None, ge=0)
    is_active: bool | None = None
    position: int | None = None


class ShippingQuoteRequest(BaseModel):
    subtotal: float = Field(..., ge=0)
    state: str | None = None
    pincode: str | None = None
    weight_grams: float = 0
    payment_method: str | None = Field(
        default="prepaid", description="cod | prepaid | razorpay"
    )
