# Design: Codex CLI image-generation provider (key-free, with API-key fallback)

**Date:** 2026-06-22
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal

The gpt-image tier (`imagegen.py`) always needs an `OPENAI_API_KEY`. But many users have the
**Codex CLI**, which generates images natively via its own OpenAI/ChatGPT plan auth — **no key
needed**. Make image generation **detect Codex and prefer it** when installed, falling back to the
API-key path otherwise. Same for the HTML-page gpt-image backdrops (they call the same code).

**Verified feasibility (this machine, codex-cli 0.141.0):**
`codex exec --skip-git-repo-check -s workspace-write -C <dir> "<prompt>; save the PNG to <abs
path>; use real image generation"` produced a real **1536×1024 PNG** via Codex's **native
image-generation tool** (`image_generation_call`/`image_generation_end` in the session log) — using
the Codex plan auth, **no `OPENAI_API_KEY`**. It is **slower** (~minutes/image, agent loop) and
chatty (run it with captured output). `codex exec` honored `workspace-write` without prompting.

## Decisions (from brainstorming)
- **Auto, Codex-first:** `meta.image_provider` ∈ {`"auto"` (default), `"codex"`, `"openai"`}.
  `auto` = Codex when `codex` is on PATH, else the API-key path. Explicit values force a provider.
- **Cache distinguishes provider via `model`:** pass `model="codex"` for the Codex path (the cache
  key already hashes `model`), so Codex and OpenAI images don't collide and re-renders stay free.
  No `_cache_key` signature change.
- **Size is best-effort for Codex** (it returns ~1536×1024); request the aspect in the prompt and
  let the renderer's cover-fit handle the rest.
- **Faithful, unchanged:** Codex images are `broll`/atmospheric; the prompt forbids logos/text/named
  vehicles; the critic (R1e/R2) still applies regardless of provider.

## Architecture

`meta.image_source == "openai"` stays the **on/off gate** for the AI-image tier. A new
`meta.image_provider` selects **how** to fulfill it — Codex vs the OpenAI key — resolved per-run.
`synthesize_images` dispatches to `_generate_codex` (no key) or the existing `generate` (key).

## Component 1 — Codex provider (`imagegen.py`, new)
- `_codex_available() -> bool` → `shutil.which("codex") is not None`.
- `_generate_codex(prompt, out_path, size="1536x1024", quality="medium") -> None`:
  - `os.makedirs(dirname(out_path))`; run, with **captured** output + a generous timeout (e.g. 600s):
    ```
    codex exec --skip-git-repo-check -s workspace-write -C <dirname(out_path)>
      "Generate a {size} cinematic image: {prompt}. Use your image-generation tool (do NOT draw it
       with code/PIL). Save the resulting PNG to {out_path}. Output nothing else."
    ```
  - **Validate**: after the run, if `out_path` is missing or `PIL.Image.open(out_path).verify()`
    fails → raise `RuntimeError` (so the caller catches it and falls back). No key is ever used.

## Component 2 — provider dispatch (`imagegen.py` `synthesize_images`)
- Keep the gate: `if meta.get("image_source") != "openai": return data`.
- Resolve provider once: `provider = (meta.get("image_provider") or "auto").lower()`; if `"auto"`
  → `"codex" if _codex_available() else "openai"`.
- Per pending scene: `model = "codex" if provider == "codex" else DEFAULT_MODEL`; compute
  `_cache_path(out_dir, prompt, model, size, quality)` (provider-distinct); on cache miss:
  - `provider == "codex"` → `_generate_codex(prompt, cp, size, quality)` (no key)
  - else → `key = key or env/~.openai_key`; `generate(prompt, cp, key, size, quality, DEFAULT_MODEL)`
  - write the manifest sidecar with `"provider"` + `model`; set `s["image"]`.
- The `except Exception` fallback is unchanged (any provider failure → free-tier fallback + notice).
- Reporting: for Codex, print "via Codex plan (no key)"; for OpenAI, the existing `est $X`.
- `key` resolution from `~/.openai_key` (read if present) is added to the OpenAI branch so the
  workflow's file-based key still works.

## Component 3 — schema (`storyboard.py`)
- `VALID_IMAGE_PROVIDERS = {"auto", "codex", "openai"}`; in `validate`, if `meta.image_provider` is
  present it must be one of them. (`image_source`/`image_quality` checks unchanged.)

## Component 4 — workflow (`SKILL.md`)
- Interview (gpt-image tier): no longer *always* ask for a key. Instead: **if `codex` is installed,
  generate via Codex's native image-gen (no key — uses your Codex plan, but slower); else ask for
  the OpenAI key (`OPENAI_API_KEY` / `~/.openai_key`); else fall back to the free programmatic / HTML
  tier.** Set `meta.image_provider` (`auto` default) when the user wants to force one.
- Guardrails + failure table: document the auto-Codex-first behavior, the speed tradeoff, and
  *no Codex + no key → free fallback*.

## Data contract
```json
{ "meta": { "image_source": "openai", "image_provider": "auto",
            "image_quality": "medium", "image_size": "1536x1024" } }
```

## Error handling
| Condition | Behavior |
|---|---|
| `image_provider:"auto"` + codex on PATH | Use Codex (no key). |
| `image_provider:"auto"` + no codex | Use the OpenAI key path (env/`~/.openai_key`); no key → free fallback. |
| Codex run fails / no valid image produced | `_generate_codex` raises → caught → that scene falls back to free tier. |
| `image_provider:"openai"` forced, no key | `generate` raises "no OPENAI_API_KEY" → free fallback. |
| Cached image present | Skip generation (free, offline) — provider-keyed cache. |

## Testing (all mocked — NO real codex, NO network)
- `_codex_available`: mock `shutil.which` → True/None.
- `_generate_codex`: mock `subprocess.run` to (a) write a valid PNG at `out_path` → asserts the
  `codex exec` argv (subcommand, `--skip-git-repo-check`, `-s workspace-write`, `-C`, the prompt
  names `out_path`), no key referenced; (b) write nothing → `_generate_codex` raises.
- `synthesize_images` dispatch: `image_provider:"auto"` + `_codex_available` mocked True →
  `_generate_codex` called, `generate` NOT called, no key needed; + mocked False with a key →
  `generate` called; provider-keyed cache path differs (model "codex" vs "gpt-image-2").
- schema: `image_provider` enum validated; bad value raises; absent = fine.
- Existing imagegen/render tests stay green.

## Out of scope
Controlling Codex's exact output dimensions; streaming Codex progress; using Codex for TTS or other
media; parallelizing Codex runs. Codex stays a single-image, best-effort provider; the API-key path
remains the deterministic/faster option.
