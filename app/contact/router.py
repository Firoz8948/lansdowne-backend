from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_admin

from . import service
from .schemas import ContactResponse, ContactSubmitRequest

router = APIRouter()


@router.post("/submit", response_model=ContactResponse)
async def submit(payload: ContactSubmitRequest):
    return await service.submit(payload.model_dump())


@router.get("/", response_model=list[ContactResponse])
async def list_messages(_: dict = Depends(get_current_admin)):
    return await service.list_messages()
