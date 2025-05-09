from fastapi import FastAPI

from app.routers import service, sockets, task

app = FastAPI()

app.include_router(service, prefix="/service")
app.include_router(sockets, prefix="/ws")
app.include_router(task, prefix="/tasks")