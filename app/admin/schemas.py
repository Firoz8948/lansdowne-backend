from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class AdminProfileUpdateRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None


class TokenData(BaseModel):
    admin_id: str
    email: str
    role: str


class ProductVariantOption(BaseModel):
    name: str
    price: float
    mrp: float
    stock: int
    weight: Optional[float] = None
    hex: Optional[str] = None
    colors: Optional[list[dict[str, str]]] = None
    image_url: Optional[str] = None
    images: Optional[list[str]] = None


class ProductVariant(BaseModel):
    name: str
    options: list[ProductVariantOption]


class ProductColorSwatch(BaseModel):
    name: str = ""
    hex: str


class ProductCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    price: float
    mrp: float
    category: str = ""
    category_id: Optional[int] = None
    category_ids: Optional[list[int]] = None
    stock: int = 0
    unit: Optional[str] = "grams"
    weight: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    is_featured: bool = False
    is_active: bool = True
    variants: Optional[list[ProductVariant]] = []
    metafields: Optional[dict[str, str]] = {}
    colors: Optional[list[ProductColorSwatch]] = None
    color_group_id: Optional[str] = None
    color_sibling_ids: Optional[list[int]] = None


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    mrp: Optional[float] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    category_ids: Optional[list[int]] = None
    stock: Optional[int] = None
    unit: Optional[str] = None
    weight: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    variants: Optional[list[ProductVariant]] = None
    metafields: Optional[dict[str, str]] = None
    colors: Optional[list[ProductColorSwatch]] = None
    color_group_id: Optional[str] = None
    color_sibling_ids: Optional[list[int]] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    price: float
    mrp: float
    category: str
    stock: int
    unit: Optional[str]
    weight: Optional[float]
    images: list[str]
    is_featured: bool
    is_active: bool
    variants: Optional[list[ProductVariant]] = []
    metafields: Optional[dict[str, str]] = {}
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class DashboardStats(BaseModel):
    total_orders: int
    total_revenue: float
    total_products: int
    active_products: int = 0
    total_customers: int = 0
    total_shipped: int
    recent_orders: list[Any]
    revenue_trend: list[Any]
