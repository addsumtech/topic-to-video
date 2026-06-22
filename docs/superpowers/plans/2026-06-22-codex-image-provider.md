# Codex CLI Image-Gen Provider — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate AI images via the installed **Codex CLI** (native image-gen, no API key) when present, falling back to the OpenAI-key path otherwise — selected by `meta.image_provider` (auto, Codex-first).

**Architecture:** Add `_codex_available()` + `_generate_codex()` to `imagegen.py`; `synthesize_images` resolves a provider (auto → Codex if `codex` on PATH, else `openai`) and dispatches per-scene, keying the cache by `model="codex"` vs `"gpt-image-2"`. `storyboard.py` validates `meta.image_provider`. SKILL.md documents the auto-Codex-first behavior.

**Tech Stack:** Python 3 (stdlib `shutil`/`subprocess`), Pillow (validation), the external `codex` CLI, pytest. No new dependency.

## Global Constraints
- **Codex provider uses NO API key.** Command (verified): `codex exec --skip-git-repo-check -s workspace-write -C <dirname(out_path)> "<instruction naming out_path>"`, run with `capture_output=True`, `timeout=600`. After it returns, **validate** the image exists + opens (`PIL.Image.open(p).verify()`); raise `RuntimeError` otherwise so the caller falls back.
- **Auto, Codex-first:** `meta.image_provider ∈ {"auto"(default),"codex","openai"}`; `auto` → `"codex" if codex on PATH else "openai"`.
- **Cache distinguishes provider via `model`:** `model="codex"` for the Codex path, `DEFAULT_MODEL` ("gpt-image-2") for OpenAI — the existing `_cache_key` already hashes `model`, so NO signature change.
- `image_source == "openai"` stays the on/off gate for the AI-image tier.
- **Module-level `import shutil, subprocess`** (stdlib) so tests can monkeypatch `imagegen.shutil`/`imagegen.subprocess`. (`requests` stays lazy in `generate`.)
- Faithful unchanged (Codex images are `broll`/atmospheric). Tests fully mocked — NO real codex, NO network. Existing tests stay green.

---

### Task 1: Codex provider — `_codex_available` + `_generate_codex`

**Files:**
- Modify: `scripts/imagegen.py` (add module imports + the two functions)
- Test: `tests/test_imagegen.py`

**Interfaces (Produces):**
- `_codex_available() -> bool`
- `_generate_codex(prompt, out_path, size="1536x1024", quality="medium") -> None` (raises on missing codex / no valid image)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_imagegen.py`:
```python
def _valid_png(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (8, 8), (10, 20, 30)).save(path)

def test_codex_available(monkeypatch):
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: "/usr/bin/codex" if n == "codex" else None)
    assert imagegen._codex_available() is True
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: None)
    assert imagegen._codex_available() is False

def test_generate_codex_builds_command_and_validates(tmp_path, monkeypatch):
    out = str(tmp_path / ".assets" / "x.png")
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: "/usr/bin/codex")
    cap = {}
    def fake_run(cmd, **kw):
        cap["cmd"] = cmd; cap["kw"] = kw
        _valid_png(out)                       # simulate codex producing the image
    monkeypatch.setattr(imagegen.subprocess, "run", fake_run)
    imagegen._generate_codex("a generic rocket", out, "1536x1024", "medium")
    cmd = cap["cmd"]
    assert cmd[0] == "/usr/bin/codex" and cmd[1] == "exec"
    assert "--skip-git-repo-check" in cmd and "workspace-write" in cmd and "-C" in cmd
    assert out in cmd[-1] and "a generic rocket" in cmd[-1]
    assert all(("Bearer" not in str(c)) and ("sk-" not in str(c)) for c in cmd)   # no key anywhere
    assert cap["kw"].get("capture_output") is True and cap["kw"].get("timeout") == 600
    assert os.path.exists(out)

from PIL import UnidentifiedImageError  # noqa: E402
def test_generate_codex_raises_when_no_image(tmp_path, monkeypatch):
    monkeypatch.setattr(imagegen.shutil, "which", lambda n: "/usr/bin/codex")
    monkeypatch.setattr(imagegen.subprocess, "run", lambda cmd, **kw: None)   # writes nothing
    with pytest.raises(RuntimeError):
        imagegen._generate_codex("x", str(tmp_path / ".assets" / "y.png"))
```
(Ensure the test file has `from PIL import Image` and `import pytest` at the top — add if missing.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_imagegen.py -k codex -v`
Expected: FAIL (`module 'imagegen' has no attribute '_codex_available'` / `shutil`).

- [ ] **Step 3: Write the implementation**

In `scripts/imagegen.py`, add `shutil` and `subprocess` to the top-level imports (the file currently imports `argparse, base64, hashlib, json, os` and `storyboard as sb`):
```python
import argparse, base64, hashlib, json, os, shutil, subprocess
```
Add these two functions (e.g., after `generate`):
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_imagegen.py -k codex -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/imagegen.py tests/test_imagegen.py
git commit -m "feat(imagegen): Codex CLI provider — _codex_available + _generate_codex (no key)"
```

---

### Task 2: provider dispatch in `synthesize_images` + schema

**Files:**
- Modify: `scripts/imagegen.py` (`synthesize_images`; add `_read_key_file`)
- Modify: `scripts/storyboard.py` (`VALID_IMAGE_PROVIDERS` + `validate`)
- Test: `tests/test_imagegen.py`, `tests/test_storyboard.py`

**Interfaces:**
- Consumes: `_codex_available`, `_generate_codex` (Task 1); `generate`, `_cache_path`, `cost_estimate` (existing).
- Produces: `synthesize_images` routes per `meta.image_provider`; `meta.image_provider` validated against `VALID_IMAGE_PROVIDERS`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_imagegen.py`:
```python
def _board(tmp_path, provider="auto", prompt="a generic rocket"):
    out = tmp_path / "proj"; os.makedirs(out, exist_ok=True)
    d = sb.new_storyboard({"image_source": "openai", "image_provider": provider,
                           "image_quality": "medium", "image_size": "1536x1024"})
    s = sb.new_slide(1, None); s["image"] = None; s["image_prompt"] = prompt
    s["image_tag"] = "broll"; s["narration"] = "n"
    d["slides"] = [s]
    sb.save(d, os.path.join(out, "storyboard.json"))
    return str(out)

def test_synthesize_auto_prefers_codex_no_key(tmp_path, monkeypatch):
    out = _board(tmp_path, provider="auto")
    monkeypatch.setattr(imagegen, "_codex_available", lambda: True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    codex_calls = []; openai_calls = []
    monkeypatch.setattr(imagegen, "_generate_codex",
        lambda prompt, cp, size, quality: (codex_calls.append(cp), _valid_png(cp)))
    monkeypatch.setattr(imagegen, "generate", lambda *a, **k: openai_calls.append(a))
    d = imagegen.synthesize_images(out, key=None)
    assert len(codex_calls) == 1 and len(openai_calls) == 0     # codex used, no key
    img = d["slides"][0]["image"]
    assert img and "codex" in open(os.path.join(out, img[:-4] + ".json")).read()   # provider in manifest

def test_synthesize_auto_falls_to_openai_when_no_codex(tmp_path, monkeypatch):
    out = _board(tmp_path, provider="auto")
    monkeypatch.setattr(imagegen, "_codex_available", lambda: False)
    calls = []
    monkeypatch.setattr(imagegen, "generate",
        lambda prompt, cp, key, size, quality, model: (calls.append(model), _valid_png(cp)))
    imagegen.synthesize_images(out, key="sk-test")
    assert calls and calls[0] == imagegen.DEFAULT_MODEL          # openai path, gpt-image-2

def test_synthesize_codex_cache_path_distinct(tmp_path):
    # codex (model 'codex') and openai (DEFAULT_MODEL) hash to different cache files
    a = imagegen._cache_path(str(tmp_path), "p", "codex", "1536x1024", "medium")
    b = imagegen._cache_path(str(tmp_path), "p", imagegen.DEFAULT_MODEL, "1536x1024", "medium")
    assert a != b
```

Add to `tests/test_storyboard.py`:
```python
def test_validate_image_provider_enum():
    sb.validate({"meta": {"image_source": "openai", "image_provider": "codex"}, "slides": [sb.new_slide(1, "f.png")]})
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {"image_source": "openai", "image_provider": "banana"}, "slides": [sb.new_slide(1, "f.png")]})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_imagegen.py -k "synthesize_auto or cache_path_distinct" tests/test_storyboard.py -k image_provider -v`
Expected: FAIL (no provider routing; `image_provider` not validated).

- [ ] **Step 3: Write the implementation**

In `scripts/imagegen.py`, add a key-file helper (after `cost_estimate`):
```python
def _read_key_file():
    try:
        return (open(os.path.expanduser("~/.openai_key")).read().strip() or None)
    except OSError:
        return None
```
Replace the body of `synthesize_images` from the `key = ...` line through the final `return data` with:
```python
    provider = (meta.get("image_provider") or "auto").lower()
    if provider == "auto":
        provider = "codex" if _codex_available() else "openai"
    size = meta.get("image_size", "1536x1024")
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
    sb.save(data, path)
    cost = "via Codex plan (no key)" if provider == "codex" else f"est ${cost_estimate(made, quality, size)}"
    print(f"[imagegen] provider={provider}: generated {made}, cache-hit {cached}, fallback {failed}; {cost}")
    return data
```
(The `if meta.get("image_source") != "openai": return data` gate at the top of `synthesize_images` is UNCHANGED — keep it.)

In `scripts/storyboard.py`, add near the other VALID_* sets:
```python
VALID_IMAGE_PROVIDERS = {"auto", "codex", "openai"}
```
In `validate`, beside the existing `meta.image_source`/`image_quality` checks, add:
```python
    if "image_provider" in m and m["image_provider"] not in VALID_IMAGE_PROVIDERS:
        raise StoryboardError(f"meta.image_provider must be one of {VALID_IMAGE_PROVIDERS}")
```
(`m` is the `data["meta"]` already bound in `validate`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_imagegen.py tests/test_storyboard.py -v`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add scripts/imagegen.py scripts/storyboard.py tests/test_imagegen.py tests/test_storyboard.py
git commit -m "feat(imagegen): provider dispatch (auto codex-first) + image_provider schema + ~/.openai_key"
```

---

### Task 3: SKILL.md — Codex-first interview + guardrails

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Update the gpt-image interview clause**

In `SKILL.md` Workflow step 1 (the gpt-image / image-source clause), add after the key request:
```markdown
   **Image provider:** if the **`codex` CLI is installed**, generate via Codex's native
   image-generation (NO key — it uses your Codex plan; slower, ~minutes/image). Otherwise ask for
   the OpenAI key (`OPENAI_API_KEY` or `~/.openai_key`). If neither, fall back to the free
   programmatic / HTML tier. `meta.image_provider` is `auto` (default — Codex-first when installed),
   `codex`, or `openai` to force one.
```

- [ ] **Step 2: Guardrails + failure rows**

In `SKILL.md` `## Guardrails`, add:
```markdown
- **Image provider:** `imagegen.py` auto-detects the `codex` CLI and uses its native image-gen
  (no key, Codex-plan-billed, slower) when present; else the OpenAI key (`OPENAI_API_KEY` /
  `~/.openai_key`). `meta.image_provider` (`auto`/`codex`/`openai`) overrides. Codex and OpenAI
  images cache separately (keyed by provider).
```
In the `## When a step fails` table, add:
```markdown
| `imagegen.py`: Codex run fails / makes no image | `_generate_codex` raises → that scene falls back to the free tier; other cached scenes unaffected | Force `meta.image_provider:"openai"` + provide a key, or use the free programmatic/HTML tier |
| Image tier on but no codex AND no key | Each scene falls back to the free tier with a notice | Install `codex`, or set `OPENAI_API_KEY` / `~/.openai_key`, then re-run `imagegen.py` |
```

- [ ] **Step 3: Verify + full suite + commit**

Run:
```bash
grep -n "codex\|image_provider\|Codex" SKILL.md | head
python3 -m pytest -q
```
Expected: grep shows the additions; full suite PASSES.
```bash
git add SKILL.md
git commit -m "docs(skill): Codex-first image provider (no key when codex installed) + guardrails"
```

---

## Self-Review

**Spec coverage:** `_codex_available` + `_generate_codex` with the verified `codex exec` command + validation (Task 1) ✓; `synthesize_images` auto-codex-first dispatch + `model="codex"` cache distinction + `~/.openai_key` resolution + manifest `provider` (Task 2) ✓; `image_provider` schema validation (Task 2) ✓; SKILL.md interview + guardrails + failure rows (Task 3) ✓; faithful unchanged (no critic edit) ✓; no key on the codex path (Task 1 test asserts it) ✓; fully-mocked tests / no real codex (Tasks 1–2) ✓. Out-of-scope (exact Codex dimensions, streaming, parallelism) has no task.

**Placeholder scan:** none — every code/test step is complete and runnable; the `codex exec` argv and mock patterns are concrete.

**Type consistency:** `_generate_codex(prompt, out_path, size, quality)` is defined in Task 1 and called identically in Task 2's dispatch + tests. `_codex_available()` is monkeypatched and called consistently. `model` is `"codex"` vs `DEFAULT_MODEL` across the dispatch + the cache-path test. `meta.image_provider`/`VALID_IMAGE_PROVIDERS` names match across imagegen dispatch (Task 2), schema (Task 2), and SKILL.md (Task 3). `_cache_path(out_dir, prompt, model, size, quality)` signature is unchanged (provider rides in via `model`).
