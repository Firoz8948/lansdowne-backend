from pydantic import BaseModel, EmailStr, Field


class CustomerInfo(BaseModel):
    name: str = Field(..., min_length=2)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: EmailStr | None = None


class AddressInfo(BaseModel):
    line1: str
    line2: str | None = None
    landmark: str | None = None
    city: str
    state: str
    pincode: str
    country: str = "India"


class OrderItem(BaseModel):
    product_id: str | None = None
    name: str
    price: float
    quantity: int = Field(..., ge=1)
    image: str | None = None
    weight: str | None = None
    weight_grams: float | None = None
    variant_info: dict | None = None


class GuestCreateOrderRequest(BaseModel):
    customer: CustomerInfo
    address: AddressInfo
    items: list[OrderItem] = Field(..., min_length=1)
    payment_method: str = Field(default="cod", description="cod | razorpay")
    promo_code: str | None = None
    # Meta Pixel / CAPI deduplication
    meta_event_id: str | None = None
    meta_fbp: str | None = None
    meta_fbc: str | None = None


CreateOrderRequest = GuestCreateOrderRequest


class OrderResponse(BaseModel):
    id: str
    order_id: str
    razorpay_payment_id: str | None = None
    customer: CustomerInfo
    address: AddressInfo
    items: list[OrderItem]
    subtotal: float
    shipping_charge: float
    discount_amount: float = 0
    promo_code: str | None = None
    total: float
    payment_method: str
    payment_status: str
    order_status: str
    created_at: str | None = None


class UpdateStatusRequest(BaseModel):
    status: str
