"""gpt-image-2 image generation + deterministic cache. Mirrors tts._openai (lazy requests,
OPENAI_API_KEY, graceful fallback). Generation is non-deterministic, so we cache each PNG by
a sha1 of (model,size,quality,prompt) -> re-renders are free and offline."""
import argparse, base64, hashlib, json, os
import storyboard as sb

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

def synthesize_images(out_dir, key=None, date=""):
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    meta = data["meta"]
    if meta.get("image_source") != "openai":
        return data                                    # free tier — nothing to generate
    key = key or os.environ.get("OPENAI_API_KEY")
    size = meta.get("image_size", "1536x1024")
    quality = meta.get("image_quality", "medium")
    model = DEFAULT_MODEL
    pending = [s for s in data["slides"]
               if (s.get("image_prompt") or "").strip() and not s.get("image")]
    made = cached = failed = 0
    for s in pending:
        prompt = s["image_prompt"]
        cp = _cache_path(out_dir, prompt, model, size, quality)
        rel = os.path.relpath(cp, out_dir)
        if os.path.exists(cp):                          # cache hit — free, offline
            s["image"] = rel; cached += 1; continue
        try:
            generate(prompt, cp, key, size, quality, model)
            with open(cp[:-4] + ".json", "w") as f:     # manifest sidecar
                json.dump({"prompt": prompt, "model": model, "size": size, "quality": quality,
                           "tag": s.get("image_tag", "broll"), "date": date}, f, indent=2)
            s["image"] = rel; made += 1
        except Exception as e:
            print(f"[imagegen] scene {s['index']} failed ({e}); leaving for free-tier fallback")
            failed += 1
    sb.save(data, path)
    print(f"[imagegen] generated {made}, cache-hit {cached}, fallback {failed}; "
          f"est ${cost_estimate(made, quality, size)}")
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    synthesize_images(a.out_dir, a.key)

if __name__ == "__main__":
    main()
