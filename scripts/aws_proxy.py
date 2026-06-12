import os
import httpx
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel

app = FastAPI(title="EXACT 2026 AWS Intermediary Proxy")

# Path to persistently store the current RunPod target URL
TARGET_FILE = "/tmp/target_runpod_url.txt"
DEFAULT_SECRET = ""

# Load secret token from environment or use default
SECRET_TOKEN = os.getenv("PROXY_SECRET_TOKEN", DEFAULT_SECRET)

class RegisterRequest(BaseModel):
    url: str
    secret: str

def get_target_url() -> str:
    """Read the registered RunPod URL from disk."""
    if os.path.exists(TARGET_FILE):
        try:
            with open(TARGET_FILE, "r") as f:
                url = f.read().strip()
                if url:
                    return url
        except Exception:
            pass
    return ""

def set_target_url(url: str):
    """Write the registered RunPod URL to disk."""
    with open(TARGET_FILE, "w") as f:
        f.write(url.strip())

@app.post("/register_pod")
async def register_pod(payload: RegisterRequest):
    """
    Endpoint for the RunPod instance to register its dynamic public URL.
    Secured by a pre-shared secret token.
    """
    if payload.secret != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")
    
    target_url = payload.url.rstrip("/")
    set_target_url(target_url)
    return {"status": "registered", "target_url": target_url}

@app.get("/health")
async def health():
    """Health check endpoint showing proxy status and target."""
    target = get_target_url()
    return {
        "status": "ok",
        "proxy": "aws-intermediary",
        "registered_target": target or "none"
    }

@app.post("/predict")
async def proxy_predict(payload: dict = Body(...)):
    """Forward predict calls from BTC to the registered RunPod instance."""
    target = get_target_url()
    if not target:
        raise HTTPException(status_code=503, detail="No RunPod instance is currently registered")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = client.build_request("POST", f"{target}/predict", json=payload)
            # Send and stream the response back
            res = await client.send(response)
            return res.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to forward request to RunPod: {exc}")

@app.get("/v1/models")
async def proxy_models():
    """Forward model verification requests from BTC to the registered RunPod instance."""
    target = get_target_url()
    if not target:
        raise HTTPException(status_code=503, detail="No RunPod instance is currently registered")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(f"{target}/v1/models")
            return res.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to verify models on RunPod: {exc}")
