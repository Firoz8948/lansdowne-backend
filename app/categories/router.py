from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.categories import service
from app.categories.schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
)
from app.database import get_db
from app.storage import upload_file

router = APIRouter()


@router.get("/")
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await service.get_all_categories(db, include_inactive=False)


@router.get("/admin/all")
async def admin_list_categories(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_all_categories(db, include_inactive=True)


@router.get("/slug/{slug}")
async def get_category_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    cat = await service.get_category_by_slug(db, slug)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@router.get("/{category_id}/products")
async def get_category_products(
    category_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_category_products(db, category_id, page, limit)


@router.get("/{category_id}")
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    cat = await service.get_category_by_id(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@router.post("/", status_code=201)
async def create_category(
    body: CategoryCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_category(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    body: CategoryUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        updated = await service.update_category(
            db,
            category_id,
            {k: v for k, v in body.model_dump().items() if v is not None},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        deleted = await service.delete_category(db, category_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}


@router.post("/{category_id}/image")
async def upload_category_image(
    category_id: int,
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    cat = await service.get_category_by_id(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    image_url = await upload_file(file, "categories")
    return await service.set_category_image(db, category_id, image_url)
