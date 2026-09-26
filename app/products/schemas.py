from pydantic import BaseModel, ConfigDict, Field


class ProductVariantOption(BaseModel):
    id: int | None = None
    name: str
    price: float
    mrp: float
    stock: int
    weight: float | None = None
    hex: str | None = None
    colors: list[dict] = []
    image_url: str | None = None
    images: list[str] = []


class ProductVariant(BaseModel):
    id: int | None = None
    name: str
    options: list[ProductVariantOption]


class ProductColorSwatch(BaseModel):
    name: str = ""
    hex: str


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
    metafields: dict[str, str] = {}
    colors: list[ProductColorSwatch] = []
    color_group_id: str | None = None


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
    metafields: dict[str, str] | None = None
    colors: list[ProductColorSwatch] | None = None
    color_group_id: str | None = None


class ColorSibling(BaseModel):
    id: str
    slug: str
    name: str
    colors: list[ProductColorSwatch] = []
    image: str | None = None
    price: float | None = None
    mrp: float | None = None
    is_current: bool = False


class ProductResponse(ProductBase):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    category_id: int | None = None
    category_slug: str | None = None
    category_ids: list[int] = []
    categories: list[dict] = []
    color_siblings: list[ColorSibling] = []
    seo_title: str | None = ""
    seo_description: str | None = ""
    updated_at: str | None = None
    length_cm: float | None = None
    breadth_cm: float | None = None
    height_cm: float | None = None


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
