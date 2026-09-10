from datetime import datetime, timezone

from sqlalchemy import inspect as sa_inspect


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_product(product, include_relations=True) -> dict:
    def _loaded(name: str):
        """Return relationship only if already eagerly loaded (async-safe)."""
        try:
            state = sa_inspect(product)
            if name in state.unloaded:
                return None
            return getattr(product, name)
        except Exception:
            return None

    data = {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "price": product.price,
        "mrp": product.mrp,
        "category": product.category,
        "category_id": product.category_id,
        "category_slug": None,
        "stock": product.stock,
        "unit": product.unit,
        "weight": product.weight,
        "length_cm": getattr(product, "length_cm", None),
        "breadth_cm": getattr(product, "breadth_cm", None),
        "height_cm": getattr(product, "height_cm", None),
        "is_featured": product.is_featured,
        "is_active": product.is_active,
        "tags": product.tags or [],
        "metafields": product.metafields or {},
        "seo_title": getattr(product, "seo_title", None) or "",
        "seo_description": getattr(product, "seo_description", None) or "",
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }
    cat_rel = _loaded("category_rel")
    if cat_rel is not None:
        data["category_slug"] = getattr(cat_rel, "slug", None)
    if include_relations:
        images = _loaded("images")
        data["images"] = [img.url for img in (images or [])]
        variants = _loaded("variants")
        data["variants"] = [
            {
                "id": v.id,
                "name": v.name,
                "options": [
                    {
                        "id": o.id,
                        "name": o.name,
                        "price": o.price,
                        "mrp": o.mrp,
                        "stock": o.stock,
                        "weight": o.weight,
                    }
                    for o in (v.options or [])
                ],
            }
            for v in (variants or [])
        ]
    return data


def serialize_order(order) -> dict:
    shipment_data = None
    try:
        insp = sa_inspect(order)
        if "shipment" not in insp.unloaded:
            rel = order.shipment
            shipment_data = serialize_shipment(rel) if rel else None
    except Exception:
        shipment_data = None

    return {
        "id": str(order.id),
        "order_id": order.order_id,
        "customer": {
            "name": order.customer_name,
            "phone": order.customer_phone,
            "mobile": order.customer_phone,
            "email": order.customer_email,
        },
        "address": {
            "line1": order.address_line1,
            "line2": order.address_line2,
            "landmark": getattr(order, "address_landmark", None) or "",
            "city": order.address_city,
            "state": order.address_state,
            "pincode": order.address_pincode,
        },
        "subtotal": order.subtotal,
        "shipping_charge": order.shipping_charge,
        "discount_amount": getattr(order, "discount_amount", 0) or 0,
        "promo_code": getattr(order, "promo_code", None),
        "total": order.total,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "order_status": order.order_status,
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_id": order.razorpay_payment_id,
        "items": [
            {
                "id": item.id,
                "product_id": str(item.product_id) if item.product_id else None,
                "name": item.name,
                "slug": item.slug,
                "price": item.price,
                "quantity": item.quantity,
                "qty": item.quantity,
                "image": item.image,
                "variant_info": item.variant_info,
            }
            for item in (order.items or [])
        ],
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "shipment": shipment_data,
    }


def serialize_payment(payment) -> dict:
    return {
        "id": str(payment.id),
        "order_db_id": str(payment.order_db_id) if payment.order_db_id else None,
        "razorpay_order_id": payment.razorpay_order_id,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "razorpay_refund_id": getattr(payment, "razorpay_refund_id", None),
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "failure_reason": getattr(payment, "failure_reason", None),
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": (
            payment.updated_at.isoformat()
            if getattr(payment, "updated_at", None)
            else None
        ),
    }


def serialize_admin(admin) -> dict:
    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.name,
        "phone": getattr(admin, "phone", None) or "",
        "company_name": getattr(admin, "company_name", None) or "",
        "role": admin.role,
        "is_active": admin.is_active,
    }


def serialize_user(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "name": user.name,
        "address_line1": getattr(user, "address_line1", None) or "",
        "address_line2": getattr(user, "address_line2", None) or "",
        "address_landmark": getattr(user, "address_landmark", None) or "",
        "address_city": getattr(user, "address_city", None) or "",
        "address_state": getattr(user, "address_state", None) or "",
        "address_pincode": getattr(user, "address_pincode", None) or "",
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def serialize_contact(contact) -> dict:
    return {
        "id": str(contact.id),
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "subject": contact.subject,
        "message": contact.message,
        "is_read": contact.is_read,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


def serialize_shipment(shipment) -> dict:
    return {
        "id": str(shipment.id),
        "order_id": shipment.order_id,
        "awb_code": shipment.awb_code,
        "courier_name": shipment.courier_name,
        "status": shipment.status,
        "tracking_url": shipment.tracking_url,
        "shiprocket_order_id": shipment.shiprocket_order_id,
        "shiprocket_shipment_id": shipment.shiprocket_shipment_id,
        "shipmozo_reference_id": getattr(shipment, "shipmozo_reference_id", None),
        "created_at": shipment.created_at.isoformat() if shipment.created_at else None,
        "updated_at": shipment.updated_at.isoformat() if shipment.updated_at else None,
    }
