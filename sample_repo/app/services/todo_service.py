from uuid import UUID

from fastapi import HTTPException

from app.models import Role, Task, TaskStatus, User
from app.store import TASKS, USERS


class TaskService:
    def list_visible(self, actor: User) -> list[Task]:
        if actor.role is Role.ADMIN:
            return list(TASKS.values())
        return [task for task in TASKS.values() if task.owner_id == actor.id or task.assignee_id == actor.id]

    def create(self, actor: User, title: str, description: str) -> Task:
        task = Task(title=title, description=description, owner_id=actor.id, assignee_id=actor.id)
        TASKS[task.id] = task
        return task

    def update(self, actor: User, task_id: UUID, status: TaskStatus | None, title: str | None) -> Task:
        task = self._get(task_id)
        self._assert_can_mutate(actor, task)
        if status is not None:
            task.status = status
        if title is not None:
            task.title = title
        TASKS[task.id] = task
        return task

    def assign(self, actor: User, task_id: UUID, assignee_id: UUID) -> Task:
        if actor.role is not Role.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins can reassign tasks")
        task = self._get(task_id)
        if assignee_id not in USERS:
            raise HTTPException(status_code=404, detail="Assignee not found")
        task.assignee_id = assignee_id
        TASKS[task.id] = task
        return task

    def _get(self, task_id: UUID) -> Task:
        task = TASKS.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    def _assert_can_mutate(self, actor: User, task: Task) -> None:
        if actor.role is Role.ADMIN:
            return
        if actor.id not in {task.owner_id, task.assignee_id}:
            raise HTTPException(status_code=403, detail="Cannot mutate another member's task")
