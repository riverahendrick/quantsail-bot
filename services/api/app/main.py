import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.private import router as private_router
from app.api.public import router as public_router
from app.api.ws import router as ws_router

app = FastAPI()

# CORS: allow localhost for dev, Vercel domains for production
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_origins = os.environ.get("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(private_router)
app.include_router(public_router)
app.include_router(ws_router)
