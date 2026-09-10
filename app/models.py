from datetime import date, datetime
from typing import Optional
import enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(str, enum.Enum):
    cod = "cod"
    razorpay = "razorpay"
    payu = "payu"


class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Admin")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    address_line1: Mapped[Optional[str]] = mapped_column(String(500))
    address_line2: Mapped[Optional[str]] = mapped_column(String(500))
    address_landmark: Mapped[Optional[str]] = mapped_column(String(255))
    address_city: Mapped[Optional[str]] = mapped_column(String(100))
    address_state: Mapped[Optional[str]] = mapped_column(String(100))
    address_pincode: Mapped[Optional[str]] = mapped_column(String(10))
    role: Mapped[str] = mapped_column(String(50), default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cart: Mapped[Optional["Cart"]] = relationship(
        "Cart", back_populates="user", uselist=False
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    seo_title: Mapped[Optional[str]] = mapped_column(String(200))
    seo_description: Mapped[Optional[str]] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_reels: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="category_rel",
        foreign_keys="Product.category_id",
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mrp: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), default="grams")
    weight: Mapped[Optional[float]] = mapped_column(Float)
    length_cm: Mapped[Optional[float]] = mapped_column(Float)
    breadth_cm: Mapped[Optional[float]] = mapped_column(Float)
    height_cm: Mapped[Optional[float]] = mapped_column(Float)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    metafields: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    seo_title: Mapped[Optional[str]] = mapped_column(String(200))
    seo_description: Mapped[Optional[str]] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category_rel: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="products", foreign_keys=[category_id]
    )
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship("Product", back_populates="images")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    options: Mapped[list["ProductVariantOption"]] = relationship(
        "ProductVariantOption",
        back_populates="variant",
        cascade="all, delete-orphan",
    )


class ProductVariantOption(Base):
    __tablename__ = "product_variant_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mrp: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    weight: Mapped[Optional[float]] = mapped_column(Float)

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="options"
    )


class MetafieldDefinition(Base):
    __tablename__ = "metafield_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))

    address_line1: Mapped[str] = mapped_column(String(500), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(500))
    address_landmark: Mapped[Optional[str]] = mapped_column(String(255))
    address_city: Mapped[str] = mapped_column(String(100), nullable=False)
    address_state: Mapped[str] = mapped_column(String(100), nullable=False)
    address_pincode: Mapped[str] = mapped_column(String(10), nullable=False)

    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    shipping_charge: Mapped[float] = mapped_column(Float, default=0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0)
    promo_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=False)

    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), default="pending")
    order_status: Mapped[str] = mapped_column(String(50), default="pending")

    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(255))
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(255))

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payment: Mapped[Optional["Payment"]] = relationship(
        "Payment", back_populates="order", uselist=False
    )
    shipment: Mapped[Optional["Shipment"]] = relationship(
        "Shipment", back_populates="order", uselist=False
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(300))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    image: Mapped[Optional[str]] = mapped_column(String(500))
    variant_info: Mapped[Optional[dict]] = mapped_column(JSON)

    order: Mapped["Order"] = relationship("Order", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_db_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    razorpay_refund_id: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500))
    checkout_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="payment")


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(300))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    image: Mapped[Optional[str]] = mapped_column(String(500))
    variant_info: Mapped[Optional[dict]] = mapped_column(JSON)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_db_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    order_id: Mapped[str] = mapped_column(String(50), nullable=False)
    awb_code: Mapped[Optional[str]] = mapped_column(String(100))
    courier_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[str]] = mapped_column(String(100))
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500))
    shiprocket_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    shiprocket_shipment_id: Mapped[Optional[str]] = mapped_column(String(100))
    shipmozo_reference_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped["Order"] = relationship("Order", back_populates="shipment")


class OTP(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    otp: Mapped[str] = mapped_column(String(10), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class VideoProduct(Base):
    __tablename__ = "video_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    mrp: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), default="piece")
    video_url: Mapped[Optional[str]] = mapped_column(String(500))
    images: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    weight: Mapped[Optional[float]] = mapped_column(Float)
    length_cm: Mapped[Optional[float]] = mapped_column(Float)
    breadth_cm: Mapped[Optional[float]] = mapped_column(Float)
    height_cm: Mapped[Optional[float]] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BannerSlide(Base):
    __tablename__ = "banner_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    title_highlight: Mapped[Optional[str]] = mapped_column(String(255))
    subtitle: Mapped[Optional[str]] = mapped_column(Text)
    link_url: Mapped[Optional[str]] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    percent_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    # all = anyone; new_users = first-time buyers only (by phone / user_id)
    audience: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShippingZone(Base):
    __tablename__ = "shipping_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_all_india: Mapped[bool] = mapped_column(Boolean, default=False)
    states: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    rate: Mapped[float] = mapped_column(Float, nullable=False, default=49)
    prepaid_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cod_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    free_shipping_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

