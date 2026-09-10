from pydantic import BaseModel, Field


class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    item_id: str
    product_id: str
    name: str
    slug: str
    price: float
    image: str | None = None
    quantity: int
    subtotal: float


class CartResponse(BaseModel):
    id: str | None = None
    user_id: str
    items: list[CartItemResponse]
    total_items: int
    total_amount: float
