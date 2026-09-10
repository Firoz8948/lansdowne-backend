from app.common import utcnow

ORDER_STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
PAYMENT_STATUSES = ["pending", "paid", "failed", "refunded"]

FREE_SHIPPING_THRESHOLD = 999
FLAT_SHIPPING_CHARGE = 49
FREE_WEIGHT_GRAMS = 1000
WEIGHT_SURCHARGE_PER_KG = 15


def generate_order_id() -> str:
    return "ORD-" + utcnow().strftime("%Y-%m%d%H%M%S")


def calc_shipping(subtotal: float, total_weight_grams: float = 0) -> float:
    if subtotal >= FREE_SHIPPING_THRESHOLD or subtotal <= 0:
        charge = 0.0
    else:
        charge = float(FLAT_SHIPPING_CHARGE)

    if total_weight_grams > FREE_WEIGHT_GRAMS:
        extra_kg = (total_weight_grams - FREE_WEIGHT_GRAMS) / 1000
        charge += round(extra_kg * WEIGHT_SURCHARGE_PER_KG, 2)

    return charge


def _item_weight_grams(item: dict) -> float:
    variant_info = item.get("variant_info") or {}
    if variant_info.get("weight_grams"):
        return float(variant_info["weight_grams"])
    if item.get("weight_grams"):
        return float(item["weight_grams"])
    weight = item.get("weight")
    if weight is None:
        return 0.0
    if isinstance(weight, (int, float)):
        return float(weight)
    return 0.0


def total_cart_weight_grams(items: list[dict]) -> float:
    return sum(_item_weight_grams(item) * int(item.get("qty", item.get("quantity", 1))) for item in items)


def normalize_items(items: list[dict]) -> list[dict]:
    normalized = []
    for item in items:
        qty = item.get("qty", item.get("quantity", 1))
        normalized.append(
            {
                "product_id": item.get("product_id"),
                "name": item["name"],
                "price": float(item["price"]),
                "qty": int(qty),
                "image": item.get("image"),
                "weight": item.get("weight"),
                "weight_grams": item.get("weight_grams"),
                "variant_info": item.get("variant_info"),
            }
        )
    return normalized


def calc_subtotal(items: list[dict]) -> float:
    return round(sum(i["price"] * i["qty"] for i in items), 2)


def new_guest_order_doc(
    customer: dict,
    address: dict,
    items: list[dict],
    payment_method: str,
    payment_status: str,
    order_status: str,
    razorpay_payment_id: str | None = None,
    razorpay_order_id: str | None = None,
) -> dict:
    now = utcnow()
    items = normalize_items(items)
    subtotal = calc_subtotal(items)
    shipping = calc_shipping(subtotal, total_cart_weight_grams(items))
    order_id = generate_order_id()

    return {
        "order_id": order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_order_id": razorpay_order_id,
        "customer": customer,
        "address": address,
        "items": items,
        "subtotal": subtotal,
        "shipping_charge": shipping,
        "total": round(subtotal + shipping, 2),
        "payment_method": payment_method,
        "payment_status": payment_status,
        "order_status": order_status,
        "created_at": now,
        "updated_at": now,
    }
