from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    role: Role
    api_key: str


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    status: TaskStatus = TaskStatus.OPEN
    owner_id: UUID
    assignee_id: UUID | None = None
