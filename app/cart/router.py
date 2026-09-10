from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user

from . import service
from .schemas import AddToCartRequest, CartResponse, UpdateCartItemRequest

router = APIRouter()


@router.get("/", response_model=CartResponse)
async def get_cart(user: dict = Depends(get_current_user)):
    return await service.get_user_cart(user["id"])


@router.post("/add", response_model=CartResponse)
async def add_to_cart(payload: AddToCartRequest, user: dict = Depends(get_current_user)):
    return await service.add_to_cart(user["id"], payload.product_id, payload.quantity)


@router.put("/update/{item_id}", response_model=CartResponse)
async def update_item(
    item_id: str,
    payload: UpdateCartItemRequest,
    user: dict = Depends(get_current_user),
):
    return await service.update_item(user["id"], item_id, payload.quantity)


@router.delete("/remove/{item_id}", response_model=CartResponse)
async def remove_item(item_id: str, user: dict = Depends(get_current_user)):
    return await service.remove_item(user["id"], item_id)


@router.delete("/clear", response_model=CartResponse)
async def clear_cart(user: dict = Depends(get_current_user)):
    return await service.clear(user["id"])
