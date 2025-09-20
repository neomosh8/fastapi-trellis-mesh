import asyncio
import os
import sys
from typing import Optional

from PIL import Image
import torch

# Point to your local TRELLIS source tree
TRELLIS_SRC = os.environ.get("TRELLIS_SRC", "/tmp/TRELLIS/TRELLIS")
if TRELLIS_SRC not in sys.path:
    sys.path.append(TRELLIS_SRC)

# Import from your local Trellis package that lives on the server
# PYTHONPATH and editable install will make this import work there
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.pipelines import TrellisTextTo3DPipeline
from trellis.utils import postprocessing_utils


class ModelManager:
    def __init__(self):
        self.img_pipe: Optional[TrellisImageTo3DPipeline] = None
        self.txt_pipe: Optional[TrellisTextTo3DPipeline] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def load(self):
        if self.img_pipe is None or self.txt_pipe is None:
            loop = asyncio.get_event_loop()

            def _load_image():
                p = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
                if self.device == "cuda":
                    p.cuda()
                return p

            def _load_text():
                p = TrellisTextTo3DPipeline.from_pretrained("microsoft/TRELLIS-text-base")
                if self.device == "cuda":
                    p.cuda()
                return p

            img_fut = loop.run_in_executor(None, _load_image)
            txt_fut = loop.run_in_executor(None, _load_text)
            self.img_pipe, self.txt_pipe = await asyncio.gather(img_fut, txt_fut)
            print("Trellis pipelines loaded (image+text)")

    async def unload(self):
        self.img_pipe = None
        self.txt_pipe = None
        torch.cuda.empty_cache()
        print("Trellis pipelines unloaded")

    def _to_glb_bytes(self, outputs, simplify: float = 0.95, texture_size: int = 1024) -> bytes:
        glb = postprocessing_utils.to_glb(
            outputs["gaussian"][0],
            outputs["mesh"][0],
            simplify=simplify,
            texture_size=texture_size,
        )
        return glb.export(file_type="glb")

    def generate_glb_bytes(
        self,
        image: Image.Image,
        seed: int = 1,
        simplify: float = 0.95,
        texture_size: int = 1024,
    ) -> bytes:
        if self.img_pipe is None:
            raise RuntimeError("Image pipeline not loaded")

        outputs = self.img_pipe.run(image, seed=seed)
        return self._to_glb_bytes(outputs, simplify=simplify, texture_size=texture_size)

    def generate_glb_bytes_from_text(
        self,
        prompt: str,
        seed: int = 1,
        simplify: float = 0.95,
        texture_size: int = 1024,
    ) -> bytes:
        if self.txt_pipe is None:
            raise RuntimeError("Text pipeline not loaded")

        outputs = self.txt_pipe.run(prompt, seed=seed)
        return self._to_glb_bytes(outputs, simplify=simplify, texture_size=texture_size)


# a simple singleton used by the app
manager = ModelManager()
