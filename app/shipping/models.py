from app.common import utcnow


def new_shipment_doc(order_id: str) -> dict:
    now = utcnow()
    return {
        "order_id": order_id,
        "shiprocket_order_id": None,
        "shipment_id": None,
        "awb_code": None,
        "courier_name": None,
        "status": "pending",
        "tracking_url": None,
        "created_at": now,
        "updated_at": now,
    }
