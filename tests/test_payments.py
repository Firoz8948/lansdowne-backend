import hashlib
import hmac

from app.config import settings
from app.payments.payu import request_hash, response_hash, verify_response_hash
from app.payments.service import _verify_signature


def test_verify_signature_valid(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret")
    order_id = "order_123"
    payment_id = "pay_456"
    message = f"{order_id}|{payment_id}".encode()
    signature = hmac.new(b"test_secret", message, hashlib.sha256).hexdigest()
    assert _verify_signature(order_id, payment_id, signature) is True


def test_verify_signature_invalid(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret")
    assert _verify_signature("order_123", "pay_456", "bad_signature") is False


def test_payu_request_hash_stable():
    h = request_hash(
        key="key",
        txnid="txn1",
        amount="10.00",
        productinfo="Test",
        firstname="Ram",
        email="a@b.com",
        salt="salt",
        udf1="1",
    )
    raw = "key|txn1|10.00|Test|Ram|a@b.com|1||||||||||salt"
    assert h == hashlib.sha512(raw.encode()).hexdigest().lower()


def test_payu_response_hash_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "PAYU_KEY", "key")
    monkeypatch.setattr(settings, "PAYU_SALT", "salt")
    params = {
        "status": "success",
        "email": "a@b.com",
        "firstname": "Ram",
        "productinfo": "Test",
        "amount": "10.00",
        "txnid": "txn1",
        "key": "key",
        "udf1": "1",
        "udf2": "",
        "udf3": "",
        "udf4": "",
        "udf5": "",
    }
    params["hash"] = response_hash(params, salt="salt")
    assert verify_response_hash(params) is True
    params["hash"] = "deadbeef"
    assert verify_response_hash(params) is False
