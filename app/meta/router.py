from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.meta import capi

router = APIRouter()


class MetaEventRequest(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=64)
    event_id: str | None = None
    event_source_url: str | None = None
    email: str | None = None
    phone: str | None = None
    fbp: str | None = None
    fbc: str | None = None
    custom_data: dict | None = None


@router.post("/events")
async def forward_browser_event(payload: MetaEventRequest, request: Request):
    """
    Optional bridge so the browser can also send CAPI events (with hashed PII).
    Purchase is primarily sent from order/payment success on the server.
    """
    if not capi.meta_configured():
        return {"ok": False, "reason": "meta_not_configured"}

    client_ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    user_agent = request.headers.get("user-agent")

    await capi.track_generic(
        payload.event_name,
        event_id=payload.event_id,
        event_source_url=payload.event_source_url,
        email=payload.email,
        phone=payload.phone,
        client_ip=client_ip,
        user_agent=user_agent,
        fbp=payload.fbp,
        fbc=payload.fbc,
        custom_data=payload.custom_data,
    )
    return {"ok": True}
