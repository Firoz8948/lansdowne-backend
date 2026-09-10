from types import SimpleNamespace

from app.cart.service import _build_cart_response


def test_build_empty_cart():
    result = _build_cart_response("user1", None)
    assert result["items"] == []
    assert result["total_items"] == 0
    assert result["total_amount"] == 0.0


def test_build_cart_totals():
    cart = SimpleNamespace(
        id=1,
        items=[
            SimpleNamespace(
                id=1,
                product_id=1,
                name="Tawa",
                slug="tawa",
                price=100.0,
                image=None,
                quantity=2,
            ),
            SimpleNamespace(
                id=2,
                product_id=2,
                name="Kadhai",
                slug="kadhai",
                price=50.0,
                image=None,
                quantity=1,
            ),
        ],
    )
    result = _build_cart_response("user1", cart)
    assert result["total_items"] == 3
    assert result["total_amount"] == 250.0
    assert result["items"][0]["subtotal"] == 200.0
