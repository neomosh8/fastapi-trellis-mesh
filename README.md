# Trellis Mesh FastAPI

GPU model is loaded once at startup using FastAPI lifespan. One worker keeps it in memory for low latency. 
On the server you will point PYTHONPATH and install your local Trellis repo in editable mode.

Docs references:
- Lifespan startup and shutdown: https://fastapi.tiangolo.com/advanced/events/
- UploadFile for file uploads: https://fastapi.tiangolo.com/tutorial/request-files/
- Uvicorn workers guidance: https://fastapi.tiangolo.com/deployment/server-workers/

## Local dev on laptop

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# You can run "uvicorn app.main:app --reload" but generation needs GPU and Trellis repo.
# Use the server for actual inference.

## Deploy to server

# on server, keep using your working conda env
conda activate trellis

# clone this repo into /tmp/TRELLIS/service
cd /tmp/TRELLIS
mkdir -p service
cd service
git clone <YOUR_REPO_URL> .
pip install -r requirements.txt

# make your local Trellis code importable
pip install -e /tmp/TRELLIS/TRELLIS   # editable install of the local trellis package

# set the backends you already validated
export ATTN_BACKEND=xformers
export SPCONV_ALGO=native

# make sure Python can see your local package path
export PYTHONPATH=/tmp/TRELLIS/TRELLIS:$PYTHONPATH

# run with a single worker so the model is loaded once into VRAM
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

## Test

curl -X POST "http://localhost:8000/generate_mesh_file?seed=1" \
  -F "file=@/tmp/TRELLIS/TRELLIS/assets/example_image/T.png" \
  -o sample.glb

# or base64 JSON variant
curl -X POST "http://localhost:8000/generate_mesh_b64?seed=1" \
  -F "file=@/tmp/TRELLIS/TRELLIS/assets/example_image/T.png" \
  | jq -r .glb_b64 | base64 -d > sample.glb
