"""Convert uploaded images to optimized WebP before storage."""

from __future__ import annotations

import io
import logging

from fastapi import HTTPException

logger = logging.getLogger("storage")

# Raster formats we re-encode to WebP. GIFs kept as-is (may be animated).
_CONVERTIBLE = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# High visual quality; still much smaller than typical PNG/JPEG uploads.
_WEBP_QUALITY = 85
_MAX_EDGE = 2400


def optimize_image_bytes(
    content: bytes,
    *,
    source_ext: str,
) -> tuple[bytes, str, str]:
    """Return (bytes, extension, content_type).

    PNG/JPEG/WebP → optimized WebP. Other / failed conversions return original.
    """
    ext = (source_ext or "").lower()
    if ext not in _CONVERTIBLE or not content:
        return content, ext or ".jpg", _guess_content_type(ext)

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        logger.warning("Pillow not installed — uploading original image")
        return content, ext, _guess_content_type(ext)

    try:
        with Image.open(io.BytesIO(content)) as img:
            img = ImageOps.exif_transpose(img)

            # Animated / multi-frame: keep original to avoid breaking animation.
            n_frames = getattr(img, "n_frames", 1) or 1
            if n_frames > 1:
                return content, ext, _guess_content_type(ext)

            if img.mode in ("P", "LA"):
                img = img.convert("RGBA")
            elif img.mode == "CMYK":
                img = img.convert("RGB")
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            w, h = img.size
            longest = max(w, h)
            if longest > _MAX_EDGE:
                scale = _MAX_EDGE / float(longest)
                img = img.resize(
                    (max(1, int(w * scale)), max(1, int(h * scale))),
                    Image.Resampling.LANCZOS,
                )

            out = io.BytesIO()
            save_kwargs = {
                "format": "WEBP",
                "quality": _WEBP_QUALITY,
                "method": 6,
            }
            if img.mode == "RGBA":
                save_kwargs["lossless"] = False
            img.save(out, **save_kwargs)
            webp_bytes = out.getvalue()

            # Keep original only if somehow larger after conversion (rare).
            if len(webp_bytes) >= len(content) and ext == ".webp":
                return content, ".webp", "image/webp"

            logger.info(
                "Image optimized %s → webp (%s KB → %s KB)",
                ext,
                max(1, len(content) // 1024),
                max(1, len(webp_bytes) // 1024),
            )
            return webp_bytes, ".webp", "image/webp"
    except Exception as exc:
        logger.exception("Image optimization failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Could not process this image. Please upload a valid JPG or PNG.",
        ) from exc


def _guess_content_type(ext: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(ext, "application/octet-stream")
