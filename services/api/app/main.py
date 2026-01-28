from fastapi import FastAPI

from app.api.private import router as private_router
from app.api.public import router as public_router
from app.api.ws import router as ws_router

app = FastAPI()
app.include_router(private_router)
app.include_router(public_router)
app.include_router(ws_router)
