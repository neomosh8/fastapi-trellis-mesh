# server/api.py
import io
import base64
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image
from .model_manager import manager

router = APIRouter()

@router.post("/generate_mesh_b64")
async def generate_mesh_b64(file: UploadFile = File(...), seed: int = 1):
    try:
        data = await file.read()
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid image")
    glb_bytes = manager.generate_glb_bytes(image, seed=seed)
    return {"glb_b64": base64.b64encode(glb_bytes).decode("utf-8")}

@router.post("/generate_mesh_file")
async def generate_mesh_file(file: UploadFile = File(...), seed: int = 1):
    try:
        data = await file.read()
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid image")
    glb_bytes = manager.generate_glb_bytes(image, seed=seed)
    return StreamingResponse(
        io.BytesIO(glb_bytes),
        media_type="model/gltf-binary",
        headers={"Content-Disposition": 'attachment; filename="output.glb"'},
    )

