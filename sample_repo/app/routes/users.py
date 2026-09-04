from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import AdminUser, CurrentUser
from app.models import Role, User
from app.store import USERS, USER_BY_KEY

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role: Role = Role.MEMBER
    api_key: str = Field(min_length=8, max_length=64)


@router.get("/me", response_model=User)
def me(user: CurrentUser) -> User:
    return user


@router.post("", response_model=User, status_code=201)
def create_user(payload: CreateUserRequest, _admin: AdminUser) -> User:
    user = User(name=payload.name, role=payload.role, api_key=payload.api_key)
    USERS[user.id] = user
    USER_BY_KEY[user.api_key] = user
    return user
