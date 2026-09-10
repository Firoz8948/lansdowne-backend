from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.banners import service
from app.banners.schemas import BannerCreateRequest, BannerUpdateRequest
from app.database import get_db
from app.storage import upload_file

router = APIRouter()


@router.get("/")
async def public_banners(
    device: str | None = Query(None, pattern="^(desktop|mobile)$"),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_banners(db, device=device, active_only=True)


@router.get("/admin/all")
async def admin_list_banners(
    device: str | None = Query(None, pattern="^(desktop|mobile)$"),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_banners(db, device=device, active_only=False)


@router.post("/", status_code=201)
async def create_banner(
    body: BannerCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_banner(db, body.model_dump())


@router.put("/{banner_id}")
async def update_banner(
    banner_id: int,
    body: BannerUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = await service.update_banner(db, banner_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Banner not found")
    return updated


@router.delete("/{banner_id}")
async def delete_banner(
    banner_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_banner(db, banner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Banner not found")
    return {"message": "Banner deleted"}


@router.post("/{banner_id}/image")
async def upload_banner_image(
    banner_id: int,
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    url = await upload_file(file, "banners")
    updated = await service.set_banner_image(db, banner_id, url)
    if not updated:
        raise HTTPException(status_code=404, detail="Banner not found")
    return updated
