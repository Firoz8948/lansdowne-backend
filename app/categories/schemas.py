from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CategoryCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    image_url: Optional[str] = None
    seo_title: Optional[str] = ""
    seo_description: Optional[str] = ""
    is_active: bool = True
    position: int = 0


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    is_active: Optional[bool] = None
    position: Optional[int] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    image_url: Optional[str]
    seo_title: Optional[str] = ""
    seo_description: Optional[str] = ""
    is_active: bool
    position: int
    is_reels: bool = False
    product_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
