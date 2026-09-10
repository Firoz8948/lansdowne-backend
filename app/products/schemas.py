from pydantic import BaseModel, Field


class ProductVariantOption(BaseModel):
    name: str
    price: float
    mrp: float
    stock: int
    weight: float | None = None


class ProductVariant(BaseModel):
    name: str
    options: list[ProductVariantOption]


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(..., ge=0)
    mrp: float | None = Field(default=None, ge=0)
    category: str
    stock: int = Field(default=0, ge=0)
    unit: str = "grams"
    weight: float | None = Field(default=None, ge=0, description="Weight value in the chosen unit")
    length_cm: float | None = Field(default=None, ge=0)
    breadth_cm: float | None = Field(default=None, ge=0)
    height_cm: float | None = Field(default=None, ge=0)
    images: list[str] = []
    is_featured: bool = False
    is_active: bool = True
    variants: list[ProductVariant] = []
    tags: list[str] = []
    metafields: dict[str, str] = {}
    seo_title: str | None = ""
    seo_description: str | None = ""


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0)
    mrp: float | None = Field(default=None, ge=0)
    category: str | None = None
    stock: int | None = Field(default=None, ge=0)
    unit: str | None = None
    weight: float | None = Field(default=None, ge=0)
    length_cm: float | None = Field(default=None, ge=0)
    breadth_cm: float | None = Field(default=None, ge=0)
    height_cm: float | None = Field(default=None, ge=0)
    images: list[str] | None = None
    is_featured: bool | None = None
    is_active: bool | None = None
    variants: list[ProductVariant] | None = None
    tags: list[str] | None = None
    metafields: dict[str, str] | None = None
    seo_title: str | None = None
    seo_description: str | None = None


class ProductResponse(ProductBase):
    id: str
    slug: str
    category_id: int | None = None
    category_slug: str | None = None


class PaginatedProducts(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None
    image: str | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    image: str | None = None
