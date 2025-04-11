from fastapi import FastAPI
from app.api.github import router

app = FastAPI()

app.include_router(router)