from fastapi import FastAPI

from app.routes.todos import router as tasks_router
from app.routes.users import router as users_router

app = FastAPI(title="Nexus Tasks", version="0.4.2")
app.include_router(users_router)
app.include_router(tasks_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
