from pathlib import Path

from app.database import Base
import app.models  # noqa: F401


def test_orm_metadata_contains_categories_but_no_subcategory_schema():
    assert "categories" in Base.metadata.tables
    assert "subcategories" not in Base.metadata.tables
    assert "product_subcategories" not in Base.metadata.tables

    product_columns = Base.metadata.tables["products"].columns
    assert "category_id" in product_columns
    assert "subcategory_id" not in product_columns


def test_startup_migration_only_drops_legacy_subcategory_schema():
    source = Path("app/database.py").read_text(encoding="utf-8")

    assert "DROP TABLE IF EXISTS product_subcategories" in source
    assert "DROP TABLE IF EXISTS subcategories" in source
    assert "DROP COLUMN IF EXISTS subcategory_id" in source
    assert "CREATE TABLE IF NOT EXISTS subcategories" not in source
    assert "CREATE TABLE IF NOT EXISTS product_subcategories" not in source
