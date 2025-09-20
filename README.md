Here’s a clean **final README** you can drop into your repo. It documents project structure, environment variables, paths, and usage.

---

# Trellis Mesh FastAPI

FastAPI microservice for generating 3D meshes (GLB) from images using the **local Trellis repo**.
The Trellis pipeline is loaded once at startup and kept in GPU memory for low latency inference.

---

## 📂 Project Structure

```
fastapi-trellis-mesh/
├── README.md
├── requirements.txt
├── server/                   # FastAPI service code
│   ├── __init__.py
│   ├── main.py               # FastAPI app, lifespan startup/shutdown
│   ├── api.py                # Endpoints
│   ├── model_manager.py      # Loads and manages Trellis pipeline
│   ├── schemas.py            # Pydantic models (optional)
│   └── utils.py              # Helpers (optional)
```

> Note: The package was renamed from `app` → `server` to avoid collisions with `app.py` inside Trellis repo.

---

## ⚙️ Required Environment Variables

These must be set before running the API:

```bash
# Required Trellis backend configs
export ATTN_BACKEND=xformers      # Alternatives: flash-attn, xformers
export SPCONV_ALGO=native         # Alternatives: auto, implicit_gemm, native

# Path to your local Trellis repo (default already matches server path)
export TRELLIS_SRC=/tmp/TRELLIS/TRELLIS
```

Optional for PyTorch compilation warnings:

```bash
export TORCH_CUDA_ARCH_LIST="8.0"   # or match your GPU compute capability
```

---

## 📦 Dependencies

Install only the lightweight API dependencies:

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
fastapi
uvicorn[standard]
python-multipart
Pillow
trimesh
```

---

## 🖥️ Linking Local Trellis Repo

The API does **not** use PyPI’s broken `trellis` package.
Instead, it loads your local Trellis code:

```bash
# Make Trellis repo importable by the API
# (do NOT edit Trellis repo itself)
export TRELLIS_SRC=/tmp/TRELLIS/TRELLIS
```

The `server/model_manager.py` includes a shim:

```python
TRELLIS_SRC = os.environ.get("TRELLIS_SRC", "/tmp/TRELLIS/TRELLIS")
if TRELLIS_SRC not in sys.path:
    sys.path.append(TRELLIS_SRC)
```

This ensures imports like:

```python
from trellis.pipelines import TrellisImageTo3DPipeline
```

work correctly without polluting global `PYTHONPATH`.

---

## 🚀 Running the API

From inside the repo folder:

```bash
unset PYTHONPATH   # avoid collision with /tmp/TRELLIS/TRELLIS/app.py

uvicorn server.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1
```

**Why 1 worker?** Each worker loads the model into GPU memory. Multiple workers duplicate VRAM usage. For a single GPU, use `--workers 1`.

---

## 🧪 Endpoints

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Generate Mesh (download as file)

```bash
curl -X POST "http://localhost:8000/generate_mesh_file?seed=1" \
  -F "file=@/tmp/TRELLIS/TRELLIS/assets/example_image/T.png" \
  -o sample.glb
```

### Generate Mesh (base64 JSON)

```bash
curl -X POST "http://localhost:8000/generate_mesh_b64?seed=1" \
  -F "file=@/tmp/TRELLIS/TRELLIS/assets/example_image/T.png" \
  | jq -r .glb_b64 | base64 -d > sample.glb
```

---

## 📝 Notes

* **Startup**: The Trellis pipeline is loaded once in FastAPI’s `lifespan` startup hook.
* **Shutdown**: VRAM is cleared with `torch.cuda.empty_cache()` when the app exits.
* **Export Fix**: We explicitly call `glb.export(file_type="glb")` so trimesh writes valid GLB bytes.
* **Local only**: This repo is API glue. Trellis itself stays at `/tmp/TRELLIS/TRELLIS`.

---

👉 Next steps: if you want to run this in Docker, I can prepare a GPU-ready `Dockerfile` using `nvidia/cuda:12.1-runtime-ubuntu22.04`.

Do you also want me to include a **docker-compose.yaml** so you can run with GPUs easily on the server?
