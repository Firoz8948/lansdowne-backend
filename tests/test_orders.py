from app.orders.models import calc_shipping, calc_subtotal, generate_order_id, new_guest_order_doc


def test_order_id_prefix():
    assert generate_order_id().startswith("ORD-")


def test_free_shipping_above_threshold():
    assert calc_shipping(1500) == 0.0


def test_flat_shipping_below_threshold():
    assert calc_shipping(500) == 49.0


def test_new_guest_order_doc_totals():
    doc = new_guest_order_doc(
        customer={"name": "Rahul", "mobile": "9876543210"},
        address={"line1": "123 MG Road", "city": "Mumbai", "state": "MH", "pincode": "400001"},
        items=[{"product_id": "p1", "name": "Iron Tawa", "price": 499, "qty": 2}],
        payment_method="razorpay",
        payment_status="paid",
        order_status="processing",
        razorpay_payment_id="pay_xxx",
    )
    assert doc["total"] == 1047.0  # 998 subtotal + 49 shipping
    assert doc["order_status"] == "processing"
    assert doc["payment_status"] == "paid"
    assert doc["customer"]["name"] == "Rahul"


def test_calc_subtotal():
    items = [{"name": "A", "price": 100, "qty": 2}, {"name": "B", "price": 50, "qty": 1}]
    assert calc_subtotal(items) == 250.0
