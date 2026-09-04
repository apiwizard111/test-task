# Nexus Tasks

Internal task tracker for a small product team. HTTP API only.

## Auth

Every request except `GET /health` requires header `X-API-Key`.
Keys are issued per user. Roles: `admin` and `member`.

Admins can create users and reassign any task. Members can create and update
their own tasks.

## Endpoints

| Method | Path | Who |
| --- | --- | --- |
| GET | /health | anyone |
| POST | /users | admin |
| GET | /users/me | authenticated |
| GET | /tasks | authenticated |
| POST | /tasks | authenticated |
| PATCH | /tasks/{id} | owner or admin |
| POST | /tasks/{id}/assign | admin |

## Dependencies

Python 3.12, FastAPI, Pydantic v2. No database — tasks live in process memory.
This is a demo service, not production.
