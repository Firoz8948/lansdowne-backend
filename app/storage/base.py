import uuid
from pathlib import Path

from fastapi import HTTPException

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".avi"}


def validate_ext(filename: str | None, allowed: set[str], default: str = ".jpg") -> str:
    ext = Path(filename or "").suffix.lower() or default
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    return ext


def build_key(folder: str, ext: str) -> str:
    return f"{folder.strip('/')}/{uuid.uuid4().hex}{ext}"
