from pydantic import BaseModel, Field


class BannerCreateRequest(BaseModel):
    device: str = Field(..., pattern="^(desktop|mobile)$")
    title: str | None = None
    title_highlight: str | None = None
    subtitle: str | None = None
    link_url: str | None = None
    position: int = 0
    is_active: bool = True


class BannerUpdateRequest(BaseModel):
    title: str | None = None
    title_highlight: str | None = None
    subtitle: str | None = None
    link_url: str | None = None
    position: int | None = None
    is_active: bool | None = None
