from typing import Optional

from pydantic import BaseModel


class SendOTPRequest(BaseModel):
    phone: str
    name: Optional[str] = ""


class SendOTPResponse(BaseModel):
    message: str
    phone: str
    otp: Optional[str] = None
    debug: Optional[bool] = False


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = ""


class VerifyOTPResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: dict
