from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.private import router as private_router
from app.api.public import router as public_router
from app.api.ws import router as ws_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(private_router)
app.include_router(public_router)
app.include_router(ws_router)
