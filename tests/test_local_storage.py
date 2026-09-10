import asyncio
import tempfile
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app import storage
from app.storage import local


def _upload(filename: str, content: bytes = b"binary-image-bytes") -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename)


def _with_temp_uploads(func):
    """Point the local backend at a throwaway directory for one call."""
    original = local.UPLOADS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        local.UPLOADS_DIR = Path(tmp)
        try:
            return func(Path(tmp))
        finally:
            local.UPLOADS_DIR = original


def test_local_backend_is_selected_when_bunny_is_not_configured():
    assert storage.active_backend_name(bunny_configured=False) == "local"
    assert storage.active_backend_name(bunny_configured=True) == "bunny"


def test_local_upload_writes_the_file_and_returns_an_uploads_url():
    def scenario(uploads_dir: Path) -> None:
        url = asyncio.run(local.upload_file(_upload("tawa.png"), "products"))

        assert url.startswith("/uploads/products/")
        assert url.endswith(".png")

        saved = uploads_dir / url.removeprefix("/uploads/")
        assert saved.is_file()
        assert saved.read_bytes() == b"binary-image-bytes"

    _with_temp_uploads(scenario)


def test_local_upload_rejects_unsupported_extensions():
    def scenario(_: Path) -> None:
        try:
            asyncio.run(local.upload_file(_upload("payload.exe"), "products"))
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("expected unsupported file type to be rejected")

    _with_temp_uploads(scenario)


def test_local_delete_removes_a_previously_uploaded_file():
    def scenario(uploads_dir: Path) -> None:
        url = asyncio.run(local.upload_file(_upload("belan.jpg"), "products"))
        saved = uploads_dir / url.removeprefix("/uploads/")

        asyncio.run(local.delete_file(url))

        assert not saved.exists()

    _with_temp_uploads(scenario)


def test_local_delete_cannot_escape_the_uploads_directory():
    def scenario(uploads_dir: Path) -> None:
        outside = uploads_dir.parent / "secret.env"
        outside.write_text("keep me", encoding="utf-8")

        asyncio.run(local.delete_file("/uploads/../secret.env"))

        assert outside.is_file()

    _with_temp_uploads(scenario)
