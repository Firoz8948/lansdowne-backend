from typing import Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    address_landmark: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_pincode: str | None = None
    role: str = "customer"
    is_active: bool = True
    created_at: str | None = None


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_landmark: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_pincode: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
