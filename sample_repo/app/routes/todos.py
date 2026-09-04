from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import AdminUser, CurrentUser
from app.models import Task, TaskStatus
from app.services.todo_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])
_service = TaskService()


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    status: TaskStatus | None = None


class AssignTaskRequest(BaseModel):
    assignee_id: UUID


@router.get("", response_model=list[Task])
def list_tasks(user: CurrentUser) -> list[Task]:
    return _service.list_visible(user)


@router.post("", response_model=Task, status_code=201)
def create_task(payload: CreateTaskRequest, user: CurrentUser) -> Task:
    return _service.create(user, payload.title, payload.description)


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: UUID, payload: UpdateTaskRequest, user: CurrentUser) -> Task:
    return _service.update(user, task_id, payload.status, payload.title)


@router.post("/{task_id}/assign", response_model=Task)
def assign_task(task_id: UUID, payload: AssignTaskRequest, admin: AdminUser) -> Task:
    return _service.assign(admin, task_id, payload.assignee_id)
