from datetime import datetime, timezone
import re

from sqlalchemy import inspect as sa_inspect


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


_HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")


def _normalize_hex(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not _HEX_RE.match(raw):
        return None
    if not raw.startswith("#"):
        raw = f"#{raw}"
    if len(raw) == 4:
        raw = "#" + "".join(ch * 2 for ch in raw[1:])
    return raw.upper()


def _normalize_colors(raw) -> list[dict]:
    """Accept [{name, hex}] or list of hex strings; return clean [{name, hex}]."""
    if not raw:
        return []
    out: list[dict] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                hex_val = _normalize_hex(item.get("hex") or item.get("color"))
                if not hex_val:
                    continue
                name = (item.get("name") or "").strip() or hex_val
                out.append({"name": name[:80], "hex": hex_val})
            elif isinstance(item, str):
                hex_val = _normalize_hex(item)
                if hex_val:
                    out.append({"name": hex_val, "hex": hex_val})
    return out[:6]


def serialize_color_sibling(product) -> dict:
    images = []
    try:
        state = sa_inspect(product)
        if "images" not in state.unloaded:
            images = [img.url for img in (product.images or [])]
    except Exception:
        pass
    colors = _normalize_colors(getattr(product, "colors", None))
    return {
        "id": str(product.id),
        "slug": product.slug,
        "name": product.name,
        "colors": colors,
        "image": images[0] if images else None,
        "price": product.price,
        "mrp": product.mrp,
    }


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
        "metafields": product.metafields or {},
        "colors": _normalize_colors(getattr(product, "colors", None)),
        "color_group_id": getattr(product, "color_group_id", None),
        "color_siblings": [],
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }
    cat_rel = _loaded("category_rel")
    if cat_rel is not None:
        data["category_slug"] = getattr(cat_rel, "slug", None)

    categories_m2m = _loaded("categories_m2m")
    if categories_m2m is not None:
        data["categories"] = [
            {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
            }
            for cat in categories_m2m
        ]
        data["category_ids"] = [cat.id for cat in categories_m2m]
    else:
        data["categories"] = []
        data["category_ids"] = (
            [product.category_id] if product.category_id else []
        )

    if include_relations:
        images = _loaded("images")
        data["images"] = [
            img.url
            for img in sorted(
                images or [],
                key=lambda i: (getattr(i, "position", 0) or 0, getattr(i, "id", 0) or 0),
            )
        ]
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
                        "hex": getattr(o, "hex", None),
                        "colors": _normalize_colors(
                            getattr(o, "colors", None)
                            or (
                                [{"name": o.name, "hex": o.hex}]
                                if getattr(o, "hex", None)
                                else []
                            )
                        ),
                        "image_url": getattr(o, "image_url", None),
                        "images": (
                            list(getattr(o, "images", None) or [])
                            or (
                                [o.image_url]
                                if getattr(o, "image_url", None)
                                else []
                            )
                        ),
                    }
                    for o in (v.options or [])
                ],
            }
            for v in (variants or [])
        ]
    return data


def format_variant_info_label(variant_info) -> str:
    """Build a short label from order line variant_info for display / shipping."""
    if not isinstance(variant_info, dict) or not variant_info:
        return ""
    if variant_info.get("label"):
        return str(variant_info["label"]).strip()
    sels = variant_info.get("selections")
    if isinstance(sels, list) and sels:
        labeled = []
        for s in sels:
            if not isinstance(s, dict):
                continue
            v, o = s.get("variant"), s.get("option")
            if v and o:
                labeled.append(f"{v}: {o}")
            elif o:
                labeled.append(str(o))
            elif v:
                labeled.append(str(v))
        if labeled:
            return " · ".join(labeled)
    variant = variant_info.get("variant")
    option = variant_info.get("option")
    return " · ".join(p for p in (variant, option) if p)


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
    customer_name = None
    customer_phone = None

    # Prefer linked order customer details
    try:
        insp = sa_inspect(payment)
        if "order" not in insp.unloaded and payment.order is not None:
            customer_name = payment.order.customer_name
            customer_phone = payment.order.customer_phone
    except Exception:
        pass

    # Fall back to checkout snapshot (pre-order / unpaid rows)
    if not customer_name or not customer_phone:
        snap = getattr(payment, "checkout_snapshot", None) or {}
        cust = snap.get("customer") if isinstance(snap, dict) else None
        if isinstance(cust, dict):
            customer_name = customer_name or cust.get("name")
            customer_phone = (
                customer_phone
                or cust.get("phone")
                or cust.get("mobile")
            )

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
        "customer": {
            "name": customer_name or None,
            "phone": customer_phone or None,
        },
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": (
            payment.updated_at.isoformat()
            if getattr(payment, "updated_at", None)
            else None
        ),
    }


def serialize_admin(admin) -> dict:
    from app.config import settings

    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.name,
        # Locked brand settings (env) — always surface these for Admin → Settings
        "phone": (settings.ADMIN_NOTIFY_PHONE or getattr(admin, "phone", None) or ""),
        "company_name": (settings.BRAND_NAME or getattr(admin, "company_name", None) or ""),
        "notify_email": (settings.ADMIN_NOTIFY_EMAIL or ""),
        "brand_name": (settings.BRAND_NAME or ""),
        "role": admin.role,
        "is_active": admin.is_active,
        "settings_locked": True,
    }


def serialize_user(user) -> dict:
    dob = getattr(user, "date_of_birth", None)
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "name": user.name,
        "date_of_birth": dob.isoformat() if dob else None,
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
