"""Media storage: local disk by default, BunnyCDN when it is configured."""

from fastapi import UploadFile

from app.config import get_settings
from app.storage import bunny, local
from app.storage.base import ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT

__all__ = [
    "ALLOWED_IMAGE_EXT",
    "ALLOWED_VIDEO_EXT",
    "active_backend_name",
    "delete_file",
    "upload_file",
]


def active_backend_name(*, bunny_configured: bool | None = None) -> str:
    preference = (get_settings().STORAGE_BACKEND or "auto").strip().lower()
    if preference in ("local", "bunny"):
        return preference

    if bunny_configured is None:
        bunny_configured = bunny.is_configured()
    return "bunny" if bunny_configured else "local"


def _backend():
    return bunny if active_backend_name() == "bunny" else local


async def upload_file(
    file: UploadFile,
    folder: str,
    *,
    allowed_ext: set[str] = ALLOWED_IMAGE_EXT,
    default_ext: str = ".jpg",
) -> str:
    return await _backend().upload_file(
        file,
        folder,
        allowed_ext=allowed_ext,
        default_ext=default_ext,
    )


async def delete_file(url: str) -> None:
    await _backend().delete_file(url)
