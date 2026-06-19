"""gpt-image-2 image generation + deterministic cache. Mirrors tts._openai (lazy requests,
OPENAI_API_KEY, graceful fallback). Generation is non-deterministic, so we cache each PNG by
a sha1 of (model,size,quality,prompt) -> re-renders are free and offline."""
import base64, hashlib, os

API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-2"
# rough per-image USD by quality at landscape — for the confirm step, NOT a list price.
_COST = {"low": 0.01, "medium": 0.04, "high": 0.17}

def _cache_key(prompt, model, size, quality):
    return hashlib.sha1(f"{model}|{size}|{quality}|{prompt}".encode("utf-8")).hexdigest()[:16]

def _cache_path(out_dir, prompt, model, size, quality):
    return os.path.join(out_dir, ".assets", _cache_key(prompt, model, size, quality) + ".png")

def cost_estimate(n, quality="medium", size="1536x1024"):
    return round(n * _COST.get(quality, 0.04), 3)

def generate(prompt, out_path, key, size="1536x1024", quality="medium", model=DEFAULT_MODEL):
    """Generate ONE image via gpt-image-2 and write a PNG to out_path.
    Raises RuntimeError if no key; raises on HTTP error (caller catches for fallback)."""
    if not key:
        raise RuntimeError("no OPENAI_API_KEY")
    import requests
    r = requests.post(API_URL,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "prompt": prompt, "size": size,
                            "quality": quality, "n": 1},
                      timeout=180)
    r.raise_for_status()
    b64 = r.json()["data"][0]["b64_json"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
