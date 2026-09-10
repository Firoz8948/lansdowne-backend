from fastapi import APIRouter, Query

from . import service
from .schemas import CategoryResponse, PaginatedProducts, ProductResponse

router = APIRouter()


@router.get("/", response_model=PaginatedProducts)
async def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    category: str | None = None,
    category_slug: str | None = None,
    search: str | None = None,
    sort: str | None = None,
):
    return await service.list_products(
        page=page,
        page_size=page_size,
        category=category,
        category_slug=category_slug,
        search=search,
        sort=sort,
    )


@router.get("/featured", response_model=list[ProductResponse])
async def get_featured():
    result = await service.list_products(page=1, page_size=12, featured=True)
    return result["items"]


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories():
    return await service.list_categories()


@router.get("/search", response_model=PaginatedProducts)
async def search_products(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
):
    return await service.list_products(page=page, page_size=page_size, search=q)


@router.get("/category/{name}", response_model=PaginatedProducts)
async def get_by_category(
    name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
):
    return await service.list_products(page=page, page_size=page_size, category=name)


@router.get("/{slug}", response_model=ProductResponse)
async def get_product(slug: str):
    return await service.get_product_by_slug(slug)
