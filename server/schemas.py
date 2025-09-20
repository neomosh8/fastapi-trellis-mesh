from pydantic import BaseModel

class MeshResponse(BaseModel):
    glb_b64: str
