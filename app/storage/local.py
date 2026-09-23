from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings
from app.storage.base import ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT, build_key, validate_ext
from app.storage.optimize import optimize_image_bytes

URL_PREFIX = "/uploads"

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _configured_dir() -> Path:
    configured = (get_settings().UPLOAD_DIR or "").strip()
    if not configured:
        return _BACKEND_ROOT / "uploads"
    path = Path(configured)
    return path if path.is_absolute() else _BACKEND_ROOT / path


UPLOADS_DIR = _configured_dir()


def _should_optimize(ext: str, allowed_ext: set[str]) -> bool:
    """Optimize raster images only — never videos."""
    if allowed_ext & ALLOWED_VIDEO_EXT and ext in ALLOWED_VIDEO_EXT:
        return False
    return ext in ALLOWED_IMAGE_EXT or ext in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
    }


async def upload_file(
    file: UploadFile,
    folder: str,
    *,
    allowed_ext: set[str] = ALLOWED_IMAGE_EXT,
    default_ext: str = ".jpg",
) -> str:
    ext = validate_ext(file.filename, allowed_ext, default_ext)
    content = await file.read()

    if _should_optimize(ext, allowed_ext):
        content, ext, _ = optimize_image_bytes(content, source_ext=ext)

    key = build_key(folder, ext)
    destination = UPLOADS_DIR / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    return f"{URL_PREFIX}/{key}"


async def delete_file(url: str) -> None:
    key = _key_from_url(url)
    if not key:
        return

    root = UPLOADS_DIR.resolve()
    target = (root / key).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return

    target.unlink()


def _key_from_url(url: str) -> str:
    marker = f"{URL_PREFIX}/"
    index = (url or "").find(marker)
    if index == -1:
        return ""
    return url[index + len(marker) :].split("?", 1)[0].strip("/")
