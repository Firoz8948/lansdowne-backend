from pydantic import BaseModel


class CreateShipmentRequest(BaseModel):
    order_id: str


class RateRequest(BaseModel):
    pickup_pincode: str
    delivery_pincode: str
    weight: float = 0.5
    cod: bool = False


class ShipmentResponse(BaseModel):
    id: str
    order_id: str
    shiprocket_order_id: str | None = None
    awb_code: str | None = None
    courier_name: str | None = None
    status: str
    tracking_url: str | None = None
