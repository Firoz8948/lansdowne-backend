from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .utils import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    # Prefer Authorization header, fall back to HttpOnly cookie
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token: str = Depends(_extract_token)) -> dict:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {
        "id": payload["sub"],
        "email": payload.get("email"),
        "phone": payload.get("phone"),
        "role": payload.get("role", "customer"),
    }


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict | None:
    """Returns user if token is valid, else None."""
    try:
        token = await _extract_token(request, credentials)
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        return {
            "id": payload["sub"],
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "role": payload.get("role", "customer"),
        }
    except HTTPException:
        return None


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
