# server/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

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

DOC_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Trellis Mesh Playground</title>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; padding: 0; background: #0f0f0f; color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    header { padding: 1.5rem 2rem; }
    main { max-width: 960px; margin: 0 auto; padding: 0 2rem 2rem; }
    form { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1rem; }
    label { font-weight: 600; }
    textarea, input { background: #1e1e1e; border: 1px solid #333; color: inherit; border-radius: 6px; padding: 0.6rem; width: 100%; box-sizing: border-box; }
    textarea { resize: vertical; }
    button { align-self: flex-start; background: #4f46e5; border: none; color: #fff; padding: 0.6rem 1.2rem; border-radius: 6px; font-weight: 600; cursor: pointer; transition: background 0.2s ease; }
    button:hover { background: #4338ca; }
    button:disabled { opacity: 0.6; cursor: wait; }
    #status { min-height: 1.5rem; }
    #download-link { display: none; margin-left: 1rem; color: #38bdf8; text-decoration: none; }
    #download-link:hover { text-decoration: underline; }
    #viewer { height: 520px; border: 1px solid #222; border-radius: 10px; overflow: hidden; background: #111; }
    canvas { display: block; }
    @media (max-width: 640px) { main { padding: 0 1rem 2rem; } }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
        "three/examples/jsm/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
      }
    }
  </script>
</head>
<body>
  <header>
    <h1>Trellis Mesh Playground</h1>
    <p>Enter a text prompt, generate a mesh, download the GLB, and preview it inline.</p>
  </header>
  <main>
    <form id="prompt-form">
      <div>
        <label for="prompt-input">Prompt</label>
        <textarea id="prompt-input" rows="3" placeholder="e.g. a weathered wooden treasure chest with brass accents" required></textarea>
      </div>
      <div>
        <label for="seed-input">Seed (optional)</label>
        <input id="seed-input" type="number" placeholder="1" />
      </div>
      <div>
        <button id="generate-btn" type="submit">Generate Mesh</button>
        <a id="download-link" download="trellis_mesh.glb">Download GLB</a>
      </div>
    </form>
    <p id="status"></p>
    <div id="viewer"></div>
  </main>
  <script type="module">
    import * as THREE from "three";
    import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
    import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

    const form = document.getElementById("prompt-form");
    const promptInput = document.getElementById("prompt-input");
    const seedInput = document.getElementById("seed-input");
    const statusEl = document.getElementById("status");
    const generateBtn = document.getElementById("generate-btn");
    const downloadLink = document.getElementById("download-link");
    const viewerEl = document.getElementById("viewer");

    let renderer;
    let scene;
    let camera;
    let controls;
    const loader = new GLTFLoader();
    const subjectGroup = new THREE.Group();
    let currentDownloadUrl = null;

    initScene();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const prompt = promptInput.value.trim();
      if (!prompt) {
        statusEl.textContent = "Please enter a prompt.";
        return;
      }

      const seedValue = seedInput.value.trim();
      const payload = { prompt: prompt };
      if (seedValue !== "") {
        const parsedSeed = Number(seedValue);
        if (!Number.isNaN(parsedSeed)) {
          payload.seed = parsedSeed;
        }
      }

      statusEl.textContent = "Generating mesh...";
      generateBtn.disabled = true;
      downloadLink.style.display = "none";

      try {
        const response = await fetch("/generate_mesh_from_text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || "Request failed");
        }

        const blob = await response.blob();
        await loadModelFromBlob(blob);
        statusEl.textContent = "Mesh ready. Use the viewer or download the GLB.";
      } catch (error) {
        console.error(error);
        statusEl.textContent = "Error: " + (error.message || error);
      } finally {
        generateBtn.disabled = false;
      }
    });

    async function loadModelFromBlob(blob) {
      if (currentDownloadUrl) {
        URL.revokeObjectURL(currentDownloadUrl);
        currentDownloadUrl = null;
      }

      const arrayBuffer = await blob.arrayBuffer();
      await new Promise((resolve, reject) => {
        loader.parse(
          arrayBuffer,
          "",
          (gltf) => {
            while (subjectGroup.children.length) {
              subjectGroup.remove(subjectGroup.children[0]);
            }
            subjectGroup.add(gltf.scene);
            fitCameraToObject(gltf.scene);
            resolve();
          },
          (error) => {
            reject(error);
          }
        );
      });

      currentDownloadUrl = URL.createObjectURL(blob);
      downloadLink.href = currentDownloadUrl;
      downloadLink.style.display = "inline-block";
    }

    function initScene() {
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x111111);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.setSize(viewerEl.clientWidth, viewerEl.clientHeight);
      viewerEl.appendChild(renderer.domElement);

      camera = new THREE.PerspectiveCamera(45, viewerEl.clientWidth / viewerEl.clientHeight, 0.1, 1000);
      camera.position.set(4, 3, 4);

      const ambient = new THREE.AmbientLight(0xffffff, 0.5);
      scene.add(ambient);

      const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
      keyLight.position.set(5, 10, 5);
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0xffffff, 0.6);
      fillLight.position.set(-4, 6, -3);
      scene.add(fillLight);

      const rimLight = new THREE.DirectionalLight(0xffffff, 0.4);
      rimLight.position.set(0, 4, -8);
      scene.add(rimLight);

      const grid = new THREE.GridHelper(10, 20, 0x444444, 0x222222);
      grid.position.y = -1;
      scene.add(grid);

      scene.add(subjectGroup);

      controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.target.set(0, 0.5, 0);

      window.addEventListener("resize", handleResize);
      animate();
    }

    function handleResize() {
      if (!renderer) {
        return;
      }

      const width = viewerEl.clientWidth;
      const height = viewerEl.clientHeight;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    function fitCameraToObject(object) {
      const box = new THREE.Box3().setFromObject(object);
      if (box.isEmpty()) {
        return;
      }

      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      box.getSize(size);
      box.getCenter(center);

      const maxDim = Math.max(size.x, size.y, size.z);
      const fitDistance = maxDim * 1.8;
      const direction = new THREE.Vector3(1, 1, 1).normalize();

      camera.position.copy(center.clone().add(direction.multiplyScalar(fitDistance)));
      camera.near = fitDistance / 100;
      camera.far = fitDistance * 10;
      camera.updateProjectionMatrix();

      controls.target.copy(center);
      controls.update();
    }

    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
  </script>
</body>
</html>
"""

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/doc", response_class=HTMLResponse)
async def doc_page():
    return HTMLResponse(DOC_PAGE_HTML)
