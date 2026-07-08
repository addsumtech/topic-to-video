"""gpt-image-2 image generation + deterministic cache. Mirrors tts._openai (lazy requests,
OPENAI_API_KEY, graceful fallback). Generation is non-deterministic, so we cache each PNG by
a sha1 of (model,size,quality,prompt) -> re-renders are free and offline."""
import argparse, base64, hashlib, json, os, shutil, subprocess
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

def _codex_available():
    """True if the Codex CLI is on PATH (it generates images natively, no API key)."""
    return shutil.which("codex") is not None

def _generate_codex(prompt, out_path, size="1536x1024", quality="medium"):
    """Generate ONE image via the installed Codex CLI's native image-gen — NO API key.
    Raises RuntimeError if codex is missing or no valid image is produced (caller falls back)."""
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI not found")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    work = os.path.dirname(out_path)
    instr = (f"Generate a {size} cinematic image: {prompt}. "
             f"Use your image-generation tool (do NOT draw it with code or PIL). "
             f"Save the resulting PNG to {out_path}. Output nothing else.")
    subprocess.run([codex, "exec", "--skip-git-repo-check", "-s", "workspace-write", "-C", work, instr],
                   check=True, capture_output=True, timeout=600)
    if not os.path.exists(out_path):
        raise RuntimeError(f"codex produced no image at {out_path}")
    from PIL import Image
    Image.open(out_path).verify()             # raises if the file is not a valid image

def _read_key_file():
    try:
        return (open(os.path.expanduser("~/.openai_key")).read().strip() or None)
    except OSError:
        return None

def synthesize_soft_textures(out_dir, data, key, provider, size, quality, date=""):
    """Generate a SMALL reusable set (<=3) of on-topic soft background textures for the AI look
    (from meta.soft_texture_prompts) into meta.soft_textures — atmospheric b-roll the design-director
    rotates behind CONTENT pages at low opacity so they aren't flat. sha1-cached like the per-scene
    images (re-renders are free). No-ops with a note when the deck declares no soft_texture_prompts."""
    meta = data["meta"]
    prompts = [p for p in (meta.get("soft_texture_prompts") or []) if (p or "").strip()][:3]
    meta.setdefault("soft_textures", [])              # distinguish 'attempted, none' from 'not attempted' downstream
    if not prompts:
        print("[imagegen] AI look but no meta.soft_texture_prompts — content pages will be flat; "
              "have the design-director emit 2-3 on-topic texture prompts")
        return 0
    model = "codex" if provider == "codex" else DEFAULT_MODEL
    rels, made, cached, failed = [], 0, 0, 0
    for prompt in prompts:
        cp = _cache_path(out_dir, prompt, model, size, quality)
        rel = os.path.relpath(cp, out_dir)
        if os.path.exists(cp):
            rels.append(rel); cached += 1; continue
        try:
            if provider == "codex":
                _generate_codex(prompt, cp, size, quality)
            else:
                generate(prompt, cp, key, size, quality, DEFAULT_MODEL)
            with open(cp[:-4] + ".json", "w") as f:
                json.dump({"prompt": prompt, "provider": provider, "model": model, "size": size,
                           "quality": quality, "tag": "broll", "kind": "soft_texture", "date": date},
                          f, indent=2)
            rels.append(rel); made += 1
        except Exception as e:
            print(f"[imagegen] soft texture failed ({e}); skipping")
            failed += 1
    meta["soft_textures"] = rels
    print(f"[imagegen] soft textures: generated {made}, cache-hit {cached}, fallback {failed} "
          f"→ meta.soft_textures[{len(rels)}]")
    return made


def synthesize_images(out_dir, key=None, date=""):
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    meta = data["meta"]
    if meta.get("image_source") != "openai":
        return data                                    # free tier — nothing to generate
    provider = (meta.get("image_provider") or "auto").lower()
    if provider == "auto":
        provider = "codex" if _codex_available() else "openai"
    # Default the generated-image size from the deck aspect so a 9:16 deck gets
    # portrait imagery (1024x1536) instead of landscape; an explicit meta.image_size wins.
    _aspect_default = "1024x1536" if str(meta.get("aspect", "16:9")) == "9:16" else "1536x1024"
    size = meta.get("image_size", _aspect_default)
    quality = meta.get("image_quality", "medium")
    model = "codex" if provider == "codex" else DEFAULT_MODEL
    if provider != "codex":
        key = key or os.environ.get("OPENAI_API_KEY") or _read_key_file()
    pending = [s for s in data["slides"]
               if (s.get("image_prompt") or "").strip() and not s.get("image")]
    made = cached = failed = 0
    for s in pending:
        prompt = s["image_prompt"]
        cp = _cache_path(out_dir, prompt, model, size, quality)
        rel = os.path.relpath(cp, out_dir)
        if os.path.exists(cp):
            s["image"] = rel; cached += 1; continue
        try:
            if provider == "codex":
                _generate_codex(prompt, cp, size, quality)
            else:
                generate(prompt, cp, key, size, quality, DEFAULT_MODEL)
            with open(cp[:-4] + ".json", "w") as f:
                json.dump({"prompt": prompt, "provider": provider, "model": model, "size": size,
                           "quality": quality, "tag": s.get("image_tag", "broll"), "date": date},
                          f, indent=2)
            s["image"] = rel; made += 1
        except Exception as e:
            print(f"[imagegen] scene {s['index']} failed ({e}); leaving for free-tier fallback")
            failed += 1
    smade = synthesize_soft_textures(out_dir, data, key, provider, size, quality, date)
    sb.save(data, path)
    cost = "via Codex plan (no key)" if provider == "codex" else f"est ${cost_estimate(made + smade, quality, size)}"
    print(f"[imagegen] provider={provider}: generated {made}, cache-hit {cached}, fallback {failed}; {cost}")
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    synthesize_images(a.out_dir, a.key)

if __name__ == "__main__":
    main()
