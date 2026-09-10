from app.common import utcnow


def new_pending_payment_doc(
    amount: float,
    razorpay_order_id: str,
    checkout: dict,
) -> dict:
    now = utcnow()
    return {
        "order_id": None,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": None,
        "razorpay_signature": None,
        "amount": round(amount, 2),
        "currency": "INR",
        "status": "created",
        "checkout": checkout,
        "created_at": now,
        "updated_at": now,
    }
