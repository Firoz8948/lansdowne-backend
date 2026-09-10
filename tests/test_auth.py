from app.auth.utils import (
    create_access_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)


def test_generate_otp_length():
    otp = generate_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()


def test_password_hash_and_verify():
    hashed = hash_password("Secret@123")
    assert hashed != "Secret@123"
    assert verify_password("Secret@123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token({"sub": "abc", "role": "user"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "abc"
    assert payload["type"] == "access"


def test_decode_invalid_token():
    assert decode_token("not-a-real-token") is None
