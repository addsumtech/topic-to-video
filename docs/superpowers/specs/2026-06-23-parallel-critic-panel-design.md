# Design: parallel critic panel (general)

**Date:** 2026-06-23
**Skill:** slides-to-video
**Status:** approved (brainstorming) → ready for implementation plan

## Problem & goal

The skill has ONE monolithic critic (`agents/critic.md`, R0–R7) run once at step 5. It mixes
unrelated concerns (faithfulness, content quality, rendered-caption legibility) in a single pass,
and the A/V-sync failure we just fixed was never a standing check. Split the critic into a
**parallel panel of three specialized critics across two stages**, redistributing the full rubric
so nothing is lost, and add a deterministic A/V gate. Faster (script critics run concurrently),
sharper (each critic owns one responsibility), and A/V drift is caught mechanically.

## Decisions (from brainstorming)
- **Two stages.** Content + narrative critics run IN PARALLEL on the script/storyboard at step 5
  (before TTS). The AV/video critic runs at the sample/render stage (step 8) on the real `out.mp4`.
- **Deterministic A/V gate.** A new `scripts/check_av.py` probes the render and hard-fails on drift;
  the AV critic reads its report + judges the frames.
- **Three standalone agent files** (retire the monolith).

## Architecture
Two review stages, three agents, one new check script. SKILL.md dispatches the two script critics
concurrently (one message, two Agent calls), the controller synthesizes a single PASS/REVISE, and
the AV critic runs post-render fed by `check_av.py`. The pipeline order is unchanged.

## Component 1 — `agents/critic-narrative.md` (manuscript & narrative — script stage)
Owns (from the old rubric): **R0** factual accuracy/fidelity (no invented facts/numbers; close to
the slides + materials) — the safety-critical gate; **R1** spoken-style fluency (human, not
read-aloud bullets); **R1b** narration in `meta.language`; **R1c** voice matches that language;
**R4** explicit transitions; **R7 (text level)** the captions auto-derived from `narration` segment
into clean readable lines with no garbled/again-truncated text; plus **re-conceived coverage** and
**narrative pull** (a hook + throughline that keeps the viewer watching — new emphasis). Returns its
own `PASS`/`REVISE` (R0, R1c are hard REVISE) + EDITS citing slide `index`.

## Component 2 — `agents/critic-content.md` (content quality — script stage)
Owns: content **informativeness / structure / depth** and **optimization suggestions** (new
emphasis); **R3** pacing within ceiling; **R1d** animated scenes show only sourced content (a
fabricated/mis-stated on-screen value is an R0-class hard REVISE); informative-first **visual-type
selection** (never a decorative photo for a fact); **R1e** imagery broll faithfulness (generic only
— no named/specific landmark, logo, face, or in-image text); **R2** audio↔visual coherence (each
line matches its beat); **R5/R6** callout count + in-bounds. Returns its own `PASS`/`REVISE` (R1d
fabricated value is hard REVISE) + EDITS.

## Component 3 — `agents/critic-av.md` (video & A/V — render stage)
Runs on the rendered sample / `out.mp4`. Owns: **A/V sync** (video duration ≈ audio duration;
per-clip sample-rate uniformity) — reads `check_av.py`'s report and treats a drift/non-uniform
failure as hard REVISE; **R7 (rendered)** the burned-in captions are legible, correct, aligned with
speech, no tofu/□□□; **visual rendering quality** (theme applied + correct light/dark mode, no
blank/unstyled pages, no glyph tofu, motion smooth / no jitter). Returns `PASS`/`REVISE` + the
specific frames/timestamps at fault.

## Component 4 — `scripts/check_av.py` (new, deterministic A/V gate)
- `evaluate(v_dur, a_dur, rates, n_cues, n_scenes, drift_tol=0.3) -> dict` (PURE, no I/O): returns
  `{"ok": bool, "drift": float, "uniform_rates": bool, "issues": [str]}`. `ok` is False when
  `abs(v_dur-a_dur) > drift_tol` OR `len(set(rates)) > 1`. Cue/scene mismatch is a **warning** only
  (captions derive from sentences, so counts legitimately differ) — recorded in `issues`, not
  failing `ok`.
- `probe_durations(mp4) -> (v_dur, a_dur)` and `clip_rates(clips_dir) -> list[int]` (use `ffprobe`).
- `check(out_dir) -> dict` wires probing → `evaluate`.
- `main()`: print a human report; **exit 1** when not `ok`, else 0.
- Deterministic (no randomness/wall-clock). Probe helpers tolerate a missing stream (return 0.0).

## Component 5 — workflow (`SKILL.md`)
- **Step 5 (script review, parallel):** dispatch `critic-narrative` + `critic-content`
  CONCURRENTLY (one message, two Agent calls) on the storyboard + comprehension brief + materials.
  **Synthesize:** overall `PASS` only if BOTH return PASS; apply the UNION of required EDITS;
  re-dispatch until both PASS. Then the existing 🔴 script sign-off. (PLAN → WRITE → **CHECK panel**.)
- **Step 8 (rendered review):** after the sample renders, run `python scripts/check_av.py <out_dir>`
  and dispatch `critic-av` on the sample frames + the check report. Must PASS (A/V drift or a
  rendered-caption error = REVISE → fix + re-render). Then the 🔴 sample sign-off.
- Retire `agents/critic.md`: delete it and repoint every reference (step 3.5/4/5/8 prose, the
  PLAN→WRITE→CHECK note, the failure table) to the panel.
- General across all three visual tiers (programmatic / gpt-image / HTML).

## Faithfulness (unchanged, now split)
R0 narration faithfulness (narrative critic) + R1d on-screen-value faithfulness (content critic) +
R1e broll faithfulness (content critic) together preserve the "no invented facts" guarantee — both
script critics can flag a faithfulness issue and either one's REVISE blocks the ship.

## Error handling
| Condition | Behavior |
|---|---|
| One script critic PASS, the other REVISE | Overall REVISE — apply that critic's edits, re-dispatch the panel (or just the failing one) until both PASS. |
| `check_av.py`: `out.mp4` missing / no audio stream | Probe returns 0.0 → reported as an issue; AV critic flags it. |
| `check_av.py`: drift > 0.3s or non-uniform clip rates | Exit 1 → AV critic REVISE → fix (clear `.clips/`, normalize audio) + re-render. |
| `.clips/` absent (single-pass render) | `clip_rates` returns [] → uniformity check skipped (the out.mp4 duration check still runs). |
| ffprobe missing | `check_av.py` errors clearly; AV critic falls back to eyeballing durations. |

## Testing (deterministic; ffprobe-dependent parts skipif-gated)
- **`check_av.py` `evaluate` (pure, always runs):** aligned (v≈a, uniform rates) → ok; drift > tol →
  not ok + drift reported; non-uniform rates → not ok; cue≠scene count → ok but warning recorded.
- **`check_av.py` integration (skipif no ffmpeg):** build a tiny aligned mp4 (lavfi) → `check` ok,
  exit 0; build a mismatched-duration mp4 → not ok, exit 1.
- **agent files (prose):** grep each new file for its owned rubric items; grep `critic.md` is gone
  and no dangling references remain in SKILL.md.
- **SKILL.md (prose):** grep step 5 dispatches both script critics "in parallel" + synthesis; step 8
  runs `check_av.py` + `critic-av`.
- Existing suite stays green.

## Out of scope
A 4th critic; auto-fixing (critics only report + edit text, as today); parallelizing the AV critic's
internal checks; a GUI report. The panel is three agents + one script.
