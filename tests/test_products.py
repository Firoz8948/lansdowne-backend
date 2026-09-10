from app.products.models import slugify


def test_slugify_basic():
    assert slugify("Premium Iron Tawa") == "premium-iron-tawa"


def test_slugify_special_chars():
    assert slugify("Kadhai & Lid (3L)!!") == "kadhai-lid-3l"


def test_slugify_collapses_spaces():
    assert slugify("  Cast   Iron   Set  ") == "cast-iron-set"
