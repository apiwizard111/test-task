from uuid import UUID

from app.models import Role, Task, User

SEED_ADMIN = User(
    name="Ada Admin",
    role=Role.ADMIN,
    api_key="nexus-admin-key",
)
SEED_MEMBER = User(
    name="Lin Member",
    role=Role.MEMBER,
    api_key="nexus-member-key",
)

USERS: dict[UUID, User] = {
    SEED_ADMIN.id: SEED_ADMIN,
    SEED_MEMBER.id: SEED_MEMBER,
}
USER_BY_KEY: dict[str, User] = {
    SEED_ADMIN.api_key: SEED_ADMIN,
    SEED_MEMBER.api_key: SEED_MEMBER,
}
TASKS: dict[UUID, Task] = {}
