import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.routers import service, sockets, task

app = FastAPI()

cors_origins = os.getenv("CORS_ORIGINS", "")
origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(service, prefix="/service")
app.include_router(sockets, prefix="/ws")
app.include_router(task, prefix="/tasks")