# edge-tts Provider + Accent/Gender Voice Selection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `edge-tts` as the preferred free, natural-neural TTS provider for the slides-to-video skill, with user-selectable accent and gender, falling back to macOS `say` offline.

**Architecture:** Voice stays a single `"provider:name"` string in `meta.voice`. A new `edge` provider joins `say`/`openai`. A `_resolve_voice(meta)` step maps the new `"auto"` default to a concrete voice (edge if available, else say), so `_provider()` only ever splits a concrete string. A curated `EDGE_VOICE_CATALOG` maps `(language, accent, gender) → voice_id`. `render.py` is untouched (edge emits `.mp3` like openai).

**Tech Stack:** Python 3, `edge-tts` (pip, pure-python, neural TTS via Microsoft Edge endpoint), macOS `say`, ffprobe (existing), pytest.

## Global Constraints

- Reuse the existing `meta.voice = "provider:name"` scheme; do NOT add a new schema object. (spec: Approach A)
- edge-tts is the *preferred default*; macOS `say` is the offline fallback; `openai` stays available with a key. (spec: Decisions)
- Never auto-install edge-tts silently — the *workflow* offers `pip install edge-tts` once; `tts.py` only ever falls back to `say`. (spec: Decisions)
- Tests must NOT touch the network or call the real Edge endpoint — mock every synthesis/availability path. (spec: Testing)
- Default gender for `auto` resolution is `female`. (spec: User Review)
- `tts.py` imports `_common` as a module; tests patch `tts._common.run` / `tts._have_edge` / `tts._edge`. (codebase fact)

---

### Task 1: Edge voice catalog + `resolve_edge_voice` + reference doc

**Files:**
- Modify: `scripts/tts.py` (add catalog + resolver after `SAY_VOICE_BY_LANG`, ~line 45)
- Modify: `references/tts-voices.md` (add edge-tts section after the non-English voices table)
- Test: `tests/test_tts.py`

**Interfaces:**
- Produces: `EDGE_VOICE_CATALOG` (dict), `resolve_edge_voice(language, accent=None, gender="female") -> str|None`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tts.py`:
```python
def test_edge_catalog_resolution():
    assert tts.resolve_edge_voice("en", "UK", "male") == "en-GB-RyanNeural"
    assert tts.resolve_edge_voice("zh", "Mainland", "female") == "zh-CN-XiaoxiaoNeural"
    assert tts.resolve_edge_voice("en") == "en-US-AriaNeural"      # default accent + gender
    assert tts.resolve_edge_voice("ja", gender="male") == "ja-JP-KeitaNeural"
    assert tts.resolve_edge_voice("EN-us", "uk") == "en-GB-SoniaNeural"  # case-insensitive
    assert tts.resolve_edge_voice("xx") is None                   # unknown language
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_tts.py::test_edge_catalog_resolution -v`
Expected: FAIL with `AttributeError: module 'tts' has no attribute 'resolve_edge_voice'`

- [ ] **Step 3: Write minimal implementation**

In `scripts/tts.py`, add after the `_resolve_say_voice` function (after line 56):
```python
# Curated edge-tts neural voices: language -> accent -> {female, male} -> voice id.
# "_default" names the accent used when none is given. Escape hatch for anything not
# here: `python -m edge_tts --list-voices` and set meta.voice = "edge:<id>" directly.
EDGE_VOICE_CATALOG = {
    "en": {"_default": "US",
           "US": {"female": "en-US-AriaNeural", "male": "en-US-GuyNeural"},
           "UK": {"female": "en-GB-SoniaNeural", "male": "en-GB-RyanNeural"},
           "AU": {"female": "en-AU-NatashaNeural", "male": "en-AU-WilliamNeural"},
           "IN": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"}},
    "zh": {"_default": "Mainland",
           "Mainland": {"female": "zh-CN-XiaoxiaoNeural", "male": "zh-CN-YunxiNeural"},
           "HK": {"female": "zh-HK-HiuMaanNeural", "male": "zh-HK-WanLungNeural"},
           "TW": {"female": "zh-TW-HsiaoChenNeural", "male": "zh-TW-YunJheNeural"}},
    "ja": {"_default": "JP", "JP": {"female": "ja-JP-NanamiNeural", "male": "ja-JP-KeitaNeural"}},
    "ko": {"_default": "KR", "KR": {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"}},
    "es": {"_default": "ES", "ES": {"female": "es-ES-ElviraNeural", "male": "es-ES-AlvaroNeural"}},
    "fr": {"_default": "FR", "FR": {"female": "fr-FR-DeniseNeural", "male": "fr-FR-HenriNeural"}},
    "de": {"_default": "DE", "DE": {"female": "de-DE-KatjaNeural", "male": "de-DE-ConradNeural"}},
    "pt": {"_default": "BR", "BR": {"female": "pt-BR-FranciscaNeural", "male": "pt-BR-AntonioNeural"}},
    "it": {"_default": "IT", "IT": {"female": "it-IT-ElsaNeural", "male": "it-IT-DiegoNeural"}},
    "ru": {"_default": "RU", "RU": {"female": "ru-RU-SvetlanaNeural", "male": "ru-RU-DmitryNeural"}},
    "nl": {"_default": "NL", "NL": {"female": "nl-NL-ColetteNeural", "male": "nl-NL-MaartenNeural"}},
    "hi": {"_default": "IN", "IN": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"}},
}

def resolve_edge_voice(language, accent=None, gender="female"):
    """Map (language, accent, gender) to a concrete edge-tts voice id, or None if the
    language isn't in the curated catalog. Accent falls back to the language's default;
    gender falls back to female. Language/accent matching is case-insensitive."""
    lang = (language or "").lower().replace("_", "-").split("-")[0]
    table = EDGE_VOICE_CATALOG.get(lang)
    if not table:
        return None
    by_key = {k.lower(): k for k in table if k != "_default"}
    key = by_key.get((accent or "").lower(), table["_default"])
    g = gender if gender in ("female", "male") else "female"
    return table[key][g]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tts.py::test_edge_catalog_resolution -v`
Expected: PASS

- [ ] **Step 5: Add the reference doc section**

In `references/tts-voices.md`, after the "Non-English voices (multi-language)" table, add:
````markdown
---

## edge-tts (preferred free voice — natural neural, cross-platform)

`edge-tts` uses Microsoft Edge's free online neural voices — far more natural than `say`,
and it runs on any OS (not just macOS). Install once:

```bash
pip install edge-tts
```

Set a voice by accent + gender; the id goes in `meta.voice` as `edge:<id>`:

```json
"meta": { "voice": "edge:en-GB-SoniaNeural" }
```

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

Anything not listed: `python -m edge_tts --list-voices` and use any id as `edge:<id>`.

**Notes:** needs network (it's a free, unauthenticated cloud endpoint — an unofficial Edge
service, stable for years but not contractual). When edge-tts is unavailable, tts.py falls
back to macOS `say`.
````

- [ ] **Step 6: Commit**

```bash
git add scripts/tts.py references/tts-voices.md tests/test_tts.py
git commit -m "feat(tts): edge-tts voice catalog + resolve_edge_voice + docs"
```

---

### Task 2: `_have_edge` availability check + `_resolve_voice`

**Files:**
- Modify: `scripts/tts.py` (add both functions after `resolve_edge_voice`)
- Test: `tests/test_tts.py`

**Interfaces:**
- Consumes: `resolve_edge_voice`, `_resolve_say_voice` (Task 1 / existing)
- Produces: `_have_edge() -> bool`, `_resolve_voice(meta: dict) -> str` (a concrete `"provider:name"`)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tts.py`:
```python
def test_resolve_voice_auto_prefers_edge(monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    assert tts._resolve_voice({"voice": "auto", "language": "en"}) == "edge:en-US-AriaNeural"
    assert tts._resolve_voice({"voice": "auto", "language": "zh"}) == "edge:zh-CN-XiaoxiaoNeural"

def test_resolve_voice_auto_falls_back_to_say(monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    assert tts._resolve_voice({"voice": "auto", "language": "zh"}) == "say:Tingting"
    assert tts._resolve_voice({"voice": "auto", "language": "en"}) == "say:Samantha"

def test_resolve_voice_passthrough_explicit():
    assert tts._resolve_voice({"voice": "edge:en-GB-RyanNeural", "language": "en"}) == "edge:en-GB-RyanNeural"
    assert tts._resolve_voice({"voice": "openai:alloy", "language": "en"}) == "openai:alloy"
    assert tts._resolve_voice({"voice": "say:Alex", "language": "en"}) == "say:Alex"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tts.py -k resolve_voice -v`
Expected: FAIL with `AttributeError: module 'tts' has no attribute '_resolve_voice'`

- [ ] **Step 3: Write minimal implementation**

In `scripts/tts.py`, add after `resolve_edge_voice` (from Task 1):
```python
def _have_edge():
    """True if the edge-tts package is importable (no network check)."""
    import importlib.util
    return importlib.util.find_spec("edge_tts") is not None

def _resolve_voice(meta):
    """Turn meta.voice into a concrete 'provider:name'. The 'auto' sentinel prefers
    edge-tts (language + default accent + female) when available, else the language-
    matched macOS say voice. Any explicit 'edge:/say:/openai:' spec passes through."""
    spec = meta.get("voice", "auto")
    lang = meta.get("language", "auto")
    if spec and spec != "auto":
        return spec
    if _have_edge():
        vid = resolve_edge_voice(lang, gender="female")
        if vid:
            return f"edge:{vid}"
    name, _ = _resolve_say_voice("Samantha", lang)
    return f"say:{name}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_tts.py -k resolve_voice -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/tts.py tests/test_tts.py
git commit -m "feat(tts): _have_edge + _resolve_voice (auto -> edge|say)"
```

---

### Task 3: `_edge` synthesis function

**Files:**
- Modify: `scripts/tts.py` (add `_edge` near `_say`/`_openai`, after line 28)
- Test: `tests/test_tts.py`

**Interfaces:**
- Consumes: `_common.run` (existing)
- Produces: `_edge(text: str, out_path: str, voice: str) -> None` (writes an mp3 to `out_path`)

- [ ] **Step 1: Write the failing test** (mocks the runner — no network)

Add to `tests/test_tts.py`:
```python
def test_edge_invokes_edge_tts(monkeypatch):
    captured = {}
    monkeypatch.setattr(tts._common, "run", lambda cmd, **kw: captured.setdefault("cmd", cmd))
    tts._edge("hello world", "/tmp/clip.mp3", "en-US-AriaNeural")
    cmd = captured["cmd"]
    assert "edge_tts" in cmd
    assert cmd[cmd.index("--voice") + 1] == "en-US-AriaNeural"
    assert cmd[cmd.index("--text") + 1] == "hello world"
    assert cmd[cmd.index("--write-media") + 1] == "/tmp/clip.mp3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tts.py::test_edge_invokes_edge_tts -v`
Expected: FAIL with `AttributeError: module 'tts' has no attribute '_edge'`

- [ ] **Step 3: Write minimal implementation**

In `scripts/tts.py`, add after `_openai` (after line 28):
```python
def _edge(text, out_path, voice):
    # edge-tts neural voice via its CLI module (sync subprocess avoids threading its
    # asyncio into our sync pipeline). Writes an mp3 directly; ffprobe reads duration.
    import sys
    _common.run([sys.executable, "-m", "edge_tts",
                 "--voice", voice, "--text", text, "--write-media", out_path])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_tts.py::test_edge_invokes_edge_tts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/tts.py tests/test_tts.py
git commit -m "feat(tts): _edge synthesis via edge-tts CLI"
```

---

### Task 4: Wire `edge` into `synthesize` (resolution, ext, branch, fallback)

**Files:**
- Modify: `scripts/tts.py:58-90` (the `synthesize` function)
- Test: `tests/test_tts.py`

**Interfaces:**
- Consumes: `_resolve_voice`, `_provider`, `_resolve_say_voice`, `_edge`, `_openai`, `_say`, `_have_edge`
- Produces: `synthesize(out_dir, only=None) -> dict` (unchanged signature; now supports edge)

- [ ] **Step 1: Write the failing test** (edge path, fully mocked — no network/ffprobe)

Add to `tests/test_tts.py`:
```python
def test_synthesize_uses_edge_when_resolved(tmp_path, monkeypatch):
    out = _proj(tmp_path)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "auto"; data["meta"]["language"] = "en"
    sb.save(data, os.path.join(out, "storyboard.json"))

    monkeypatch.setattr(tts, "_have_edge", lambda: True)
    made = []
    def fake_edge(text, dest, voice):
        with open(dest, "wb") as f:
            f.write(b"\x00")
        made.append((dest, voice))
    monkeypatch.setattr(tts, "_edge", fake_edge)
    monkeypatch.setattr(tts._common, "audio_duration", lambda p: 1.0)

    res = tts.synthesize(out)
    assert made, "edge synthesis was not called"
    assert made[0][1] == "en-US-AriaNeural"
    assert all(s["audio"].endswith(".mp3") for s in res["slides"])
    assert all(s["duration"] == 1.0 for s in res["slides"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tts.py::test_synthesize_uses_edge_when_resolved -v`
Expected: FAIL (edge branch doesn't exist yet — `say`/`_say` is called instead, `made` stays empty)

- [ ] **Step 3: Write minimal implementation**

In `scripts/tts.py`, replace the body of `synthesize` from the voice-resolution line through the synthesis branch. Replace lines 63-85 (from `prov, name = _provider(...)` through the `except` fallback block) with:
```python
    prov, name = _provider(_resolve_voice(data["meta"]))
    if prov == "say":
        name, note = _resolve_say_voice(name, data["meta"].get("language", "auto"))
        if note:
            print(note)

    for s in data["slides"]:
        if only and s["index"] != only:
            continue
        text = (s.get("narration") or "").strip() or " "
        ext = "aiff" if prov == "say" else "mp3"
        rel = os.path.join("audio", f"{s['index']:02d}.{ext}")
        dest = os.path.join(out_dir, rel)
        try:
            if prov == "openai":
                _openai(text, dest, name)
            elif prov == "edge":
                _edge(text, dest, name)
            else:
                _say(text, dest, name)
        except Exception as e:
            print(f"[tts] {prov} failed ({e}); falling back to say:Samantha")
            rel = os.path.join("audio", f"{s['index']:02d}.aiff")
            dest = os.path.join(out_dir, rel)
            _say(text, dest, "Samantha")
```
(Note: the `for` loop and `except` body are unchanged from the original except for the new `elif prov == "edge"` branch and the new resolution line; shown in full so it can be pasted as one block.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_tts.py::test_synthesize_uses_edge_when_resolved -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/tts.py tests/test_tts.py
git commit -m "feat(tts): route edge provider through synthesize with say fallback"
```

---

### Task 5: Default `meta.voice = "auto"` + keep existing tests offline-deterministic

**Files:**
- Modify: `scripts/storyboard.py:26-27` (the `meta` dict in `new_storyboard`)
- Modify: `tests/test_tts.py` (force say in the live synth test)
- Modify: `tests/test_render.py` (force say in `_build`)
- Test: `tests/test_storyboard.py`

**Interfaces:**
- Produces: `new_storyboard()["meta"]["voice"] == "auto"`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_storyboard.py`:
```python
def test_default_voice_is_auto():
    assert sb.new_storyboard()["meta"]["voice"] == "auto"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_storyboard.py::test_default_voice_is_auto -v`
Expected: FAIL (`assert 'say:Samantha' == 'auto'`)

- [ ] **Step 3: Change the default**

In `scripts/storyboard.py`, in `new_storyboard`, change the `meta` dict's voice value:
```python
    meta = {"aspect": "16:9", "width": 1920, "height": 1080, "fps": 30,
            "language": "auto", "voice": "auto", "captions": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_storyboard.py::test_default_voice_is_auto -v`
Expected: PASS

- [ ] **Step 5: Keep the live synth tests on `say` (offline-deterministic)**

The default is now `"auto"`, which would prefer edge (and hit the network) if edge-tts is
installed in the dev environment. Force `say` in the two tests that actually synthesize.

In `tests/test_tts.py`, change the live test signature + first line:
```python
@pytest.mark.skipif(not _common.have_tool("say"), reason="macOS 'say' only")
def test_synthesize_writes_audio_and_durations(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "_have_edge", lambda: False)
    out = _proj(tmp_path)
    data = tts.synthesize(out)
    for s in data["slides"]:
        assert s["audio"] and os.path.exists(os.path.join(out, s["audio"]))
        assert s["duration"] and s["duration"] > 0.2
```

In `tests/test_render.py`, in `_build`, set the voice explicitly before synth:
```python
def _build(tmp_path, fixtures_dir):
    out = str(tmp_path / "proj")
    ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), out)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "say:Samantha"      # offline-deterministic; no edge/network in CI
    for s in data["slides"]:
        s["narration"] = f"This is slide {s['index']}."
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)
    return out
```

- [ ] **Step 6: Run the full suite to verify everything is green**

Run: `python3 -m pytest -q`
Expected: PASS (all tests; the new edge tests + existing say/render/storyboard tests)

- [ ] **Step 7: Commit**

```bash
git add scripts/storyboard.py tests/test_tts.py tests/test_render.py tests/test_storyboard.py
git commit -m "feat(tts): default meta.voice=auto; keep synth tests offline-deterministic"
```

---

### Task 6: SKILL.md — interview, TTS step (offer-install), guardrails, failure table

**Files:**
- Modify: `SKILL.md` (Tools line, Workflow step 1 interview, step 7 TTS, Guardrails, failure table)

**Interfaces:** none (prose). Verified by reading + grep.

- [ ] **Step 1: Update the Tools line**

In `SKILL.md`, in the `## Tools` section, change the TTS mention so edge-tts is listed:
```markdown
`soffice` (pptx→pdf), PyMuPDF `fitz`, `python-pptx`, **edge-tts** (preferred neural voice, free, cross-platform — needs network), macOS `say` (offline fallback), `ffmpeg`, PIL.
Captions burn via PIL + a bundled font (no libass needed). Optional: OpenAI/ElevenLabs
TTS if the user gives an API key.
```

- [ ] **Step 2: Update the interview (step 1) voice clause**

In `SKILL.md` Workflow step 1, replace `voice (local `say` vs cloud)` with:
```markdown
voice — **edge-tts** (natural neural, free, needs network; then pick **accent** + **gender**
from `references/tts-voices.md`) by default, with macOS `say` as the offline fallback, or
cloud TTS if they give a key;
```

- [ ] **Step 3: Update the TTS step (step 7) with the availability check + offer-to-install**

In `SKILL.md`, replace step 7 (`**TTS** — run `tts.py`...`) with:
```markdown
7. **TTS** — before synth, if `meta.voice` is `auto` or `edge:*`, check edge-tts is
   installed: `python -c "import edge_tts"`. If it's missing, **offer to install it once**
   (`pip install edge-tts`) for natural neural voices; if the user declines, set
   `meta.voice` to a `say:` fallback and continue. Then run `tts.py` (use `--only N` while
   iterating on one slide). edge-tts emits `.mp3`; `say` emits `.aiff` — both fine.
```

- [ ] **Step 4: Update Guardrails (voice forms)**

In `SKILL.md` `## Guardrails`, replace the `Set meta.voice (...)` bullet with:
```markdown
- Set `meta.voice`, `meta.captions`, and `meta.language` in the storyboard, not via flags.
  `meta.voice` is one of: `auto` (default — tts.py prefers edge-tts, else `say`),
  `edge:<id>` (e.g. `edge:en-GB-SoniaNeural`), `say:<voice>`, or `openai:<voice>`.
```

- [ ] **Step 5: Add failure-table rows**

In `SKILL.md`, in the `## When a step fails` table, after the existing `tts.py` cloud row, add:
```markdown
| `tts.py`: edge-tts not installed | The workflow offers `pip install edge-tts` once; on decline, set `meta.voice` to a `say:` fallback | tts.py auto-falls back to `say` at synth time and prints a notice — continue |
| `tts.py`: edge-tts network error / endpoint down | tts.py catches it and falls back to `say:Samantha` with a notice — continue | Switch `meta.voice` to an explicit `say:` voice (fully offline) |
```

- [ ] **Step 6: Verify the prose changes are present**

Run:
```bash
grep -n "edge-tts\|edge:<id>\|import edge_tts" SKILL.md
```
Expected: matches in Tools, step 1, step 7, Guardrails, and the failure table (≥5 lines).

- [ ] **Step 7: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): document edge-tts as preferred voice (interview, install, guardrails)"
```

---

## Self-Review

**Spec coverage:**
- edge provider → Tasks 3, 4 ✓
- preferred default + say fallback → Tasks 2 (`_resolve_voice`), 4 (synthesize), 5 (`auto` default) ✓
- accent + gender catalog + escape hatch → Task 1 (catalog + doc) ✓
- offer-install-once → Task 6 (step 7 prose); synth-time safety-net fallback → Task 4 ✓
- voice ID in meta.voice (Approach A) → all tasks; no new schema object ✓
- render.py unchanged → confirmed (no task touches it) ✓
- tests mocked / no network → Tasks 1-4 mock; Task 5 forces say offline ✓
- default gender female → Task 2 `_resolve_voice` ✓
- non-Mac + edge unavailable + no key → existing `except` falls to `say`, which errors clearly if `say` is absent (existing behavior, documented in spec) ✓

**Placeholder scan:** none — every code/test step shows full content.

**Type consistency:** `resolve_edge_voice(language, accent, gender)` and `_resolve_voice(meta)` names/returns match across Tasks 1, 2, 4. `_edge(text, out_path, voice)` matches its call in Task 4. `_provider` only ever receives a concrete string (from `_resolve_voice`), never `"auto"`.
