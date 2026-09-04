from typing import Annotated

from fastapi import Depends

from app.auth import authenticate, require_admin
from app.models import User

CurrentUser = Annotated[User, Depends(authenticate)]


def admin_user(user: CurrentUser) -> User:
    return require_admin(user)


AdminUser = Annotated[User, Depends(admin_user)]
