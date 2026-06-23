# Parallel Critic Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic `agents/critic.md` with a parallel panel — two script-stage critics (narrative, content) run concurrently at step 5, an AV critic runs post-render at step 8 fed by a new deterministic `scripts/check_av.py`.

**Architecture:** A new pure-logic A/V gate (`check_av.py`) probes the render and hard-fails on drift / non-uniform clip audio rates. Three standalone agent files redistribute the full R0–R7 rubric. SKILL.md dispatches the two script critics in one message (parallel), synthesizes a single PASS/REVISE, and runs the AV critic + `check_av.py` at the sample stage.

**Tech Stack:** Python 3 (stdlib + ffprobe), pytest, Markdown agent prompts.

## Global Constraints
- `check_av.py` DETERMINISTIC (no randomness/wall-clock). `evaluate(...)` is PURE (no I/O) so it unit-tests without ffprobe. Fail (`ok=False`) when `abs(v_dur-a_dur) > drift_tol` (default 0.3) OR clip rates non-uniform OR a stream is missing (dur ≤ 0). Cue/scene count mismatch is a WARNING only.
- Full R0–R7 redistribution, nothing lost: **narrative** owns R0, R1, R1b, R1c, R4, R7(text), coverage, narrative-pull; **content** owns R1d, R1e, R2, R3, R5, R6, informativeness/optimization; **av** owns A/V-sync, R7(rendered captions), visual-rendering quality.
- Each critic returns its OWN `PASS`/`REVISE` + EDITS; hard-REVISE triggers: R0 (narrative), R1c (narrative), R1d fabricated on-screen value (content), R7 (either level), A/V drift (av). Overall ship only when ALL pass.
- Retire `agents/critic.md` (delete) and leave NO dangling reference to it.
- Existing test suite stays green.

---

### Task 1: `scripts/check_av.py` — deterministic A/V gate

**Files:**
- Create: `scripts/check_av.py`
- Test: `tests/test_check_av.py` (new)

**Interfaces (Produces):**
- `evaluate(v_dur, a_dur, rates, n_cues, n_scenes, drift_tol=0.3) -> dict` (keys: ok, drift, uniform_rates, issues, warnings)
- `probe_durations(mp4) -> (v_dur, a_dur)`; `clip_rates(clips_dir) -> list[int]`; `check(out_dir) -> dict`; `main()`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_check_av.py`:
```python
import os, subprocess, pytest
import check_av
import _common

def test_evaluate_aligned_ok():
    r = check_av.evaluate(10.0, 10.05, [48000, 48000], 5, 3)
    assert r["ok"] is True and r["uniform_rates"] is True and r["issues"] == []

def test_evaluate_drift_fails():
    r = check_av.evaluate(10.0, 12.6, [48000], 5, 3)
    assert r["ok"] is False and r["drift"] == 2.6
    assert any("drift" in i for i in r["issues"])

def test_evaluate_nonuniform_rates_fails():
    r = check_av.evaluate(10.0, 10.0, [22050, 24000], 5, 3)
    assert r["ok"] is False and r["uniform_rates"] is False
    assert any("sample rate" in i for i in r["issues"])

def test_evaluate_missing_stream_fails():
    r = check_av.evaluate(10.0, 0.0, [48000], 5, 3)
    assert r["ok"] is False

def test_evaluate_no_clips_is_uniform():
    r = check_av.evaluate(10.0, 10.1, [], 5, 3)
    assert r["ok"] is True and r["uniform_rates"] is True   # no clips -> uniformity skipped

def test_evaluate_cue_mismatch_is_warning_not_failure():
    r = check_av.evaluate(10.0, 10.0, [48000], 0, 3)
    assert r["ok"] is True and any("caption" in w for w in r["warnings"])

@pytest.mark.skipif(not _common.have_tool("ffmpeg"), reason="needs ffmpeg")
def test_check_integration_aligned_then_drift(tmp_path):
    out = str(tmp_path)
    aligned = os.path.join(out, "out.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=30",
                    "-f", "lavfi", "-i", "sine=duration=3", "-c:v", "libx264", "-c:a", "aac",
                    "-shortest", aligned], capture_output=True)
    r = check_av.check(out)
    assert r["ok"] is True and r["drift"] < 0.3
    # now a mismatched render: 5s video, 3s audio (no -shortest)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
                    "-f", "lavfi", "-i", "sine=duration=3", "-c:v", "libx264", "-c:a", "aac",
                    aligned], capture_output=True)
    r2 = check_av.check(out)
    assert r2["ok"] is False and r2["drift"] > 1.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/donghanglyu/.claude/skills/slides-to-video && python3 -m pytest tests/test_check_av.py -v`
Expected: FAIL (`No module named 'check_av'`).

- [ ] **Step 3: Write the implementation**

Create `scripts/check_av.py`:
```python
"""Deterministic A/V sanity gate for a rendered video. Probes out.mp4 (video vs audio stream
duration), the per-scene clips (audio sample-rate uniformity), and out.srt (caption-cue count),
and fails on A/V drift or non-uniform clip audio rates — the failure mode that desyncs the
'-c copy' concat. Feeds the AV critic (SKILL.md step 8). No randomness, no wall-clock."""
import glob, os, subprocess, sys

def _ffprobe(args):
    return subprocess.run(["ffprobe", "-v", "error", *args], capture_output=True, text=True).stdout.strip()

def probe_durations(mp4):
    def dur(stream):
        out = _ffprobe(["-select_streams", stream, "-show_entries", "stream=duration",
                        "-of", "default=nw=1:nk=1", mp4])
        try:
            return float(out.splitlines()[0])
        except (ValueError, IndexError):
            return 0.0
    return dur("v:0"), dur("a:0")

def clip_rates(clips_dir):
    rates = []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        out = _ffprobe(["-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                        "-of", "default=nw=1:nk=1", c])
        try:
            rates.append(int(out.splitlines()[0]))
        except (ValueError, IndexError):
            pass
    return rates

def evaluate(v_dur, a_dur, rates, n_cues, n_scenes, drift_tol=0.3):
    drift = abs(v_dur - a_dur)
    uniform = len(set(rates)) <= 1
    issues = []
    if drift > drift_tol:
        issues.append(f"A/V drift {drift:.3f}s > {drift_tol}s (video {v_dur:.2f}s vs audio {a_dur:.2f}s)")
    if not uniform:
        issues.append(f"non-uniform clip audio sample rates {sorted(set(rates))} — '-c copy' concat desyncs")
    if v_dur <= 0 or a_dur <= 0:
        issues.append(f"missing stream (video {v_dur:.2f}s, audio {a_dur:.2f}s)")
    warnings = []
    if n_scenes and n_cues == 0:
        warnings.append("no caption cues in out.srt")
    ok = (drift <= drift_tol) and uniform and v_dur > 0 and a_dur > 0
    return {"ok": ok, "drift": round(drift, 3), "uniform_rates": uniform,
            "issues": issues, "warnings": warnings}

def _count_cues(srt):
    try:
        return open(srt).read().count(" --> ")
    except OSError:
        return 0

def check(out_dir):
    v, a = probe_durations(os.path.join(out_dir, "out.mp4"))
    rates = clip_rates(os.path.join(out_dir, ".clips"))
    n_cues = _count_cues(os.path.join(out_dir, "out.srt"))
    n_scenes = 0
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import storyboard as sb
        n_scenes = len(sb.load(os.path.join(out_dir, "storyboard.json")).get("slides", []))
    except Exception:
        pass
    r = evaluate(v, a, rates, n_cues, n_scenes)
    r.update({"video_dur": round(v, 3), "audio_dur": round(a, 3),
              "rates": sorted(set(rates)), "cues": n_cues, "scenes": n_scenes})
    return r

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    r = check(out_dir)
    print(f"[check_av] {'OK' if r['ok'] else 'FAIL'}  video={r['video_dur']}s audio={r['audio_dur']}s "
          f"drift={r['drift']}s rates={r['rates']} cues={r['cues']}/{r['scenes']}")
    for i in r["issues"]:
        print(f"  ISSUE: {i}")
    for w in r["warnings"]:
        print(f"  warn: {w}")
    sys.exit(0 if r["ok"] else 1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_check_av.py -v`
Expected: PASS (6 pure tests; the integration test passes with ffmpeg, else skipped).

- [ ] **Step 5: Commit**

```bash
git add scripts/check_av.py tests/test_check_av.py
git commit -m "feat(check_av): deterministic A/V gate — fails on drift / non-uniform clip rates"
```

---

### Task 2: three standalone critic agent files (retire the monolith)

**Files:**
- Create: `agents/critic-narrative.md`, `agents/critic-content.md`, `agents/critic-av.md`
- Delete: `agents/critic.md`
- Read first (source of the rubric text to lift): `agents/critic.md` (before deleting)

- [ ] **Step 1: Read the current rubric**

Read `agents/critic.md` fully — it holds the R0–R7 text + the EDITS/VERDICT output format. You will split this text across the three new files verbatim where possible, adapting only the framing.

- [ ] **Step 2: Write `agents/critic-narrative.md`**

A self-contained agent prompt (mirror critic.md's structure: intro, `## Your inputs`, `## Rubric`,
`## Output format` with EDITS + a one-word `PASS`/`REVISE` VERDICT). It reviews the SCRIPT/storyboard
(pre-TTS) and owns ONLY:
- **R0 — Factual accuracy & fidelity** (no invented facts/numbers; close to the slides + materials) — THE primary, hard-REVISE check.
- **R1 — Spoken-style fluency** (one idea per sentence, addressed to "you", human not AI).
- **R1b — Narration in `meta.language`**; **R1c — voice matches that language** (hard REVISE — a wrong-language voice garbles TTS).
- **R4 — Explicit transitions** between beats.
- **R7 (text level) — captions auto-derive from `narration`**: clean sentence segmentation, no garbled/again-truncated text, fits on screen (hard REVISE on a real subtitle error).
- **Re-conceived coverage** (a re-conceived arc still covers the source's substance, invents nothing) + **narrative pull** (hook + throughline that keeps the viewer watching).
VERDICT REVISE on ANY R0, R1c, or R7 failure. End by stating the file IS the review (VERDICT line + EDITS by slide `index`).

- [ ] **Step 3: Write `agents/critic-content.md`**

Self-contained, reviews the SCRIPT/storyboard, owns ONLY:
- **Content quality** — informativeness, structure, depth; concrete **optimization suggestions**.
- **R3 — Pacing** within the ceiling (no frame too long).
- **R1d — Animated scenes show only sourced content** — a fabricated/mis-stated on-screen value (chart values/labels, titles, timeline events) is an R0-class **hard REVISE**.
- **Informative-first visual selection** — never a decorative photo for a fact; the `visual.type` fits the point.
- **R1e — Imagery broll faithfulness** — `motif`/`broll` must be GENERIC; FAIL if a prompt names/depicts a specific landmark/logo/face or in-image text; `asserted` AI imagery is FAIL.
- **R2 — Audio↔visual coherence** — each narration line matches its beat's visual.
- **R5/R6 — Callout count + in-bounds** (slide scenes only).
VERDICT REVISE on any R1d invented value, R1e fabrication, or other failure. File IS the review (VERDICT + EDITS by `index`).

- [ ] **Step 4: Write `agents/critic-av.md`**

Self-contained, reviews the RENDERED sample / `out.mp4` (step 8). Owns ONLY:
- **A/V sync** — read the report from `python scripts/check_av.py <out_dir>` (video dur ≈ audio dur; per-clip sample-rate uniformity). A `FAIL`/non-zero exit is a **hard REVISE** (fix: clear `.clips/`, regenerate audio with one engine, re-render).
- **R7 (rendered) — burned-in captions** are legible, correct, aligned with speech, no tofu/□□□.
- **Visual rendering quality** — the theme is applied with the right light/dark mode, no blank/unstyled pages, no glyph tofu, motion smooth (no jitter).
State its inputs are the rendered sample frames + the `check_av.py` report. File IS the review (VERDICT + the offending frames/timestamps).

- [ ] **Step 5: Delete the monolith + verify**

```bash
git rm agents/critic.md
grep -rn "R0\|R1c\|R1d\|R1e\|R7\|PASS\|REVISE\|narrative pull\|check_av\|optimization" agents/critic-narrative.md agents/critic-content.md agents/critic-av.md | head
```
Expect each file to contain its owned items. Confirm no rubric item is missing across the three.

- [ ] **Step 6: Commit**

```bash
git add agents/critic-narrative.md agents/critic-content.md agents/critic-av.md
git rm agents/critic.md 2>/dev/null; git add -A agents/
git commit -m "feat(agents): split critic into narrative + content (script) + av (render) panel"
```

---

### Task 3: SKILL.md workflow — parallel panel + synthesis + repoint references

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Find every critic reference**

```bash
grep -n "critic\|critic.md\|CHECK\|R0\|R7\|step 5\|step 8\|sample sign-off" SKILL.md
```
Note each spot that names `agents/critic.md` or "the critic" (step 3.5 PLAN→WRITE→CHECK note, step 4 cross-ref, step 5, step 8, the failure table).

- [ ] **Step 2: Rewrite step 5 (parallel script critics + synthesis)**

Replace the single-critic step 5 with: dispatch `agents/critic-narrative.md` AND
`agents/critic-content.md` **concurrently — in ONE message with two Agent calls** — on the storyboard
+ comprehension brief + materials. Synthesize: overall **PASS only when BOTH return PASS**; apply the
UNION of their required EDITS; re-dispatch the panel (or the failing critic) until both PASS. Keep the
existing 🔴 script sign-off after PASS. Update the PLAN→WRITE→CHECK note (the CHECK is now a parallel
panel).

- [ ] **Step 3: Rewrite step 8 (rendered review with check_av + AV critic)**

In step 8 (sample sign-off), after rendering the sample add: run
`python scripts/check_av.py <out_dir>` (deterministic A/V gate — non-zero exit = A/V drift / non-uniform
clip rates → fix and re-render) and dispatch `agents/critic-av.md` on the sample frames + the check
report. Require its PASS before the 🔴 sample sign-off.

- [ ] **Step 4: Repoint the rest + failure table**

Replace remaining `agents/critic.md` / "the critic" references (step 3.5 note, step 4 cross-ref) with
the panel. In the `## When a step fails` table, ensure the A/V-drift row references `check_av.py`
(it already does after the prior fix) and add a line that the AV critic + `check_av.py` gate the
rendered output. Ensure NO reference to the deleted `agents/critic.md` remains.

- [ ] **Step 5: Verify + full suite + commit**

```bash
grep -n "critic-narrative\|critic-content\|critic-av\|check_av.py\|in ONE message\|in parallel\|PASS only when BOTH" SKILL.md
grep -rn "agents/critic.md" SKILL.md   # expect: NO matches
python3 -m pytest -q
```
Expected: the panel + check_av wired in; no dangling `critic.md`; full suite PASSES.
```bash
git add SKILL.md
git commit -m "docs(skill): step 5 parallel critic panel + synthesis; step 8 check_av + AV critic"
```

---

## Self-Review

**Spec coverage:** `check_av.py` pure `evaluate` + probes + `check` + `main` (Task 1) ✓; three standalone agents with the full R0–R7 redistribution (Task 2) ✓; `critic.md` retired + references repointed (Tasks 2/3) ✓; SKILL.md step 5 parallel + synthesis, step 8 check_av + AV critic (Task 3) ✓; faithfulness preserved across narrative R0 + content R1d/R1e (Task 2) ✓; error handling (missing stream → dur 0 → fail; no clips → uniform; cue mismatch → warning) encoded in `evaluate` (Task 1) ✓. Out-of-scope (4th critic, auto-fix) has no task.

**Placeholder scan:** none — `check_av.py` + all tests are complete + runnable; agent-file content is specified by its exact owned-rubric list (the implementer lifts the detailed text from the existing `critic.md` it reads in Step 1).

**Type consistency:** `evaluate(v_dur, a_dur, rates, n_cues, n_scenes, drift_tol=0.3) -> dict` with keys `ok/drift/uniform_rates/issues/warnings` is defined in Task 1 and asserted by the Task-1 tests with those exact keys. `check(out_dir)` adds `video_dur/audio_dur/rates/cues/scenes`. The agent filenames `critic-narrative.md`/`critic-content.md`/`critic-av.md` (Task 2) match the SKILL.md dispatch names (Task 3). The rubric-ownership split (narrative: R0/R1/R1b/R1c/R4/R7-text; content: R1d/R1e/R2/R3/R5/R6; av: A/V-sync/R7-rendered/visual) is identical in the spec, Task 2, and the Global Constraints.
