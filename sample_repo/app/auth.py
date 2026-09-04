from fastapi import Header, HTTPException

from app.models import Role, User
from app.store import USER_BY_KEY

API_KEY_HEADER = "X-API-Key"


class AuthError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=401, detail=detail)


def authenticate(x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER)) -> User:
    if not x_api_key:
        raise AuthError("Missing X-API-Key header")
    user = USER_BY_KEY.get(x_api_key)
    if user is None:
        raise AuthError("Unknown API key")
    return user


def require_admin(user: User) -> User:
    if user.role is not Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
