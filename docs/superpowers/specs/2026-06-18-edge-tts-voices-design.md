# Design: edge-tts provider + accent/gender voice selection

**Date:** 2026-06-18
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goals

The skill's "free / local" TTS path hard-depends on macOS `say`, which (a) sounds robotic
next to modern neural voices and (b) only runs on a Mac, so audio can't be rendered on
Linux/Windows runtimes. We add **edge-tts** — Microsoft Edge's free, unauthenticated neural
TTS — as a third provider, and let users choose **accent** (locale) and **gender**, which
Edge voice IDs already encode.

**Goals**
1. Add an `edge` TTS provider with natural neural voices, free and no API key.
2. Make edge-tts the *preferred default* free voice, with macOS `say` as the offline fallback.
3. Let users pick accent + gender from a curated catalog, with an escape hatch to any Edge voice.
4. Keep the pipeline working when edge-tts is unavailable (not installed / offline).

**Non-goals (YAGNI)** — rate/pitch/SSML tuning; per-slide voices; auto-install without
consent; accents beyond the curated catalog. All deferrable.

## Decisions (from brainstorming)

- **Role:** edge-tts is the preferred default; `say` is the offline fallback; `openai` stays
  available when a key is given.
- **Picker:** curated catalog (English US/UK/AU/IN; Chinese Mainland/HK/TW; single-accent
  entries for the other supported languages) × male/female, plus a "list all" escape hatch.
- **Missing dependency:** when edge-tts is the chosen voice but not installed, **offer to
  `pip install edge-tts` once**; on decline, fall back to `say`. Never auto-install silently.
- **Voice representation:** concrete voice ID in `meta.voice` (Approach A) — reuse the
  existing `provider:name` scheme; `edge` simply joins `say`/`openai`. No new schema object.

## Architecture

Voice flows through the existing single source of truth — `meta.voice` in `storyboard.json` —
as `"provider:name"`. The interview resolves language + accent + gender to a concrete Edge ID
and writes it (e.g. `"edge:en-GB-SoniaNeural"`). `tts.py` reads it and synthesizes.

### Component 1 — `scripts/tts.py`: `edge` provider

- `_edge(text, out_path, voice)`: shells out via `subprocess` to
  `python -m edge_tts --voice <id> --text <text> --write-media <out>.mp3`.
  Synchronous subprocess — deliberately avoids threading edge-tts's asyncio into the
  otherwise-sync pipeline. Output is `.mp3` (like the openai path).
- `_have_edge()`: returns whether `edge_tts` is importable (`python -c "import edge_tts"`).
- `EDGE_VOICE_CATALOG`: the machine-usable map `(language, accent, gender) -> voice_id`
  used for default resolution; the human-readable table lives in `references/tts-voices.md`.
- `_resolve_voice(meta)` precedence:
  1. `meta.voice == "edge:<id>"` → use `<id>`. If `edge_tts` import fails at synth time →
     print a notice and fall back to `say` (language-matched, existing `_resolve_say_voice`).
  2. `meta.voice == "say:<v>"` / `"openai:<v>"` → unchanged.
  3. `meta.voice == "auto"` (new default) → if edge available, resolve
     `language` + default gender (female) + default accent → an Edge ID; else `say`.
- **Resolution order (avoids the `auto` parse bug):** `synthesize()` first calls
  `_resolve_voice(meta)`, which maps the `"auto"` sentinel to a concrete `"provider:name"`
  string (edge if available, else say) and passes through any explicit `"edge:"/"say:"/"openai:"`.
  Only the resolved concrete string is handed to `_provider()` for the `":"` split — so
  `_provider()` never sees the bare `"auto"` literal. `edge` needs no parser change, only a
  new branch in `synthesize()`.

`render.py` is **unchanged** — it consumes `slide["audio"]` and gets duration from ffprobe,
so an `.mp3` from edge works exactly like the openai `.mp3`.

### Component 2 — `references/tts-voices.md`

New "edge-tts (preferred, free, neural)" section: install line, the curated accent×gender
table with voice IDs, the `python -m edge_tts --list-voices` escape hatch, and a note that it
needs network and is an unofficial endpoint.

### Component 3 — `SKILL.md`

- **Interview** voice question: **edge-tts (natural, needs net)** ▸ accent + gender ·
  **say (offline)** · **cloud (OpenAI key)**.
- **TTS step**: availability check (`python -c "import edge_tts"`); if missing → offer to
  `pip install edge-tts` once; on decline set `meta.voice` to the `say` fallback and continue.
- **Guardrails**: document the three `meta.voice` forms incl. `edge:`; note `auto`.
- **Failure table** rows: *edge offline → say fallback*; *edge not installed → offer install*.

### Component 4 — `scripts/storyboard.py`

- Default `meta.voice`: `"say:Samantha"` → `"auto"` so tts.py picks the best available
  provider per language at synth time.

## Voice catalog (initial curated set)

| Lang | Accent | Female | Male |
|---|---|---|---|
| en | US | en-US-AriaNeural | en-US-GuyNeural |
| en | UK | en-GB-SoniaNeural | en-GB-RyanNeural |
| en | AU | en-AU-NatashaNeural | en-AU-WilliamNeural |
| en | IN | en-IN-NeerjaNeural | en-IN-PrabhatNeural |
| zh | Mainland | zh-CN-XiaoxiaoNeural | zh-CN-YunxiNeural |
| zh | HK | zh-HK-HiuMaanNeural | zh-HK-WanLungNeural |
| zh | TW | zh-TW-HsiaoChenNeural | zh-TW-YunJheNeural |
| ja | — | ja-JP-NanamiNeural | ja-JP-KeitaNeural |
| ko | — | ko-KR-SunHiNeural | ko-KR-InJoonNeural |
| es | — | es-ES-ElviraNeural | es-ES-AlvaroNeural |
| fr | — | fr-FR-DeniseNeural | fr-FR-HenriNeural |
| de | — | de-DE-KatjaNeural | de-DE-ConradNeural |
| pt | — | pt-BR-FranciscaNeural | pt-BR-AntonioNeural |
| it | — | it-IT-ElsaNeural | it-IT-DiegoNeural |
| ru | — | ru-RU-SvetlanaNeural | ru-RU-DmitryNeural |
| nl | — | nl-NL-ColetteNeural | nl-NL-MaartenNeural |
| hi | — | hi-IN-SwaraNeural | hi-IN-MadhurNeural |

Voice IDs to be verified against `python -m edge_tts --list-voices` during implementation.

## Error handling

| Condition | Behavior |
|---|---|
| edge-tts chosen, module missing (workflow) | Offer `pip install edge-tts` once; decline → `say` fallback |
| edge-tts chosen, module missing (synth time safety net) | Print notice, fall back to `say`, continue (no hard crash) |
| edge-tts network error | Catch in `_edge`, print notice, fall back to `say` |
| Non-Mac + edge unavailable + no openai key | `say` also unavailable → clear error telling the user to install edge-tts or provide a key |

## Testing

- `_provider("edge:en-GB-SoniaNeural")` parses to `("edge", "en-GB-SoniaNeural")`.
- Catalog resolution: `(en, UK, male) -> en-GB-RyanNeural`; `(zh, Mainland, female) -> zh-CN-XiaoxiaoNeural`.
- `auto` + edge available → resolves to a catalog ID for the meta language.
- edge missing → synth falls back to `say` (mock `_have_edge` False; no network in CI).
- Existing `say` synthesis tests stay green.
- All network-touching paths are mocked; CI never calls the Edge endpoint.

## Out of scope / future

SSML/rate/pitch controls, mixing voices per slide, additional accents, caching synthesized
audio across renders.
