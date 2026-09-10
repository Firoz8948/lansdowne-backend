from pydantic import BaseModel, EmailStr, Field


class ContactSubmitRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = None
    subject: str | None = None
    message: str = Field(..., min_length=5, max_length=2000)


class ContactResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None = None
    subject: str | None = None
    message: str
    is_read: bool
    created_at: str | None = None
