# server/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

os.environ.setdefault("ATTN_BACKEND", "xformers")
os.environ.setdefault("SPCONV_ALGO", "native")

from .model_manager import manager
from .api import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.load()
    try:
        yield
    finally:
        await manager.unload()

app = FastAPI(title="Trellis Mesh API", lifespan=lifespan)
app.include_router(api_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
