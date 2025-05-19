import os

from dotenv import load_dotenv, find_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.routers import service, sockets, task, users

load_dotenv(find_dotenv())

app = FastAPI()

cors_origins = os.getenv("CORS_ORIGINS", "")
origins = [
    '*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)


app.include_router(service, prefix="/service")
app.include_router(sockets, prefix="/ws")
app.include_router(task, prefix="/tasks")
app.include_router(users, prefix="/users")