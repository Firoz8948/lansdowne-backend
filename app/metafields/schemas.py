from pydantic import BaseModel, Field


class MetafieldDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)


class MetafieldDefinitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    position: int | None = None
    is_active: bool | None = None


class MetafieldDefinitionResponse(BaseModel):
    id: str
    name: str
    key: str
    position: int
    is_active: bool
