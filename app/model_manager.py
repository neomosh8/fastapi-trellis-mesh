import io
import asyncio
from typing import Optional
from PIL import Image
import torch

# Import from your local Trellis package that lives on the server
# PYTHONPATH and editable install will make this import work there
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import postprocessing_utils


class ModelManager:
    def __init__(self):
        self.pipe: Optional[TrellisImageTo3DPipeline] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def load(self):
        # Load once
        if self.pipe is None:
            # Optional: do this in a thread to avoid blocking event loop
            def _load():
                p = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
                if self.device == "cuda":
                    p.cuda()
                return p

            self.pipe = await asyncio.get_event_loop().run_in_executor(None, _load)
            print("Trellis pipeline loaded")

    async def unload(self):
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            torch.cuda.empty_cache()
            print("Trellis pipeline unloaded")

    def generate_glb_bytes(
        self,
        image: Image.Image,
        seed: int = 1,
        simplify: float = 0.95,
        texture_size: int = 1024,
    ) -> bytes:
        if self.pipe is None:
            raise RuntimeError("Pipeline not loaded")

        outputs = self.pipe.run(image, seed=seed)
        glb = postprocessing_utils.to_glb(
            outputs["gaussian"][0],
            outputs["mesh"][0],
            simplify=simplify,
            texture_size=texture_size,
        )
        buf = io.BytesIO()
        glb.export(buf)
        buf.seek(0)
        return buf.read()


# a simple singleton used by the app
manager = ModelManager()
