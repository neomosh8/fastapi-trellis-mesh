import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Make sure these are set before importing trellis anywhere
os.environ.setdefault("ATTN_BACKEND", "xformers")
os.environ.setdefault("SPCONV_ALGO", "native")

from .model_manager import manager  # singleton manager
from .api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once at startup, keep in memory
    await manager.load()
    try:
        yield
    finally:
        await manager.unload()


app = FastAPI(title="Trellis Mesh API", lifespan=lifespan)
app.include_router(api_router)

# Basic health endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}
