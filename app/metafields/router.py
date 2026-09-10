from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.database import get_db

from . import service
from .schemas import MetafieldDefinitionCreate, MetafieldDefinitionUpdate

router = APIRouter()


@router.get("/")
async def list_metafields(db: AsyncSession = Depends(get_db)):
    """Public list of active metafield definitions (for product pages)."""
    return await service.list_definitions(db, active_only=True)


@router.get("/admin/all")
async def list_all_metafields(
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_definitions(db, active_only=False)


@router.post("/", status_code=201)
async def create_metafield(
    body: MetafieldDefinitionCreate,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_definition(db, body.name)


@router.put("/{definition_id}")
async def update_metafield(
    definition_id: int,
    body: MetafieldDefinitionUpdate,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updated = await service.update_definition(
        db, definition_id, body.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Metafield not found")
    return updated


@router.delete("/{definition_id}")
async def delete_metafield(
    definition_id: int,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_definition(db, definition_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Metafield not found")
    return {"ok": True}
