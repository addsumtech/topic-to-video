# Device Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw phones, tablets, laptops and monitors that show the product's real screenshots and recordings, and perform typing, taps, scrolls and drags on them on the narration's own words — sub-project 1 of the "object layer".

**Architecture:** Python owns everything that is MEASURED or DECIDED before a render (`scripts/device_script.py` parses and schedules a beat's step script; `scripts/screen_media.py` measures screenshots and recordings; `scripts/screen_text.py` finds text in a screenshot). TypeScript owns the DRAWING (`runtime/device.tsx`, `runtime/screen.tsx`, `runtime/gesture.tsx`, and two registers, `DeviceDemo` and `DeviceHero`). The numbers both sides use live once, in `remotion/src/runtime/deviceSpec.json`; the one piece of geometry Python needs (the screen's size, for the legibility gate) is ported and held to the TypeScript by a parity test.

**Tech Stack:** Remotion 4.0.486 (`OffthreadVideo`, `Img`, `Sequence` from `remotion`), React, TypeScript (types stripped by the bundler), esbuild + node for pure-function probes, Python 3 + pytest, numpy + PIL (already used), ffprobe, macOS Vision through a compiled Swift helper (optional), tesseract (optional).

**Spec:** `docs/superpowers/specs/2026-09-26-device-layer-design.md` (reference renders of the approved choices beside it in `assets/2026-09-26-device-layer/`).

## Global Constraints

- Remotion stays at 4.0.486; no new npm dependency (`OffthreadVideo`, `Img`, `Sequence` all come from `remotion`).
- No new hard Python dependency; tesseract / pytesseract and the Swift toolchain are optional and every path that needs them fails LOUDLY when they are absent.
- Every register and runtime function is a pure function of the frame: no `Math.random`, no `Date`, no wall clock.
- Every colour comes from DNA tokens with `*_D0` fallbacks; the null-DNA standalone render must work.
- The content contract holds: refuse, never guess. Anything `content_contract_qa.py` flags that is genuinely not a claim carries `// @decor|@positional|@fallback|@truncates: <reason>` on the line or the line above.
- The device and everything drawn on it stay inside the content zone: above `contentBottom(W, H)`.
- Looks: `flat`, `real`, `screen`. Default when a beat names none: `real` on a dark-keyed beat, `flat` on a light one; `screen` only when chosen.
- Taps and clicks: an accent-coloured ring plus ONE expanding ripple (brand style). `tap` and `click` are one step; what is drawn follows the device kind (`touch` in deviceSpec.json).
- Caret: solid while keystrokes arrive; afterwards on/off in phases of 16 frames (`caretPhaseFrames`); reduced motion: solid; always at the typing HEAD (un-typed glyphs take no width).
- Push-in: the smallest zoom at which the target's text is as tall as the film's caption glyphs (ink height), capped at 4× (`maxZoom`); `"camera": "still"` turns it off.
- Minimum durations (seconds): screen change 0.5, tap/click 0.6, Latin keystroke 0.15, CJK word commit 0.35, scroll 0.9 — plus the rulings below.
- CJK typing: two-glyph words by default, or exactly the author's list when `type` is an array.
- Recordings: muted; playback rate capped at 2× (`maxVideoRate`).
- Text targets: macOS Vision first, tesseract elsewhere, results cached per screenshot content hash; not found / ambiguous / no recogniser are errors that list what WAS recognised.
- Every git commit stages NAMED paths only (never `git add -A` / `git add .`), never overrides git config with `-c`, and ends its message with `Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx`. Nothing is pushed.
- Never edit a register or a runtime file while `register_energy.py` / `prop_reach.py` / a full test suite is running.

## Rulings (where the spec is silent — decided here, with the reason)

- **drag** takes scroll's minimum (0.9 s) and **mark** takes tap's (0.6 s): they are the same gesture shapes.
- **cameraLeadSeconds = 0.35**: every gesture step's window opens this long BEFORE its action, so the push-in lands before the finger does; the action itself happens on the cue.
- **`mark` may carry `"video": <seconds>`** — the recording's moment that should play at that cue. Without it the spec's "piecewise-linear between cue-carrying marks" has nothing to be linear between.
- **Targets are fractions of the VISIBLE screen.** A text target on a long screenshot is converted using that step's scroll state; one scrolled out of view is an error ("scroll first").
- **The standalone demo draws skeleton bars and no text**, so no demo copy exists that could leak into a film.
- **`runtime/motion.ts` is not modified.** Every register imports it; editing it would invalidate every row of `register_energy.json` (a ~50-minute sweep). The caret converts t into frames with the exported `useAnimSpan()` instead.
- **Typing on a screenshot paints the field's own background over its placeholder** before drawing the typed text (in the DNA body face, at the field's measured text size). Without this the placeholder and the typed text would both show — found while planning; the spec did not say.
- **Aspect tolerance 4%**: a screenshot within 4% of the screen's proportion fits; taller than that is a long screenshot; wider is an error.
- **Field background tolerance 8 per channel; ink threshold 40 grey levels** — detection constants for `screen_media.py`, each exercised by a test on light AND dark screenshots.

## Review Focus

1. **An Android screenshot (1080×2400, 9:20) in a phone (9:19.5)** must fit, not error and not become a long screenshot: it is 2.6% taller, inside the 4% tolerance. → Task 3, `test_an_android_screenshot_fits_a_phone`.
2. **A dark-mode screenshot** (light text on a dark UI): text height and field detection must work with inverted polarity. → Task 3, `test_dark_mode_text_and_field`.
3. **A cue word the narration also says earlier, or twice**: the in-order search must bind each step to the right occurrence. → Task 2, `test_a_repeated_phrase_lands_on_successive_items`.
4. **A beat too short for its script**: the error states the seconds needed and available and names the steps — never a crash, never a silent squeeze. → Task 1, `test_a_short_beat_says_how_much_time_is_missing`.
5. **Typed text longer than its field**: the text scrolls left inside the field so the caret stays visible, as a real input does. → Task 9, `test_long_typed_text_stays_inside_its_field`.

## File Structure

| File | Responsibility |
|---|---|
| `remotion/src/runtime/deviceSpec.json` | Every number of the device layer, read by TS and Python |
| `scripts/device_script.py` | Step shape, per-kind minimum time, the schedule, and `prepare()` / `check_slide()` |
| `scripts/screen_media.py` | Screenshot/recording facts, text height at a point, field under a point, caption ink height |
| `scripts/screen_text.py` + `scripts/ocr_macos.swift` | Find text in a screenshot (macOS Vision, tesseract fallback, cache) |
| `scripts/device_geometry.py` | Python port of `deviceGeometry()` for the legibility gate (parity-tested) |
| `remotion/src/runtime/device.tsx` | `deviceGeometry()`, `defaultLook()`, `isTouch()`, `alpha()`, `<Device>` |
| `remotion/src/runtime/screen.tsx` | `<ScreenImage>`, `<ScreenVideo>`, `scrollRangePx()`, `flingAt()` |
| `remotion/src/runtime/gesture.tsx` | `typeChunks()`, `typedCount()`, `caretOn()`, `framesBetween()`, `<TapRipple>`, `<CursorArrow>` |
| `remotion/src/shots/DeviceDemo.tsx`, `DeviceHero.tsx` | The two registers |
| `remotion/cards/DeviceDemo.md`, `DeviceHero.md` | Their shot cards |
| `scripts/render_remotion.py` | `resolve_cue_props` resolves lists of timed items in order; `build_scenes` calls `device_script.prepare` |
| `scripts/validate.py` | `_check_remotion` reports device-script errors and warnings per beat |
| `remotion/src/shots/CommandSummon.tsx`, `TermTable.tsx` | Adopt the shared caret |
| `tests/_tsprobe.py` | Shared helper: run a TS snippet against the real runtime in node |
| `tests/test_device_script.py`, `test_cue_lists.py`, `test_screen_media.py`, `test_screen_text.py`, `test_device_runtime.py`, `test_caret.py`, `test_device_demo.py`, `test_device_hero.py`, `test_device_wiring.py` | Tests, one file per task |

---

### Task 1: The numbers and the schedule

**Files:**
- Create: `remotion/src/runtime/deviceSpec.json`
- Create: `scripts/device_script.py`
- Test: `tests/test_device_script.py`

**Interfaces:**
- Consumes: `render_remotion.frame_at_t(durF, t)`, `render_remotion.t_at_seconds(sec, durF, fps)`, `render_remotion.ENTRY_T` (existing).
- Produces: `device_script.SPEC` (dict of deviceSpec.json); `DeviceScriptError(problems: list[str])` with `.problems`; `type_chunks(value: str | list) -> list[str]`; `step_kind(step: dict) -> str`; `gesture_seconds(step) -> float`; `needs_lead(step) -> bool`; `check_shape(props: dict) -> list[str]`; `schedule_seconds(steps, anchors_s: list[float|None], start_s, end_s) -> list[tuple[t0, ta, t1]]`; `schedule(steps, dur_frames: int, fps: int) -> list[dict]` (each step gains `t0`, `ta`, `t1` in useT time).

- [ ] **Step 1: Write the spec file**

`remotion/src/runtime/deviceSpec.json`:

```json
{
  "_doc": "The device layer's numbers, defined ONCE. Read by runtime/device.tsx, runtime/screen.tsx and runtime/gesture.tsx, and by scripts/device_script.py, scripts/device_geometry.py and scripts/screen_media.py. Values come from docs/superpowers/specs/2026-09-26-device-layer-design.md and the rulings in docs/superpowers/plans/2026-09-26-device-layer.md; the durations and caps are design choices to tune on real films, not measurements.",
  "screenRatio": {"phone": [9, 19.5], "tablet": [3, 4], "laptop": [16, 10], "monitor": [16, 9]},
  "touch": {"phone": true, "tablet": true, "laptop": false, "monitor": false},
  "body": {
    "flat": {
      "phone":   {"bezel": 0.045, "radius": 0.13,  "base": 0,     "overhang": 0,    "strip": 0},
      "tablet":  {"bezel": 0.04,  "radius": 0.05,  "base": 0,     "overhang": 0,    "strip": 0},
      "laptop":  {"bezel": 0.022, "radius": 0.012, "base": 0.035, "overhang": 0.06, "strip": 0},
      "monitor": {"bezel": 0.018, "radius": 0.01,  "base": 0.16,  "overhang": 0,    "strip": 0}
    },
    "real": {
      "phone":   {"bezel": 0.045, "radius": 0.13,  "base": 0,     "overhang": 0,    "strip": 0},
      "tablet":  {"bezel": 0.04,  "radius": 0.05,  "base": 0,     "overhang": 0,    "strip": 0},
      "laptop":  {"bezel": 0.022, "radius": 0.012, "base": 0.035, "overhang": 0.06, "strip": 0},
      "monitor": {"bezel": 0.018, "radius": 0.01,  "base": 0.16,  "overhang": 0,    "strip": 0}
    },
    "screen": {
      "phone":   {"bezel": 0, "radius": 0.11,  "base": 0, "overhang": 0, "strip": 0},
      "tablet":  {"bezel": 0, "radius": 0.045, "base": 0, "overhang": 0, "strip": 0},
      "laptop":  {"bezel": 0, "radius": 0.012, "base": 0, "overhang": 0, "strip": 0.045},
      "monitor": {"bezel": 0, "radius": 0.012, "base": 0, "overhang": 0, "strip": 0.04}
    }
  },
  "island": {"w": 0.30, "h": 0.052, "top": 0.035},
  "zoneTopFrac": 0.05,
  "zoneWidthFill": 0.9,
  "placementX": {"center": 0.5, "left": 0.32, "right": 0.68},
  "minSeconds": {"screen": 0.5, "tap": 0.6, "click": 0.6, "typeLatinKey": 0.15, "typeCjkWord": 0.35,
                 "scroll": 0.9, "drag": 0.9, "mark": 0.6},
  "cameraLeadSeconds": 0.35,
  "maxZoom": 4.0,
  "maxVideoRate": 2.0,
  "caretPhaseFrames": 16,
  "aspectTolerance": 0.04
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_device_script.py`:

```python
"""The step script of a device beat: its shape, how long each step needs, and when each one happens.

A schedule that silently squeezes steps into a beat too short for them draws a tap before the finger could
have arrived and a word the voice has not reached. So every refusal here must say, in SECONDS, what is
missing — an author fixes a script from the message, not from the code.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import device_script as ds          # noqa: E402

FPS = 30


def _steps(*kinds):
    table = {"screen": {"screen": {"image": "ui/a.png"}}, "tap": {"tap": [0.5, 0.4]},
             "type": {"type": "abc", "into": [0.5, 0.1]}, "scroll": {"scroll": 0.5}}
    return [dict(table[k]) for k in kinds]


def test_latin_types_a_key_at_a_time_and_cjk_a_two_glyph_word():
    assert ds.type_chunks("ab c") == ["a", "b", " ", "c"]
    assert ds.type_chunks("上周的客户反馈") == ["上周", "的客", "户反", "馈"]
    assert ds.type_chunks("上周 AI") == ["上周", " ", "A", "I"]
    assert ds.type_chunks(["上周", "的", "客户"]) == ["上周", "的", "客户"]


def test_each_kind_needs_its_own_time():
    assert ds.gesture_seconds({"tap": [0.5, 0.5]}) == pytest.approx(0.6)
    assert ds.gesture_seconds({"type": "abc", "into": [0.5, 0.1]}) == pytest.approx(0.45)
    assert ds.gesture_seconds({"type": ["上周", "反馈"], "into": [0.5, 0.1]}) == pytest.approx(0.70)
    assert ds.needs_lead({"tap": [0.5, 0.5]}) and not ds.needs_lead({"screen": {"image": "x.png"}})


@pytest.mark.parametrize("props,needle", [
    ({"steps": [{"tap": [0.5, 0.5]}]}, "step 1 must be a `screen`"),
    ({"steps": [{"screen": {"image": "a.png"}, "tap": [0.5, 0.5]}]}, "exactly one of"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": [1.2, 0.5]}]}, "in 0..1"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"mark": [0.5, 0.5]}]}, "`mark` is for recordings"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"scroll": 0}]}, "`scroll` is a fraction"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"type": "abc"}]}, "needs `into`"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": {"text": "设置", "nth": 0}}]}, "`nth` counts from 1"),
    ({"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "colour": "red"}]}, "has no key `colour`"),
    ({"device": "watch", "steps": [{"screen": {"image": "a.png"}}]}, "`device`"),
    ({"steps": [{"screen": {"image": "a.png", "video": "b.mp4"}}]}, "exactly one of image / video / page"),
])
def test_a_malformed_script_is_refused_with_its_reason(props, needle):
    probs = ds.check_shape(props)
    assert any(needle in p for p in probs), probs


def test_a_well_formed_script_has_no_problems():
    props = {"device": "phone", "look": "real", "steps": [
        {"screen": {"image": "ui/a.png"}}, {"type": "abc", "into": [0.5, 0.1]},
        {"tap": {"text": "反馈汇总"}}, {"screen": {"image": "ui/b.png"}, "via": "push"}, {"scroll": 0.6}]}
    assert ds.check_shape(props) == []


def test_unanchored_steps_are_spread_in_order_inside_the_beat():
    out = ds.schedule(_steps("screen", "tap", "type", "tap"), 180, FPS)
    t0s = [s["t0"] for s in out]
    assert t0s == sorted(t0s)
    assert all(s["t0"] <= s["ta"] <= s["t1"] for s in out)
    assert out[0]["t0"] == pytest.approx(0.06, abs=1e-3)           # the device arrives when the shot does
    assert out[-1]["t1"] <= 1.0


def test_an_anchored_step_acts_exactly_on_its_cue():
    steps = _steps("screen", "tap", "tap")
    steps[2]["at"] = 0.7
    out = ds.schedule(steps, 180, FPS)
    assert out[2]["ta"] == pytest.approx(0.7, abs=2e-3)
    assert out[1]["t1"] <= out[2]["t0"] + 1e-6                        # the earlier step finishes first


def test_a_short_beat_says_how_much_time_is_missing():
    # 12 taps cannot fit a 2-second beat: 12 x (0.35 lead + 0.6) = 11.4 s
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.schedule(_steps("screen", *["tap"] * 12), 60, FPS)
    msg = str(e.value)
    assert "needs" in msg and " s" in msg and "beat" in msg, msg


def test_an_anchor_that_arrives_before_the_steps_before_it_can_finish_is_an_error():
    steps = _steps("screen", "tap", "tap", "tap")
    steps[3]["at"] = 0.12                                               # too early for two taps before it
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.schedule(steps, 180, FPS)
    assert "step 4" in str(e.value) and "cue" in str(e.value)
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_device_script.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'device_script'`.

- [ ] **Step 4: Implement `scripts/device_script.py`**

```python
#!/usr/bin/env python3
"""The step script of a device beat — what a step IS and WHEN it happens, in one place.

A DeviceDemo beat is a list of steps (docs/superpowers/specs/2026-09-26-device-layer-design.md §3): show a
screen, type into a field, tap, scroll, drag, mark a point on a recording. This module owns the shape of a
step, how long each kind needs, and the schedule that places every step on the beat. validate.py and
render_remotion.py both call it, so the error a validate run prints and the schedule a render uses are the
same computation, and the register draws the schedule it is given rather than inventing one.

The numbers live in remotion/src/runtime/deviceSpec.json, which the TypeScript reads too.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(_HERE, "..", "remotion", "src", "runtime", "deviceSpec.json")

STEP_KINDS = ("screen", "type", "tap", "click", "scroll", "drag", "mark")
GESTURES = ("type", "tap", "click", "scroll", "drag", "mark")
DEVICE_KINDS = ("phone", "tablet", "laptop", "monitor")
LOOKS = ("flat", "real", "screen")
VIAS = ("push", "fade")
PLACEMENTS = ("center", "left", "right")
ALLOWED = {"screen": {"screen", "via", "at"}, "type": {"type", "into", "at"}, "tap": {"tap", "at"},
           "click": {"click", "at"}, "scroll": {"scroll", "at"}, "drag": {"drag", "at"},
           "mark": {"mark", "at", "video"}}
_CJK = re.compile(r"[㐀-鿿豈-﫿぀-ヿ가-힯]")

with open(SPEC_PATH, encoding="utf-8") as _fh:
    SPEC = json.load(_fh)


class DeviceScriptError(ValueError):
    """Every problem found, not just the first — a script is fixed in one pass, not five."""

    def __init__(self, problems):
        self.problems = [str(p) for p in problems]
        super().__init__("\n".join(self.problems))


def type_chunks(value):
    """The keystrokes of a `type` step: Latin one character each, CJK a two-glyph word each (an input method
    commits words and the runtime has no segmenter), or exactly the author's own list. runtime/gesture.tsx
    `typeChunks` is the same function; tests/test_device_runtime.py holds them together."""
    if isinstance(value, list):
        return [str(v) for v in value if str(v)]
    out, run = [], ""
    for ch in str(value or ""):
        if _CJK.match(ch):
            run += ch
            if len(run) == 2:
                out.append(run)
                run = ""
        else:
            if run:
                out.append(run)
                run = ""
            out.append(ch)
    if run:
        out.append(run)
    return out


def step_kind(step):
    kinds = [k for k in STEP_KINDS if isinstance(step, dict) and k in step]
    return kinds[0] if len(kinds) == 1 else ""


def gesture_seconds(step):
    """How long the step's own action takes — without the camera's lead."""
    k, ms = step_kind(step), SPEC["minSeconds"]
    if k == "type":
        return sum(ms["typeCjkWord"] if _CJK.search(c) else ms["typeLatinKey"] for c in type_chunks(step["type"]))
    return float(ms[k])


def needs_lead(step):
    return step_kind(step) in GESTURES


def _target_problem(t, where):
    if isinstance(t, (list, tuple)):
        if len(t) == 2 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in t):
            return None
        return "%s: a position is [x, y] with both in 0..1 of the screen (got %r)" % (where, t)
    if isinstance(t, dict) and set(t) <= {"text", "nth"} and str(t.get("text", "")).strip():
        n = t.get("nth")
        if n is None or (isinstance(n, int) and n >= 1):
            return None
        return "%s: `nth` counts from 1 (got %r)" % (where, n)
    return "%s: a target is [x, y] or {\"text\": ..., \"nth\": n} (got %r)" % (where, t)


def check_shape(props):
    """Every shape problem in an AUTHORED script, as sentences. [] means it is well formed."""
    probs = []
    if props.get("device", "phone") not in DEVICE_KINDS:
        probs.append("`device` is one of %s (got %r)" % (", ".join(DEVICE_KINDS), props.get("device")))
    if props.get("look") is not None and props["look"] not in LOOKS:
        probs.append("`look` is one of %s (got %r)" % (", ".join(LOOKS), props["look"]))
    if props.get("camera") not in (None, "still"):
        probs.append("`camera` is absent or \"still\" (got %r)" % (props.get("camera"),))
    if props.get("placement", "center") not in PLACEMENTS:
        probs.append("`placement` is one of %s (got %r)" % (", ".join(PLACEMENTS), props.get("placement")))
    steps = props.get("steps")
    if not isinstance(steps, list) or not steps:
        return probs + ["`steps` must be a non-empty list — the script of what happens on the device"]
    on_video = False
    for i, st in enumerate(steps, 1):
        where = "step %d" % i
        if not isinstance(st, dict):
            probs.append("%s is not an object" % where)
            continue
        kinds = [k for k in STEP_KINDS if k in st]
        if len(kinds) != 1:
            probs.append("%s: exactly one of %s (got %s)" % (where, ", ".join(STEP_KINDS), kinds or "none"))
            continue
        k = kinds[0]
        for extra in sorted(set(st) - ALLOWED[k]):
            probs.append("%s (%s) has no key `%s` — it takes %s" % (where, k, extra, ", ".join(sorted(ALLOWED[k]))))
        if i == 1 and k != "screen":
            probs.append("step 1 must be a `screen` — the device would arrive showing nothing")
        if k == "screen":
            src = st["screen"]
            srcs = [s for s in ("image", "video", "page") if isinstance(src, dict) and s in src]
            if len(srcs) != 1:
                probs.append("%s: a screen is exactly one of image / video / page (got %r)" % (where, src))
                continue
            on_video = srcs[0] == "video"
            if st.get("via") not in (None,) + VIAS:
                probs.append("%s: `via` is %s (got %r)" % (where, " or ".join(VIAS), st.get("via")))
            if on_video:
                a, b = src.get("from", 0), src.get("to")
                if not isinstance(a, (int, float)) or a < 0 or not isinstance(b, (int, float)) or b <= a:
                    probs.append("%s: a recording needs `from` >= 0 and `to` > `from`, in seconds (got %r, %r)"
                                 % (where, a, b))
        elif k == "type":
            if not type_chunks(st["type"]):
                probs.append("%s: `type` has nothing to type" % where)
            if "into" not in st:
                probs.append("%s: `type` needs `into` — the field it types into" % where)
            else:
                p = _target_problem(st["into"], where + " `into`")
                probs.extend([p] if p else [])
        elif k in ("tap", "click", "mark"):
            p = _target_problem(st[k], where)
            probs.extend([p] if p else [])
            if k == "mark" and not on_video:
                probs.append("%s: `mark` is for recordings — a screenshot is tapped, not marked" % where)
            if k == "mark" and "video" in st and not isinstance(st["video"], (int, float)):
                probs.append("%s: `video` is the recording's moment in seconds (got %r)" % (where, st["video"]))
        elif k == "scroll":
            v = st["scroll"]
            if not isinstance(v, (int, float)) or not 0 < v <= 1:
                probs.append("%s: `scroll` is a fraction of the long screenshot's overflow, in (0, 1] (got %r)"
                             % (where, v))
        elif k == "drag":
            d = st["drag"]
            if not isinstance(d, dict) or set(d) != {"from", "to"}:
                probs.append("%s: `drag` is {\"from\": target, \"to\": target} (got %r)" % (where, d))
            else:
                for end in ("from", "to"):
                    p = _target_problem(d[end], "%s `drag.%s`" % (where, end))
                    probs.extend([p] if p else [])
        if "at" in st and not isinstance(st["at"], (dict, int, float)):
            probs.append("%s: `at` is {\"cue\": words the narration says} (got %r)" % (where, st["at"]))
    return probs


def _names(steps, idx):
    return ", ".join("step %d (%s)" % (i + 1, step_kind(steps[i])) for i in idx)


def schedule_seconds(steps, anchors, start_s, end_s):
    """[(t0, ta, t1)] in seconds from the clip start: when each step's window opens, when it acts, when it
    ends. Anchored steps act exactly on their anchor; the unanchored ones between anchors are spread evenly
    in the room the anchors leave. Raises DeviceScriptError, in seconds, when the room is not there."""
    lead = float(SPEC["cameraLeadSeconds"])
    pre = [lead if needs_lead(s) else 0.0 for s in steps]
    act = [gesture_seconds(s) for s in steps]
    n, out, cursor, i = len(steps), [None] * len(steps), float(start_s), 0
    while i < n:
        j = i
        while j < n and anchors[j] is None:
            j += 1
        run = list(range(i, j))
        limit = (anchors[j] - pre[j]) if j < n else float(end_s)
        need = sum(pre[k] + act[k] for k in run)
        slack = limit - cursor - need
        if slack < -1e-6:
            if j < n:
                raise DeviceScriptError(["%s need%s %.1f s before step %d's cue, which the narration reaches "
                                         "%.1f s into the beat — only %.1f s are left for them"
                                         % (_names(steps, run) or "the camera", "" if len(run) != 1 else "s",
                                            need + pre[j], j + 1, anchors[j], max(0.0, anchors[j] - cursor))])
            raise DeviceScriptError(["the script needs %.1f s for %s but the beat has %.1f s left"
                                     % (need, _names(steps, run), max(0.0, end_s - cursor))])
        slots = len(run) + (0 if i == 0 else 1)
        gap = slack / slots if run and slots else 0.0
        pos = cursor + (0.0 if i == 0 else gap)
        for k in run:
            out[k] = (pos, pos + pre[k], pos + pre[k] + act[k])
            pos = out[k][2] + gap
        if j < n:
            out[j] = (anchors[j] - pre[j], anchors[j], anchors[j] + act[j])
            cursor = out[j][2]
            if cursor > end_s + 1e-6:
                raise DeviceScriptError(["step %d (%s) acts on its cue %.1f s into the beat and needs %.1f s, "
                                         "but the beat ends at %.1f s" % (j + 1, step_kind(steps[j]), anchors[j],
                                                                          act[j], end_s)])
            i = j + 1
        else:
            i = j
    return out


def schedule(steps, dur_frames, fps):
    """The steps with `t0`, `ta`, `t1` in useT time. A step's `at`, if present, is ALREADY a useT time —
    render_remotion.resolve_cue_props turned the cue into one."""
    import render_remotion as rr
    start_s = rr.frame_at_t(dur_frames, rr.ENTRY_T) / float(fps)
    end_s = rr.frame_at_t(dur_frames, 1.0) / float(fps)
    anchors = [rr.frame_at_t(dur_frames, float(s["at"])) / float(fps) if isinstance(s.get("at"), (int, float))
               else None for s in steps]
    windows = schedule_seconds(steps, anchors, start_s, end_s)
    out = []
    for s, (a, b, c) in zip(steps, windows):
        d = dict(s)
        d["t0"], d["ta"], d["t1"] = (rr.t_at_seconds(x, dur_frames, fps) for x in (a, b, c))
        out.append(d)
    return out
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest tests/test_device_script.py -q`
Expected: all pass. If `test_an_anchored_step_acts_exactly_on_its_cue` is off by more than 2e-3, the `frame_at_t` / `t_at_seconds` round trip is the cause — print both values and compare against `render_remotion.t_at_seconds`'s 4-decimal rounding before changing the scheduler.

- [ ] **Step 6: Commit**

```bash
git add remotion/src/runtime/deviceSpec.json scripts/device_script.py tests/test_device_script.py
git commit -m "Device layer: the step script's shape, per-kind time and schedule, in one module

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 2: Cues inside a list resolve in order

**Files:**
- Modify: `scripts/render_remotion.py` (`resolve_cue_props`)
- Test: `tests/test_cue_lists.py`

**Interfaces:**
- Consumes: `cues._anchor_pos(narration, anchor, start)`, `cues._find(words, phrase, start)`, `cues.resolve_cues(words, anchors)`, `cues.estimate_cues_from_text(anchors, narration, duration)`, `render_remotion.t_at_seconds` (all existing).
- Produces: `resolve_cue_props(props, out_dir, audio, narration, dur_s, fps)` now also resolves every top-level LIST whose items are objects carrying `at: {"cue": ...}` — in order, one search — and raises `SystemExit` naming `prop[i].at` for a cue the narration does not say or says only before the previous item's cue. Top-level cue props behave exactly as before.

- [ ] **Step 1: Write the failing tests**

`tests/test_cue_lists.py`:

```python
"""Cues inside a list resolve in ORDER — a script's steps, a chat thread's messages.

`resolve_cue_props` used to resolve only top-level props, each searched from the start of the narration. A
list of timed items needs one ordered search: a phrase said twice must land on two successive items, and a
cue the narration reaches only before the previous item's is an error, not a silent swap.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import render_remotion as rr        # noqa: E402

FPS = 30


def _resolve(props, narration, tmp_path, words=None, dur=6.0):
    (tmp_path / "audio").mkdir(exist_ok=True)
    if words is not None:
        (tmp_path / "audio" / "01.words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return rr.resolve_cue_props(props, str(tmp_path), "audio/01.mp3", narration, dur, FPS)


def test_items_resolve_in_the_order_the_voice_says_them(tmp_path):
    props = {"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "at": {"cue": "搜索"}},
                       {"tap": [0.5, 0.6], "at": {"cue": "点开"}}]}
    out = _resolve(props, "先在上面搜索上周的反馈，然后点开第一条。", tmp_path)
    a, b = out["steps"][1]["at"], out["steps"][2]["at"]
    assert isinstance(a, float) and isinstance(b, float) and a < b
    assert "at" not in out["steps"][0]


def test_a_repeated_phrase_lands_on_successive_items(tmp_path):
    words = [{"w": w, "t": t} for w, t in [("点", 0.4), ("这里", 0.6), ("然后", 1.4), ("再", 2.0), ("点", 2.6),
                                            ("这里", 2.8)]]
    props = {"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.2, 0.2], "at": {"cue": "点这里"}},
                       {"tap": [0.8, 0.8], "at": {"cue": "点这里"}}]}
    out = _resolve(props, "点这里，然后再点这里。", tmp_path, words=words)
    a, b = out["steps"][1]["at"], out["steps"][2]["at"]
    assert b > a + 0.2, "both items bound to the first 点这里: %r %r" % (a, b)


def test_a_cue_said_only_before_the_previous_one_is_an_error(tmp_path):
    props = {"steps": [{"screen": {"image": "a.png"}}, {"tap": [0.5, 0.5], "at": {"cue": "点开"}},
                       {"tap": [0.5, 0.6], "at": {"cue": "搜索"}}]}
    with pytest.raises(SystemExit) as e:
        _resolve(props, "先搜索，再点开。", tmp_path)
    assert "steps[2].at" in str(e.value) and "BEFORE" in str(e.value)


def test_a_cue_the_narration_never_says_names_the_item(tmp_path):
    props = {"messages": [{"side": "you", "text": "hi", "at": {"cue": "不存在的话"}}]}
    with pytest.raises(SystemExit) as e:
        _resolve(props, "这里什么都没说。", tmp_path)
    assert "messages[0].at" in str(e.value)


def test_top_level_cues_are_unchanged(tmp_path):
    out = _resolve({"turnAt": {"cue": "工作中"}}, "它现在是绿色的工作中状态。", tmp_path)
    assert isinstance(out["turnAt"], float)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_cue_lists.py -q`
Expected: the list tests FAIL (the `at` dicts come back unresolved); `test_top_level_cues_are_unchanged` PASSES.

- [ ] **Step 3: Replace `resolve_cue_props` in `scripts/render_remotion.py`**

Replace the whole function (from `def resolve_cue_props(` to its `return out`) with:

```python
def resolve_cue_props(props, out_dir, audio, narration, dur_s, fps):
    """A prop written `{"cue": "<words the narration says>"}` becomes the `t` at which the voice says them.

    WHY. A register that changes state at a fixed fraction of its clip changes it at a moment that has nothing
    to do with the sentence over it. Measured on a delivered film: CompanionCard turned its card grey at ~19.9s
    while the voice was still saying 「绿色的工作中」 (20.5-21.7s) — for a second the frame said 等待中 under a
    sentence saying 工作中. The timing belongs to the narration, and the narration's own word times are on disk
    (tts.py writes `audio/NN.words.json`), so the board names the WORDS and this puts the event on them. Without
    word times the position is estimated from the narration text, the same fallback the html tier's cues use.
    `{"cue": ..., "offset": seconds}` shifts it. An anchor the narration does not contain is an ERROR — landing
    it anywhere would be exactly the guess this exists to remove.

    LISTS OF TIMED ITEMS resolve IN ORDER. A prop that is a list of objects carrying `at: {"cue": ...}` — a
    device script's steps, a chat thread's messages — is ONE ordered search: each cue is looked for after the
    previous one's match, so a phrase the narration says twice lands on two successive items, and a cue the
    narration reaches only BEFORE the previous item's is an error rather than a silent swap."""
    def is_cue(v):
        return isinstance(v, dict) and "cue" in v and set(v) <= {"cue", "offset"}

    def timed_list(v):
        return isinstance(v, list) and any(isinstance(x, dict) and is_cue(x.get("at")) for x in v)

    if not any(is_cue(v) or timed_list(v) for v in (props or {}).values()):
        return props
    import cues as _cues
    words = []
    if audio:
        wj = os.path.splitext(os.path.join(out_dir, audio))[0] + ".words.json"
        if os.path.exists(wj):
            try:
                words = json.load(open(wj, encoding="utf-8"))
            except (OSError, ValueError):
                words = []
    dur_frames = round(dur_s * fps)
    out = dict(props)
    for k, v in props.items():
        if is_cue(v):
            phrase = str(v["cue"] or "").strip()
            if not phrase or _cues._anchor_pos(narration or "", phrase) < 0:
                raise SystemExit("[render_remotion] shot prop `%s` cues %r, which this beat's narration does not say "
                                 "— name words the voice actually speaks" % (k, phrase))
            if words and _cues._find(words, phrase, 0) >= 0:
                sec = _cues.resolve_cues(words, [phrase])[0]
            else:
                sec = _cues.estimate_cues_from_text([phrase], narration or "", dur_s)[0]
            sec += float(v.get("offset") or 0.0)
            out[k] = t_at_seconds(sec, dur_frames, fps)
        elif timed_list(v):
            items = [dict(x) if isinstance(x, dict) else x for x in v]
            idx = [i for i, x in enumerate(items) if isinstance(x, dict) and is_cue(x.get("at"))]
            phrases, pos = [], 0
            for i in idx:
                phrase = str(items[i]["at"].get("cue") or "").strip()
                if not phrase or _cues._anchor_pos(narration or "", phrase) < 0:
                    raise SystemExit("[render_remotion] shot prop `%s[%d].at` cues %r, which this beat's narration "
                                     "does not say — name words the voice actually speaks" % (k, i, phrase))
                p = _cues._anchor_pos(narration or "", phrase, pos)
                if p < 0:
                    raise SystemExit("[render_remotion] shot prop `%s[%d].at` cues %r, but the narration says it only "
                                     "BEFORE the previous item's cue — the items would play out of order. Reorder "
                                     "them, or cue a phrase said later" % (k, i, phrase))
                pos = p + len(phrase)
                phrases.append(phrase)
            if words and all(_cues._find(words, p, 0) >= 0 for p in phrases):
                secs = _cues.resolve_cues(words, phrases)
            else:
                secs = _cues.estimate_cues_from_text(phrases, narration or "", dur_s)
            for i, sec in zip(idx, secs):
                sec += float(items[i]["at"].get("offset") or 0.0)
                items[i]["at"] = t_at_seconds(sec, dur_frames, fps)
            out[k] = items
    return out
```

- [ ] **Step 4: Run the new and the existing cue tests**

Run: `python3 -m pytest tests/test_cue_lists.py -q && python3 -m pytest tests -q -k "cue" -p no:cacheprovider`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/render_remotion.py tests/test_cue_lists.py
git commit -m "Cues inside a list resolve in order: a phrase said twice lands on two items, a swap is an error

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 3: What a screenshot or recording is — measured

**Files:**
- Create: `scripts/screen_media.py`
- Test: `tests/test_screen_media.py`

**Interfaces:**
- Consumes: `device_script.SPEC`, `device_script.DeviceScriptError`; `_caption_band.caption_size_px(w, h)` (existing).
- Produces: `image_facts(path) -> {"w", "h"}`; `fit_kind(facts, device) -> "fit" | "long"` (raises `DeviceScriptError` when wider); `video_facts(path) -> {"duration", "fps", "w", "h"}`; `check_video(facts, device, frm, to) -> list[str]`; `text_band_px(path, x, y) -> float | None` (ink-band height in SOURCE pixels at image fractions x, y); `field_at(path, x, y) -> {"box": [x0,y0,x1,y1] (image fractions), "bg": "#rrggbb", "ink": "#rrggbb", "textPx": float|None}`; `caption_ink_px(lang, W, H) -> float`.

- [ ] **Step 1: Write the failing tests**

`tests/test_screen_media.py`:

```python
"""A screenshot's facts are read from the file. Light AND dark screenshots, because every constant here is a
threshold that a dark UI turns upside down."""
import os
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import device_script as ds          # noqa: E402
import screen_media as sm           # noqa: E402

FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")


def _shot(path, w=1170, h=2532, bg=(255, 255, 255), ink=(20, 23, 28), field=None, lines=()):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    if field:
        (x0, y0, x1, y1), fcol = field
        d.rounded_rectangle([x0, y0, x1, y1], radius=int((y1 - y0) * 0.3), fill=fcol)
    for (x, y, text, px) in lines:
        d.text((x, y), text, fill=ink, font=ImageFont.truetype(FONT, px))
    im.save(path)
    return path


def test_an_android_screenshot_fits_a_phone(tmp_path):
    assert sm.fit_kind({"w": 1080, "h": 2400}, "phone") == "fit"          # 2.6% taller: inside the 4%


def test_a_long_screenshot_is_long_and_a_wide_one_is_refused():
    assert sm.fit_kind({"w": 1170, "h": 6000}, "phone") == "long"
    with pytest.raises(ds.DeviceScriptError) as e:
        sm.fit_kind({"w": 2560, "h": 1600}, "phone")
    assert "wider" in str(e.value)


def test_text_height_is_the_ink_band_under_the_point(tmp_path):
    p = _shot(str(tmp_path / "a.png"), lines=[(80, 600, "发票下载失败", 48), (80, 760, "搜索结果不准确", 48)])
    h = sm.text_band_px(p, 0.2, (600 + 30) / 2532)
    assert h is not None and 35 <= h <= 60, h


def test_dark_mode_text_and_field(tmp_path):
    p = _shot(str(tmp_path / "d.png"), bg=(12, 14, 20), ink=(236, 239, 244),
              field=((60, 300, 1110, 420), (38, 42, 52)), lines=[(110, 330, "搜索反馈", 44), (80, 700, "设置", 48)])
    assert sm.text_band_px(p, 0.1, (700 + 30) / 2532) is not None
    f = sm.field_at(p, 0.5, 360 / 2532)
    x0, y0, x1, y1 = f["box"]
    assert abs(x0 - 60 / 1170) < 0.03 and abs(x1 - 1110 / 1170) < 0.03, f
    assert abs(y0 - 300 / 2532) < 0.01 and abs(y1 - 420 / 2532) < 0.01, f
    assert f["ink"] == "#ffffff" and f["textPx"] is not None


def test_a_light_field_on_a_white_page(tmp_path):
    p = _shot(str(tmp_path / "l.png"), field=((60, 300, 1110, 420), (238, 241, 244)),
              lines=[(110, 330, "搜索反馈", 44)])
    f = sm.field_at(p, 0.5, 360 / 2532)
    assert abs(f["box"][0] - 60 / 1170) < 0.03 and abs(f["box"][2] - 1110 / 1170) < 0.03, f
    assert f["ink"] == "#111111"


def test_caption_ink_is_measured_from_the_bundled_face():
    zh, en = sm.caption_ink_px("zh", 1920, 1080), sm.caption_ink_px("en", 1920, 1080)
    assert 25 < zh < 60 and 20 < en < 60, (zh, en)


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="needs ffmpeg")
def test_a_recording_is_probed_and_its_limits_checked(tmp_path):
    v = str(tmp_path / "r.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=390x844:rate=30",
                    "-t", "4", "-pix_fmt", "yuv420p", v], check=True)
    f = sm.video_facts(v)
    assert abs(f["duration"] - 4) < 0.1 and f["w"] == 390 and f["h"] == 844
    assert sm.check_video(f, "phone", 0, 3) == []
    assert any("longer than" in p for p in sm.check_video(f, "phone", 0, 9))
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_screen_media.py -q`
Expected: `ModuleNotFoundError: No module named 'screen_media'`.

- [ ] **Step 3: Implement `scripts/screen_media.py`**

```python
#!/usr/bin/env python3
"""What a screenshot or a recording IS — read from the file, never declared.

The device layer (docs/superpowers/specs/2026-09-26-device-layer-design.md) puts a user's own screenshots and
recordings inside a drawn device. Everything it needs to know about them is measured here: a screenshot's
size and whether it is a long one, a recording's length and frame rate, how tall the text is at a point (the
legibility push-in), what a text field under a point looks like (so typing can paint over its placeholder),
and how tall the film's own caption glyphs are (the height a target's text must reach).
"""
import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import device_script as ds
from _caption_band import caption_size_px

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONTS = {"zh": os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf"),
          "latin": os.path.join(_ROOT, "assets", "fonts", "Inter-VF.ttf")}
_SAMPLE = {"zh": "字幕", "latin": "Caption"}
INK_DELTA = 40        # grey levels from the local background that count as glyph ink
FIELD_TOL = 8         # per-channel tolerance that still counts as the field's own background


def image_facts(path):
    with Image.open(path) as im:
        return {"w": int(im.width), "h": int(im.height)}


def _screen_aspect(device):
    rw, rh = ds.SPEC["screenRatio"][device]
    return float(rw) / float(rh)


def fit_kind(facts, device):
    """"fit" (within the tolerance of the screen's proportion), "long" (taller: it scrolls), or an error."""
    a, s, tol = facts["w"] / float(facts["h"]), _screen_aspect(device), float(ds.SPEC["aspectTolerance"])
    if a > s * (1 + tol):
        raise ds.DeviceScriptError(["a %dx%d screenshot is wider than a %s screen allows (%.3f against %.3f) — it "
                                    "is a capture of a different device" % (facts["w"], facts["h"], device, a, s)])
    return "long" if a < s * (1 - tol) else "fit"


def video_facts(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise ds.DeviceScriptError(["cannot read the recording %s: %s" % (path, r.stderr.strip()[-200:])])
    d = json.loads(r.stdout)
    st = (d.get("streams") or [{}])[0]
    num, _, den = str(st.get("r_frame_rate", "30/1")).partition("/")
    return {"duration": float(d.get("format", {}).get("duration", 0.0)),
            "fps": float(num) / float(den or 1), "w": int(st.get("width", 0)), "h": int(st.get("height", 0))}


def check_video(facts, device, frm, to):
    probs = []
    a, s, tol = facts["w"] / float(max(1, facts["h"])), _screen_aspect(device), float(ds.SPEC["aspectTolerance"])
    if abs(a - s) > s * tol:
        probs.append("a %dx%d recording does not have a %s screen's proportion (%.3f against %.3f)"
                     % (facts["w"], facts["h"], device, a, s))
    if to > facts["duration"] + 1e-3:
        probs.append("`to` %.2f s is longer than the recording (%.2f s)" % (to, facts["duration"]))
    if frm < 0 or frm >= to:
        probs.append("`from` %.2f s must be >= 0 and before `to` %.2f s" % (frm, to))
    return probs


def _lum(path):
    return np.asarray(Image.open(path).convert("L"), dtype=float)


def _runs(rows):
    if not len(rows):
        return []
    out, start, prev = [], rows[0], rows[0]
    for r in rows[1:]:
        if r - prev > 2:
            out.append((start, prev))
            start = r
        prev = r
    out.append((start, prev))
    return out


def text_band_px(path, x, y, box=None):
    """Height in SOURCE pixels of the line of text at image fractions (x, y): the contiguous band of rows
    holding glyph ink near that point, in a window around it (or inside `box`, image fractions)."""
    a = _lum(path)
    H, W = a.shape
    cx, cy = int(round(x * (W - 1))), int(round(y * (H - 1)))
    if box:
        x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
    else:
        x0, x1 = max(0, cx - int(W * 0.12)), min(W, cx + int(W * 0.12) + 1)
        y0, y1 = max(0, cy - int(H * 0.15)), min(H, cy + int(H * 0.15) + 1)
    win = a[y0:y1, x0:x1]
    if win.size == 0:
        return None
    bg = float(np.median(win))
    runs = [r for r in _runs(np.flatnonzero((np.abs(win - bg) > INK_DELTA).any(axis=1))) if r[1] - r[0] >= 2]
    if not runs:
        return None
    ty = cy - y0
    best = min(runs, key=lambda r: 0 if r[0] <= ty <= r[1] else min(abs(ty - r[0]), abs(ty - r[1])))
    return float(best[1] - best[0] + 1)


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb[:3])


def field_at(path, x, y):
    """The text field under image fractions (x, y): its box, its background, the ink that reads on it, and the
    height of any text already in it. Grown outward while each new row/column is mostly the field's colour —
    placeholder glyphs occupy a minority of any row or column that crosses them."""
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    H, W, _ = rgb.shape
    cx, cy = int(round(x * (W - 1))), int(round(y * (H - 1)))
    patch = rgb[max(0, cy - 3):cy + 4, max(0, cx - 3):cx + 4].reshape(-1, 3)
    bg = np.median(patch, axis=0)
    same = (np.abs(rgb - bg) <= FIELD_TOL).all(axis=2)
    x0, x1, y0, y1 = cx, cx, cy, cy
    grew = True
    while grew:
        grew = False
        if x0 > 0 and same[y0:y1 + 1, x0 - 1].mean() >= 0.6:
            x0 -= 1; grew = True
        if x1 < W - 1 and same[y0:y1 + 1, x1 + 1].mean() >= 0.6:
            x1 += 1; grew = True
        if y0 > 0 and same[y0 - 1, x0:x1 + 1].mean() >= 0.6:
            y0 -= 1; grew = True
        if y1 < H - 1 and same[y1 + 1, x0:x1 + 1].mean() >= 0.6:
            y1 += 1; grew = True
    lum = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]
    box = [x0 / float(W), y0 / float(H), (x1 + 1) / float(W), (y1 + 1) / float(H)]
    return {"box": box, "bg": _hex(bg), "ink": "#111111" if lum > 140 else "#ffffff",
            "textPx": text_band_px(path, x, y, box=box)}


def caption_ink_px(lang, W, H):
    """The ink height of the film's caption glyphs at this frame size — the height a target's text must reach.
    Measured from the bundled body face at the caption's own size (layout.ts CAPTION_SIZE_FRAC)."""
    key = "zh" if str(lang or "").lower().startswith(("zh", "ja")) else "latin"
    size = caption_size_px(W, H)
    font = ImageFont.truetype(_FONTS[key], size)
    im = Image.new("L", (size * 8, size * 3), 0)
    ImageDraw.Draw(im).text((size // 2, size // 2), _SAMPLE[key], fill=255, font=font)
    rows = np.flatnonzero(np.asarray(im).max(axis=1) > 64)
    if not len(rows):
        raise RuntimeError("the caption sample %r drew no ink in %s — the bundled face lacks it"
                           % (_SAMPLE[key], _FONTS[key]))
    return float(rows[-1] - rows[0] + 1)
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_screen_media.py -q`
Expected: all pass. If `test_caption_ink_is_measured_from_the_bundled_face` fails with "drew no ink", the subset font lacks 字幕 — change `_SAMPLE["zh"]` to two glyphs it has (`python3 -c "from fontTools.ttLib import TTFont; print(0x5b57 in TTFont('assets/fonts/NotoSansSC-Subset.ttf').getBestCmap())"`), never to Latin.

- [ ] **Step 5: Commit**

```bash
git add scripts/screen_media.py tests/test_screen_media.py
git commit -m "Device layer: screenshot and recording facts, text height, the field under a point — measured

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 4: Finding text in a screenshot

**Files:**
- Create: `scripts/ocr_macos.swift`, `scripts/screen_text.py`
- Test: `tests/test_screen_text.py`

**Interfaces:**
- Consumes: `device_script.DeviceScriptError`.
- Produces: `screen_text.available() -> "vision" | "tesseract" | None`; `recognize(path, cache_dir=None) -> list[{"text": str, "box": [x0,y0,x1,y1]}]` (image fractions, top-left origin); `find_text(lines, text, nth=None) -> {"x", "y", "box"}` (raises `DeviceScriptError` listing what WAS recognised).

- [ ] **Step 1: Write `scripts/ocr_macos.swift`**

```swift
// macOS Vision text recognition for scripts/screen_text.py — prints JSON lines with boxes as image fractions
// (top-left origin). Compiled once per source hash into ~/.cache/slides-to-video/.
import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count > 1,
      let img = NSImage(contentsOfFile: CommandLine.arguments[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
  FileHandle.standardError.write("cannot read the image\n".data(using: .utf8)!)
  exit(2)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
req.recognitionLanguages = ["zh-Hans", "en-US"]
do {
  try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
} catch {
  FileHandle.standardError.write("vision failed: \(error)\n".data(using: .utf8)!)
  exit(3)
}
var out: [[String: Any]] = []
for obs in req.results ?? [] {
  guard let cand = obs.topCandidates(1).first else { continue }
  let b = obs.boundingBox
  out.append(["text": cand.string, "box": [b.minX, 1 - b.maxY, b.maxX, 1 - b.minY]])
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [])
FileHandle.standardOutput.write(data)
```

- [ ] **Step 2: Write the failing tests**

`tests/test_screen_text.py`:

```python
"""Text targets: found, or refused with what WAS found. Never a guess."""
import os
import shutil
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import device_script as ds          # noqa: E402
import screen_text as st            # noqa: E402

LINES = [{"text": "反馈汇总", "box": [0.1, 0.30, 0.4, 0.33]},
         {"text": "按产品线分组", "box": [0.1, 0.40, 0.5, 0.43]},
         {"text": "设置", "box": [0.1, 0.80, 0.2, 0.83]},
         {"text": "设置", "box": [0.6, 0.80, 0.7, 0.83]}]


def test_a_whole_line_is_found_at_its_centre():
    r = st.find_text(LINES, "反馈汇总")
    assert r["x"] == pytest.approx(0.25) and r["y"] == pytest.approx(0.315)


def test_part_of_a_line_is_found_at_its_share_of_the_line():
    r = st.find_text(LINES, "产品线")
    assert 0.1 < r["box"][0] < r["box"][2] < 0.5 and r["box"][0] > 0.15


def test_text_that_is_not_there_lists_what_is():
    with pytest.raises(ds.DeviceScriptError) as e:
        st.find_text(LINES, "发票")
    assert "反馈汇总" in str(e.value) and "not found" in str(e.value)


def test_text_found_twice_needs_nth_and_nth_picks():
    with pytest.raises(ds.DeviceScriptError) as e:
        st.find_text(LINES, "设置")
    assert "2 places" in str(e.value)
    assert st.find_text(LINES, "设置", nth=2)["x"] == pytest.approx(0.65)


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("swiftc"), reason="macOS Vision only")
def test_vision_finds_chinese_on_a_real_image(tmp_path):
    font = ImageFont.truetype(os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf"), 64)
    im = Image.new("RGB", (1170, 2532), "white")
    d = ImageDraw.Draw(im)
    d.text((100, 700), "反馈汇总", fill="black", font=font)
    d.text((100, 1200), "设置", fill="black", font=font)
    p = str(tmp_path / "s.png")
    im.save(p)
    r = st.find_text(st.recognize(p, cache_dir=str(tmp_path)), "反馈汇总")
    assert 0.05 < r["x"] < 0.4 and abs(r["y"] - (700 + 40) / 2532) < 0.02, r
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_screen_text.py -q`
Expected: `ModuleNotFoundError: No module named 'screen_text'`.

- [ ] **Step 4: Implement `scripts/screen_text.py`**

```python
#!/usr/bin/env python3
"""Find the words a step names inside a screenshot.

A step may target `{"text": "反馈汇总"}` instead of coordinates. That is resolved here, at build time, and the
coordinates are written into the props — so the per-beat render cache keys on them. macOS Vision (a compiled
Swift helper, Chinese and English) when on a Mac; tesseract when it is installed; otherwise the step must use
coordinates, and the error says so. Results are cached per screenshot content hash.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import device_script as ds

_HERE = os.path.dirname(os.path.abspath(__file__))
_SWIFT = os.path.join(_HERE, "ocr_macos.swift")
_BIN_DIR = os.path.join(os.path.expanduser("~"), ".cache", "slides-to-video")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def available():
    if sys.platform == "darwin" and shutil.which("swiftc"):
        return "vision"
    if shutil.which("tesseract"):
        return "tesseract"
    return None


def _vision(path):
    tag = _sha(_SWIFT)[:16]
    exe = os.path.join(_BIN_DIR, "ocr_macos-" + tag)
    if not os.path.exists(exe):
        os.makedirs(_BIN_DIR, exist_ok=True)
        subprocess.run(["swiftc", "-O", _SWIFT, "-o", exe], check=True, capture_output=True)
    r = subprocess.run([exe, path], capture_output=True, text=True)
    if r.returncode != 0:
        raise ds.DeviceScriptError(["text recognition failed on %s: %s" % (path, r.stderr.strip()[-200:])])
    return [{"text": o["text"], "box": [float(v) for v in o["box"]]} for o in json.loads(r.stdout or "[]")]


def _tesseract(path):
    from PIL import Image
    with Image.open(path) as im:
        W, H = im.size
    langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
    lang = "chi_sim+eng" if "chi_sim" in langs else "eng"
    r = subprocess.run(["tesseract", path, "stdout", "-l", lang, "tsv"], capture_output=True, text=True)
    lines = {}
    for row in r.stdout.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        key = (c[2], c[3], c[4])
        x, y, w, h = (int(v) for v in c[6:10])
        cur = lines.setdefault(key, {"text": "", "box": [x, y, x + w, y + h]})
        cur["text"] += c[11].strip()
        b = cur["box"]
        cur["box"] = [min(b[0], x), min(b[1], y), max(b[2], x + w), max(b[3], y + h)]
    return [{"text": v["text"], "box": [v["box"][0] / W, v["box"][1] / H, v["box"][2] / W, v["box"][3] / H]}
            for v in lines.values()]


def recognize(path, cache_dir=None):
    backend = available()
    if backend is None:
        raise ds.DeviceScriptError(["a text target needs text recognition, and this machine has none (macOS "
                                    "Vision needs `swiftc`; elsewhere install tesseract) — give the target as "
                                    "[x, y] instead"])
    cache = os.path.join(cache_dir or _BIN_DIR, "screen_text")
    os.makedirs(cache, exist_ok=True)
    memo = os.path.join(cache, "%s-%s.json" % (_sha(path), backend))
    if os.path.exists(memo):
        return json.load(open(memo, encoding="utf-8"))
    lines = _vision(path) if backend == "vision" else _tesseract(path)
    with open(memo, "w", encoding="utf-8") as fh:
        json.dump(lines, fh, ensure_ascii=False)
    return lines


def _norm(s):
    return "".join(str(s).split()).casefold()


def find_text(lines, text, nth=None):
    """{"x", "y", "box"} (image fractions) of the nth place `text` appears. A match inside a longer line takes
    its share of the line's width."""
    key = _norm(text)
    hits = []
    for ln in lines:
        t = _norm(ln["text"])
        at = t.find(key)
        while key and at >= 0:
            x0, y0, x1, y1 = ln["box"]
            a, b = at / float(len(t)), (at + len(key)) / float(len(t))
            hits.append([x0 + (x1 - x0) * a, y0, x0 + (x1 - x0) * b, y1])
            at = t.find(key, at + 1)
    hits.sort(key=lambda b: (round(b[1], 3), b[0]))
    if not hits:
        seen = ", ".join(repr(l["text"]) for l in lines[:12]) or "nothing"
        raise ds.DeviceScriptError(["%r not found in the screenshot — it shows %s" % (text, seen)])
    if nth is None and len(hits) > 1:
        raise ds.DeviceScriptError(["%r appears in %d places — say which with `nth` (1 = top-most, then left-most)"
                                    % (text, len(hits))])
    k = (nth or 1) - 1
    if k >= len(hits):
        raise ds.DeviceScriptError(["%r appears %d time(s); `nth` %d does not exist" % (text, len(hits), nth)])
    b = hits[k]
    return {"x": (b[0] + b[2]) / 2.0, "y": (b[1] + b[3]) / 2.0, "box": b}
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest tests/test_screen_text.py -q`
Expected: all pass (the Vision test runs on macOS with `swiftc`, skips elsewhere).

- [ ] **Step 6: Commit**

```bash
git add scripts/ocr_macos.swift scripts/screen_text.py tests/test_screen_text.py
git commit -m "Device layer: text targets are found in the screenshot, or refused with what was found

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 5: The device — geometry and drawing

**Files:**
- Create: `remotion/src/runtime/device.tsx`, `scripts/device_geometry.py`, `tests/_tsprobe.py`
- Test: `tests/test_device_runtime.py`

**Interfaces:**
- Consumes: `layout.CONTENT_TOP`, `layout.contentBottom`, `dna.mix`, `dna.DesignDNA`, `light.keyOf` (existing); `deviceSpec.json`; `_caption_band.caption_band_px`.
- Produces (TS): `type DeviceKind`, `DeviceLook`, `Placement`, `Rect`, `DeviceGeom`; `deviceGeometry(kind, look, W, H, placement?, kicker?) -> DeviceGeom`; `defaultLook(dna) -> DeviceLook`; `isTouch(kind) -> boolean`; `alpha(hex, a) -> string`; `<Device g dna>{screen content}</Device>`.
- Produces (Python): `device_geometry.geometry(kind, look, W, H, placement="center", kicker=False) -> dict` (same rects as TS); `tests/_tsprobe.run_ts(imports: str, body: str) -> dict`, `tests/_tsprobe.available() -> bool`.

- [ ] **Step 1: Write the shared TS probe helper `tests/_tsprobe.py`**

```python
"""Run a TypeScript snippet against the REAL runtime modules in node (esbuild bundle); return its JSON.

The snippet assigns into `out`; this returns it. Pure functions only — nothing here renders a frame."""
import json
import os
import shutil
import subprocess
import tempfile

_REM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remotion")
RUNTIME = os.path.join(_REM, "src", "runtime")


def available():
    return bool(shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules")))


def mod(name):
    return json.dumps(os.path.join(RUNTIME, name))


def run_ts(imports, body):
    tmp = tempfile.mkdtemp(prefix="tsprobe_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.tsx")
        with open(entry, "w", encoding="utf-8") as fh:
            fh.write(imports + "\nconst out: any = {};\n" + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

- [ ] **Step 2: Write the failing tests**

`tests/test_device_runtime.py` (this file grows in Tasks 6 and 7):

```python
"""The device layer's pure functions, run in node against the real modules — and held to their Python twins."""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe as tp               # noqa: E402

needs_node = pytest.mark.skipif(not tp.available(), reason="needs the remotion toolchain")
KINDS, LOOKS = ("phone", "tablet", "laptop", "monitor"), ("flat", "real", "screen")
ASPECTS = [(1920, 1080), (1080, 1920), (1080, 1080), (1080, 1350)]


@needs_node
def test_python_and_typescript_place_every_device_identically():
    import device_geometry as dg
    ts = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"), """
      for (const k of %s) for (const l of %s) for (const [W, H] of %s) for (const p of ['center', 'left'])
        out[`${k}/${l}/${W}x${H}/${p}`] = deviceGeometry(k as any, l as any, W, H, p as any, false);
    """ % (list(KINDS), list(LOOKS), [list(a) for a in ASPECTS]))
    for key, g in ts.items():
        k, l, wh, p = key.split("/")
        W, H = (int(v) for v in wh.split("x"))
        py = dg.geometry(k, l, W, H, p, False)
        assert {n: py[n] for n in ("body", "screen")} == {n: g[n] for n in ("body", "screen")}, key


@needs_node
def test_every_device_sits_inside_the_frame_and_above_the_caption_band():
    from _caption_band import caption_band_px
    ts = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"), """
      for (const k of %s) for (const l of %s) for (const [W, H] of %s)
        out[`${k}/${l}/${W}/${H}`] = deviceGeometry(k as any, l as any, W, H);
    """ % (list(KINDS), list(LOOKS), [list(a) for a in ASPECTS]))
    for key, g in ts.items():
        W, H = (int(v) for v in key.split("/")[2:])
        b, s = g["body"], g["screen"]
        assert b["x"] >= 0 and b["x"] + b["w"] <= W, key
        assert b["y"] >= 0 and b["y"] + b["h"] <= H - caption_band_px(W, H) + 1, key
        assert b["x"] <= s["x"] and s["x"] + s["w"] <= b["x"] + b["w"], key


@needs_node
def test_a_phone_fills_a_portrait_frame():
    from _caption_band import caption_band_px
    g = tp.run_ts("import {deviceGeometry} from %s;" % tp.mod("device"),
                  "out.g = deviceGeometry('phone', 'flat', 1080, 1920);")["g"]
    zone = 1920 - caption_band_px(1080, 1920) - round(1920 * 0.05)
    assert g["body"]["h"] >= 0.95 * zone, (g, zone)


@needs_node
def test_the_default_look_follows_the_ground():
    out = tp.run_ts("import {defaultLook} from %s;" % tp.mod("device"), """
      out.dark = defaultLook({bg: '#0b0d12'} as any); out.light = defaultLook({bg: '#f4f1ea'} as any);
      out.none = defaultLook(null);
    """)
    assert out == {"dark": "real", "light": "flat", "none": "flat"}
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_device_runtime.py -q`
Expected: FAIL — esbuild cannot resolve `device` (and `device_geometry` does not exist).

- [ ] **Step 4: Implement `remotion/src/runtime/device.tsx`**

```tsx
// The device a DeviceDemo / DeviceHero beat is performed on — its geometry and its three looks.
//
// deviceGeometry() is THE one definition of where a device and its screen sit. The drawing below, the camera
// and the gestures in the registers, and scripts/device_geometry.py (the legibility gate) all use it; a parity
// test holds the Python port to it. Numbers come from deviceSpec.json, shared with the Python side.
import React from 'react';
import spec from './deviceSpec.json';
import {CONTENT_TOP, contentBottom} from './layout';
import {mix, type DesignDNA} from './dna';
import {keyOf} from './light';

export type DeviceKind = 'phone' | 'tablet' | 'laptop' | 'monitor';
export type DeviceLook = 'flat' | 'real' | 'screen';
export type Placement = 'center' | 'left' | 'right';
export type Rect = {x: number; y: number; w: number; h: number};
export type DeviceGeom = {
  kind: DeviceKind; look: DeviceLook; body: Rect; screen: Rect; bezel: number; radius: number;
  island: Rect | null; base: Rect | null; strip: Rect | null;
};

type Body = {bezel: number; radius: number; base: number; overhang: number; strip: number};
const RATIO = spec.screenRatio as Record<DeviceKind, number[]>;
const BODY = spec.body as Record<DeviceLook, Record<DeviceKind, Body>>;
const PLACE = spec.placementX as Record<Placement, number>;

export const isTouch = (kind: DeviceKind): boolean => Boolean((spec.touch as Record<string, boolean>)[kind]);

export const alpha = (hex: string, a: number): string => {
  const m = /^#([0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

export const deviceGeometry = (kind: DeviceKind, look: DeviceLook, W: number, H: number,
                               placement: Placement = 'center', kicker = false): DeviceGeom => {
  const ratio = RATIO[kind], b = BODY[look]?.[kind];
  if (!ratio || !b) throw new Error(`device: no geometry for ${kind} / ${look}`);
  const [rw, rh] = ratio;
  const top = kicker ? CONTENT_TOP : Math.round(H * spec.zoneTopFrac);
  const zoneH = Math.max(1, contentBottom(W, H) - top);
  const zoneW = W * spec.zoneWidthFill;
  const shPerSw = rh / rw;
  const bwPerSw = 1 + 2 * b.bezel + 2 * b.overhang;
  const bhPerSw = shPerSw * (1 + b.strip) + 2 * b.bezel + b.base;
  const sw = Math.min(zoneW / bwPerSw, zoneH / bhPerSw);
  const sh = sw * shPerSw;
  const bodyW = sw * bwPerSw, bodyH = sw * bhPerSw;
  const margin = (W - zoneW) / 2;
  const bodyX = Math.min(Math.max(W * PLACE[placement] - bodyW / 2, margin), W - margin - bodyW);
  const bodyY = top + (zoneH - bodyH) / 2;
  const sx = bodyX + sw * (b.overhang + b.bezel);
  const sy = bodyY + sw * b.bezel + sh * b.strip;
  const R = Math.round;
  const rect = (x: number, y: number, w: number, h: number): Rect => ({x: R(x), y: R(y), w: R(w), h: R(h)});
  const isl = spec.island;
  return {
    kind, look,
    body: rect(bodyX, bodyY, bodyW, bodyH),
    screen: rect(sx, sy, sw, sh),
    bezel: R(sw * b.bezel),
    radius: R(sw * b.radius),
    island: kind === 'phone' && look !== 'screen'
      ? rect(sx + (sw * (1 - isl.w)) / 2, sy + sw * isl.top, sw * isl.w, sw * isl.h) : null,
    base: b.base > 0 ? rect(bodyX, sy + sh + sw * b.bezel, bodyW, sw * b.base) : null,
    strip: b.strip > 0 ? rect(sx, sy - sh * b.strip, sw, sh * b.strip) : null,
  };
};

/** The look a beat gets when it names none: realistic on a dark ground, flat on a light one. */
export const defaultLook = (dna: DesignDNA | null): DeviceLook => (dna && keyOf(dna) === 'dark' ? 'real' : 'flat');

const INK_D0 = '#14171c', BG_D0 = '#eef1f4';
// @decor: the metal of a realistic device body — a material, not a reading about anything the film named
const METAL_HI = '#e6e9ee', METAL_MID = '#8b919a', METAL_LO = '#5c636d';

export const Device: React.FC<{g: DeviceGeom; dna: DesignDNA | null; children?: React.ReactNode}> = ({g, dna, children}) => {
  const ink = dna?.fg ?? INK_D0;
  const bg = dna?.bg ?? BG_D0;
  const s = g.screen;
  const hi = mix(METAL_HI, bg, 0.1), mid = mix(METAL_MID, bg, 0.1), lo = mix(METAL_LO, bg, 0.1);
  const shadow = g.look === 'real' ? `0 ${Math.round(s.h * 0.05)}px ${Math.round(s.h * 0.1)}px rgba(0,0,0,0.45)`
    : `0 ${Math.round(s.h * 0.03)}px ${Math.round(s.h * 0.07)}px ${alpha(ink, g.look === 'screen' ? 0.22 : 0.16)}`;
  const lid: Rect = {x: s.x - g.bezel, y: s.y - g.bezel, w: s.w + 2 * g.bezel, h: s.h + 2 * g.bezel};
  const panelTop = g.strip ? g.strip.y : s.y;
  return (
    <>
      {g.look !== 'screen' ? (
        <div style={{position: 'absolute', left: lid.x, top: lid.y, width: lid.w, height: lid.h,
          borderRadius: g.radius + g.bezel, background: g.look === 'real' ? '#050608' : ink,
          boxShadow: g.look === 'real'
            ? `0 0 0 ${Math.max(2, Math.round(g.bezel * 0.35))}px ${hi}, 0 0 0 ${Math.max(3, Math.round(g.bezel * 0.6))}px ${lo}, ${shadow}`
            : shadow}} />
      ) : (
        <div style={{position: 'absolute', left: s.x, top: panelTop, width: s.w, height: s.y + s.h - panelTop,
          borderRadius: g.radius, background: mix(bg, '#ffffff', 0.85), boxShadow: shadow}} />
      )}
      {g.strip ? (
        <div style={{position: 'absolute', left: g.strip.x, top: g.strip.y, width: g.strip.w, height: g.strip.h,
          background: mix(bg, ink, 0.06), borderRadius: `${g.radius}px ${g.radius}px 0 0`}}>
          {[0, 1, 2].map((i) => (   // @positional: a window's three buttons are the same three on every window
            <span key={i} style={{position: 'absolute', top: g.strip!.h * 0.32, left: g.strip!.h * (0.5 + i * 0.55),
              width: g.strip!.h * 0.36, height: g.strip!.h * 0.36, borderRadius: '50%', background: mix(bg, ink, 0.25)}} />
          ))}
        </div>
      ) : null}
      <div style={{position: 'absolute', left: s.x, top: s.y, width: s.w, height: s.h, overflow: 'hidden',
        borderRadius: g.strip ? `0 0 ${g.radius}px ${g.radius}px` : g.radius, background: '#000'}}>
        {children}
        {g.look === 'real' ? (
          <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
            background: 'linear-gradient(118deg, rgba(255,255,255,0.14), rgba(255,255,255,0) 38%)'}} />
        ) : null}
      </div>
      {g.island ? (
        <div style={{position: 'absolute', left: g.island.x, top: g.island.y, width: g.island.w, height: g.island.h,
          borderRadius: g.island.h, background: g.look === 'real' ? '#000000' : ink}} />
      ) : null}
      {g.base && g.kind === 'laptop' ? (
        <div style={{position: 'absolute', left: g.base.x, top: g.base.y, width: g.base.w, height: g.base.h,
          background: g.look === 'real' ? `linear-gradient(180deg, ${hi}, ${mid} 60%, ${lo})` : ink,
          clipPath: 'polygon(0 0, 100% 0, 97% 100%, 3% 100%)'}} />
      ) : null}
      {g.base && g.kind === 'monitor' ? (
        <>
          <div style={{position: 'absolute', left: g.base.x + g.base.w * 0.44, top: g.base.y, width: g.base.w * 0.12,
            height: g.base.h * 0.82, background: g.look === 'real' ? `linear-gradient(90deg, ${lo}, ${hi}, ${lo})` : ink}} />
          <div style={{position: 'absolute', left: g.base.x + g.base.w * 0.32, top: g.base.y + g.base.h * 0.82,
            width: g.base.w * 0.36, height: g.base.h * 0.18, borderRadius: g.base.h * 0.09,
            background: g.look === 'real' ? `linear-gradient(180deg, ${hi}, ${mid})` : ink}} />
        </>
      ) : null}
    </>
  );
};
```

- [ ] **Step 5: Implement `scripts/device_geometry.py`**

```python
#!/usr/bin/env python3
"""Python port of runtime/device.tsx deviceGeometry() — for the legibility gate, which runs before a render.

tests/test_device_runtime.py holds this to the TypeScript for every kind x look x aspect: a second copy of a
rectangle is a second answer, so the copy is checked, not trusted."""
import math
import os
import re

import device_script as ds
from _caption_band import caption_band_px

_LAYOUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime", "layout.ts")


def _content_top():
    m = re.search(r"export const TITLE_BAND\s*=\s*(\d+)", open(_LAYOUT, encoding="utf-8").read())
    if not m:
        raise RuntimeError("TITLE_BAND not found in runtime/layout.ts")
    return int(m.group(1))


def _r(x):
    """Math.round: halves go UP (Python's round() sends 0.5 to 0)."""
    return int(math.floor(x + 0.5))


def geometry(kind, look, W, H, placement="center", kicker=False):
    S = ds.SPEC
    rw, rh = S["screenRatio"][kind]
    b = S["body"][look][kind]
    top = _content_top() if kicker else _r(H * S["zoneTopFrac"])
    zone_h = max(1, (H - caption_band_px(W, H)) - top)
    zone_w = W * S["zoneWidthFill"]
    sh_per_sw = float(rh) / rw
    bw = 1 + 2 * b["bezel"] + 2 * b["overhang"]
    bh = sh_per_sw * (1 + b["strip"]) + 2 * b["bezel"] + b["base"]
    sw = min(zone_w / bw, zone_h / bh)
    sh = sw * sh_per_sw
    body_w, body_h = sw * bw, sw * bh
    margin = (W - zone_w) / 2.0
    body_x = min(max(W * S["placementX"][placement] - body_w / 2.0, margin), W - margin - body_w)
    body_y = top + (zone_h - body_h) / 2.0
    sx = body_x + sw * (b["overhang"] + b["bezel"])
    sy = body_y + sw * b["bezel"] + sh * b["strip"]

    def rect(x, y, w, h):
        return {"x": _r(x), "y": _r(y), "w": _r(w), "h": _r(h)}

    return {"body": rect(body_x, body_y, body_w, body_h), "screen": rect(sx, sy, sw, sh)}
```

`caption_band_px` rounds with Python's `round()` — if the parity test fails ONLY on the caption band by one pixel, make `_caption_band.caption_band_px` use the same floor(x + 0.5) rule and note it in its docstring (it mirrors `Math.round` in layout.ts). Do not change layout.ts.

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_device_runtime.py -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add remotion/src/runtime/device.tsx scripts/device_geometry.py tests/_tsprobe.py tests/test_device_runtime.py
git commit -m "Device layer: four devices in three looks, one geometry held to its Python port

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 6: The screen — screenshots, long screenshots, recordings

**Files:**
- Create: `remotion/src/runtime/screen.tsx`
- Test: `tests/test_device_runtime.py` (append)

**Interfaces:**
- Consumes: `motion.clamp01`, `motion.easeOutCubic`, `motion.easeInOutCubic` (existing).
- Produces: `scrollRangePx(imageW, imageH, screenW, screenH) -> number`; `flingAt(u, overshoot=0.04) -> number` (0 → 1, peaks at 1 + overshoot, ends at exactly 1); `type VideoSpan = {f0, f1, v0, v1}`; `<ScreenImage src imageW imageH w h offsetPx?>`; `<ScreenVideo src spans w h>`.

- [ ] **Step 1: Append the failing tests to `tests/test_device_runtime.py`**

```python
@needs_node
def test_a_fling_ends_exactly_where_it_was_sent_and_overshoots_only_a_little():
    out = tp.run_ts("import {flingAt, scrollRangePx} from %s;" % tp.mod("screen"), """
      const us = Array.from({length: 101}, (_, i) => i / 100);
      out.v = us.map((u) => flingAt(u));
      out.range = scrollRangePx(1170, 6000, 390, 844);
      out.none = scrollRangePx(1170, 2532, 390, 844);
    """)
    v = out["v"]
    assert v[0] == 0 and abs(v[-1] - 1) < 1e-9
    assert max(v) <= 1.04 + 1e-9 and max(v) > 1.0
    assert all(b >= a - 1e-9 for a, b in zip(v[:72], v[1:73])), "the fling reverses before its peak"
    assert out["range"] == pytest.approx(6000 * 390 / 1170 - 844)
    assert out["none"] == pytest.approx(0, abs=1)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_device_runtime.py -q -k fling`
Expected: FAIL — esbuild cannot resolve `screen`.

- [ ] **Step 3: Implement `remotion/src/runtime/screen.tsx`**

```tsx
// What a device's screen shows: the user's screenshot (a long one scrolls), their recording, or a page the
// register draws. The scroll can never show past its end except inside a fling's overshoot — the range is
// computed from the image's real height, never from a box that happens to hold it.
import React from 'react';
import {Img, OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import {clamp01, easeOutCubic, easeInOutCubic} from './motion';

export const scrollRangePx = (imageW: number, imageH: number, screenW: number, screenH: number): number =>
  Math.max(0, (imageH * screenW) / Math.max(1, imageW) - screenH);

/** A fling: a fast start and an eased stop at 1 + overshoot by 72% of the gesture, then a spring back to 1. */
export const flingAt = (u: number, overshoot = 0.04): number => {
  const c = clamp01(u);
  if (c <= 0.72) return (1 + overshoot) * easeOutCubic(c / 0.72);
  return 1 + overshoot * (1 - easeInOutCubic((c - 0.72) / 0.28));
};

export type VideoSpan = {f0: number; f1: number; v0: number; v1: number};

export const ScreenImage: React.FC<{src: string; imageW: number; imageH: number; w: number; h: number; offsetPx?: number}> =
  ({src, imageW, imageH, w, h, offsetPx = 0}) => (
    <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden', background: '#ffffff'}}>
      <Img src={staticFile(src)} style={{position: 'absolute', left: 0, top: -offsetPx, width: w,
        height: (imageH * w) / Math.max(1, imageW)}} />
    </div>
  );

/** A recording, beat frames [f0, f1) showing its seconds [v0, v1) — one Sequence per span, so a mapping that
 *  bends at a cue is a chain of constant rates. */
export const ScreenVideo: React.FC<{src: string; spans: VideoSpan[]; w: number; h: number}> = ({src, spans, w, h}) => {
  const {fps} = useVideoConfig();
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden', background: '#000000'}}>
      {spans.map((s, i) => {
        const frames = Math.max(1, Math.round(s.f1 - s.f0));
        return (
          <Sequence key={i} from={Math.round(s.f0)} durationInFrames={frames} layout="none">
            <OffthreadVideo src={staticFile(src)} muted startFrom={Math.round(s.v0 * fps)}
              playbackRate={Math.max(0.01, ((s.v1 - s.v0) * fps) / frames)}
              style={{position: 'absolute', left: 0, top: 0, width: w, height: h, objectFit: 'cover'}} />
          </Sequence>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_device_runtime.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add remotion/src/runtime/screen.tsx tests/test_device_runtime.py
git commit -m "Device layer: the screen — screenshots, long screenshots that fling and settle, recordings

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 7: The gestures

**Files:**
- Create: `remotion/src/runtime/gesture.tsx`
- Test: `tests/test_device_runtime.py` (append)

**Interfaces:**
- Consumes: `motion.clamp01`, `motion.hash01` (existing); `device.alpha` (Task 5); `deviceSpec.json`.
- Produces: `typeChunks(value) -> string[]`; `typedCount(t, ta, t1, chunks, seed=1) -> number`; `caretOn(framesSinceLastKey: number | null, reduced: boolean) -> boolean`; `framesBetween(tFrom, tTo, span, entryT) -> number`; `<TapRipple x y u color size>`; `<CursorArrow x y size press?>`.

- [ ] **Step 1: Append the failing tests**

```python
_CHUNK_CASES = ["ab c", "上周的客户反馈", "上周 AI", "", "搜索：上周所有的客户反馈 invoice"]


@needs_node
def test_typing_chunks_are_the_same_on_both_sides():
    import device_script as ds
    out = tp.run_ts("import {typeChunks} from %s;" % tp.mod("gesture"),
                    "out.v = %s.map((s) => typeChunks(s));" % _CHUNK_CASES.__repr__().replace("'", '"'))
    assert out["v"] == [ds.type_chunks(s) for s in _CHUNK_CASES]


@needs_node
def test_every_chunk_is_typed_by_the_end_and_never_before_the_start():
    out = tp.run_ts("import {typeChunks, typedCount} from %s;" % tp.mod("gesture"), """
      const c = typeChunks('上周的客户反馈 invoice');
      const ts = Array.from({length: 51}, (_, i) => 0.3 + (i / 50) * 0.4);
      out.n = c.length; out.v = ts.map((t) => typedCount(t, 0.4, 0.6, c));
    """)
    v = out["v"]
    assert v[0] == 0 and v[-1] == out["n"] and all(b >= a for a, b in zip(v, v[1:]))


@needs_node
def test_the_caret_is_solid_while_typing_and_blinks_in_sixteen_frame_phases():
    out = tp.run_ts("import {caretOn} from %s;" % tp.mod("gesture"), """
      out.typing = [null, -3, 0].map((f) => caretOn(f as any, false));
      out.after = Array.from({length: 64}, (_, i) => caretOn(i + 1, false));
      out.reduced = caretOn(20, true);
    """)
    assert out["typing"] == [True, True, True] and out["reduced"] is True
    a = out["after"]
    flips = [i for i in range(1, len(a)) if a[i] != a[i - 1]]
    assert flips and all(b - a_ == 16 for a_, b in zip(flips, flips[1:])), flips
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_device_runtime.py -q -k "chunk or caret"`
Expected: FAIL — esbuild cannot resolve `gesture`.

- [ ] **Step 3: Implement `remotion/src/runtime/gesture.tsx`**

```tsx
// The gestures a device beat performs — ONE implementation. Four registers used to draw their own cursor;
// CommandSummon's caret blinked 5.6 times a second on a 5-second beat because its rate was tied to the beat's
// length. Everything here runs on frames or on the schedule it is handed, never on a beat-relative rate.
import React from 'react';
import spec from './deviceSpec.json';
import {clamp01, hash01} from './motion';
import {alpha} from './device';

const CJK = /[㐀-鿿豈-﫿぀-ヿ가-힯]/;

/** Latin one character per keystroke, CJK a two-glyph word per commit, or exactly the author's list.
 *  scripts/device_script.type_chunks is the same function; a parity test holds them together. */
export const typeChunks = (value: string | string[]): string[] => {
  if (Array.isArray(value)) return value.map(String).filter((s) => s.length > 0);
  const out: string[] = [];
  let run = '';
  for (const ch of Array.from(String(value ?? ''))) {
    if (CJK.test(ch)) {
      run += ch;
      if (Array.from(run).length === 2) { out.push(run); run = ''; }
    } else {
      if (run) { out.push(run); run = ''; }
      out.push(ch);
    }
  }
  if (run) out.push(run);
  return out;
};

/** How many chunks are on screen at t: each lands at the START of its share of [ta, t1]; shares follow the
 *  chunk's nominal time with a deterministic jitter. */
export const typedCount = (t: number, ta: number, t1: number, chunks: string[], seed = 1): number => {
  if (!chunks.length || t < ta) return 0;
  if (t >= t1) return chunks.length;
  const w = chunks.map((c, i) =>   // @decor: keystroke rhythm, not a reading about anything the film named
    (CJK.test(c) ? spec.minSeconds.typeCjkWord : spec.minSeconds.typeLatinKey) * (0.65 + 0.7 * hash01(seed * 131 + i)));
  const total = w.reduce((a, b) => a + b, 0);
  const u = ((t - ta) / Math.max(1e-6, t1 - ta)) * total;
  let acc = 0, n = 0;
  for (const x of w) { if (u >= acc) n += 1; acc += x; }
  return Math.min(chunks.length, n);
};

/** Solid until the last keystroke; then on/off in phases of `caretPhaseFrames` (the TermLog/TermThink
 *  standard, ~0.53 s at 30 fps). Reduced motion: solid. */
export const caretOn = (framesSinceLastKey: number | null, reduced: boolean): boolean => {
  if (reduced || framesSinceLastKey === null || framesSinceLastKey <= 0) return true;
  return Math.floor(framesSinceLastKey / spec.caretPhaseFrames) % 2 === 0;
};

/** Frames between two useT moments: `span` frames (useAnimSpan) cover (1 - ENTRY_T) of t. */
export const framesBetween = (tFrom: number, tTo: number, span: number, entryT: number): number =>
  ((tTo - tFrom) * span) / Math.max(1e-6, 1 - entryT);

/** The brand tap: an accent ring that lands, and ONE ripple that spreads and fades. u runs 0..1 over the tap. */
export const TapRipple: React.FC<{x: number; y: number; u: number; color: string; size: number}> = ({x, y, u, color, size}) => {
  if (!(u > 0 && u < 1)) return null;
  const land = clamp01(u / 0.15), fade = u > 0.7 ? 1 - (u - 0.7) / 0.3 : 1, wave = clamp01((u - 0.1) / 0.6);
  const ring = (scale: number, op: number, fill: boolean) => (
    <div style={{position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size,
      borderRadius: '50%', border: `${Math.max(2, Math.round(size * 0.06))}px solid ${color}`,
      background: fill ? alpha(color, 0.16) : 'transparent', opacity: op, transform: `scale(${scale})`}} />
  );
  return <>{ring(0.4 + 0.6 * land, fade, true)}{ring(1 + 1.4 * wave, (1 - wave) * 0.9 * fade, false)}</>;
};

/** A system arrow whose tip sits exactly on (x, y); `press` 0..1 shrinks it as a click lands. */
export const CursorArrow: React.FC<{x: number; y: number; size: number; press?: number}> = ({x, y, size, press = 0}) => (
  <svg viewBox="0 0 24 24" width={size} height={size} style={{position: 'absolute', left: x - size * (4 / 24),
    top: y - size * (2 / 24), overflow: 'visible', transformOrigin: `${(4 / 24) * 100}% ${(2 / 24) * 100}%`,
    transform: `scale(${1 - 0.18 * clamp01(press)})`}}>
    <path d="M4 2l16 9-7 2-3 7z" fill="#111111" stroke="#ffffff" strokeWidth={1.6} strokeLinejoin="round" />
  </svg>
);
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_device_runtime.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add remotion/src/runtime/gesture.tsx tests/test_device_runtime.py
git commit -m "Device layer: one gesture implementation — typing, caret, brand tap, cursor

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 8: CommandSummon and TermTable adopt the shared caret

**Files:**
- Modify: `remotion/src/shots/CommandSummon.tsx:54-58, 82`; `remotion/src/shots/TermTable.tsx:181, 199`
- Test: `tests/test_caret.py`

**Interfaces:**
- Consumes: `gesture.caretOn`, `gesture.framesBetween` (Task 7); `motion.useAnimSpan`, `motion.ENTRY_T`, `motion.ReducedMotionContext` (existing).
- Produces: nothing new; both registers' carets run on frames.

- [ ] **Step 1: Write the failing test** — `tests/test_caret.py`:

```python
"""CommandSummon's caret blinked on `t * 60` — a rate tied to the beat's LENGTH: measured frame by frame on a
5-second beat, 5.6 flashes a second, and it blinked while typing. A caret is solid while you type and blinks
at the system's pace afterwards; this measures the rendered frames, not the code."""
import json
import os
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _frames(tmp_path, durF=150):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    props = {"scenes": [{"shot": "CommandSummon", "durF": durF,
                         "props": {"command": "search last week feedback", "items": ["one", "two", "three"]}}],
             "dna": "product", "captions": False, "camera": 0}
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    mp4 = str(tmp_path / "cs.mp4")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Film", mp4, "--props=" + str(pf),
                        "--gl=angle", "--scale=0.5", "--log=error"], cwd=_REM, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-500:]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, 540, 960, 3).astype(int)


@needs_toolchain
def test_the_palette_caret_is_solid_while_typing_and_never_flickers(tmp_path):
    np = pytest.importorskip("numpy")
    fr = _frames(tmp_path)
    row = fr[:, 110:150, 215:785, :]
    on = ((row[..., 2] > 180) & (row[..., 2] - row[..., 0] > 60)).sum(axis=(1, 2)) > 20
    typing = on[20:60]
    assert typing.mean() > 0.9, "the caret is not solid while the command types: %r" % typing.astype(int)
    flips = int(np.sum(on[20:75][1:] != on[20:75][:-1]))
    assert flips <= 4, "the caret flipped %d times in under 2 s — it is flickering, not blinking" % flips
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_caret.py -q`
Expected: FAIL — `the caret is not solid while the command types` (the current caret blinks on `t * 60`).

- [ ] **Step 3: Edit `CommandSummon.tsx`**

Add to its imports: `import {caretOn, framesBetween} from '../runtime/gesture';` and extend the motion import with `useAnimSpan, ENTRY_T, ReducedMotionContext` (keep what is already imported). Replace line 57:

```tsx
  const caretOn = t < 0.46 && Math.floor(t * 60) % 2 === 0;
```

with:

```tsx
  // The caret runs on FRAMES (runtime/gesture): solid while the command types, then the system's 16-frame
  // phases. It used to be `Math.floor(t * 60) % 2` — a rate tied to the beat's length, measured at 5.6
  // flashes a second on a 5-second beat, blinking mid-word.
  const span = useAnimSpan();
  const reduced = React.useContext(ReducedMotionContext);
  const TYPED_BY = 0.44;
  const caretShown = t < 0.46 && caretOn(t < TYPED_BY ? null : framesBetween(TYPED_BY, t, span, ENTRY_T), reduced);
```

and on line 82 change `opacity: caretOn ? 1 : 0` to `opacity: caretShown ? 1 : 0`. (If `React` is imported as a default import already, keep it; `React.useContext` needs it.)

- [ ] **Step 4: Edit `TermTable.tsx`**

Add the same imports. Replace line 181:

```tsx
  const caretOn = Math.floor(t * 24) % 2 === 0;                  // blink driven by t → frozen under reduced motion
```

with:

```tsx
  // FRAMES, not t: `Math.floor(t * 24)` tied the blink to the beat's length. Reduced motion stays solid —
  // what the t-driven version was protecting — through caretOn's own `reduced` branch.
  const span = useAnimSpan();
  const reduced = React.useContext(ReducedMotionContext);
  const caretLit = caretOn(ran ? framesBetween(0.17, t, span, ENTRY_T) : null, reduced);
```

and on line 199 change `opacity: ran ? (caretOn ? 0.5 : 0.12) : 0.9` to `opacity: ran ? (caretLit ? 0.5 : 0.12) : 0.9`.

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest tests/test_caret.py -q && python3 scripts/content_contract_qa.py CommandSummon TermTable`
Expected: the caret test passes; the contract check reports no new finding.

- [ ] **Step 6: Re-measure the two registers** (their sources changed; do not run while anything else sweeps)

Run:
```bash
python3 scripts/register_energy.py --only CommandSummon,TermTable
python3 scripts/prop_reach.py --only CommandSummon,TermTable
python3 scripts/measure_ground_reach.py --stale
```
Expected: two rows re-measured in each manifest; `--stale` lists nothing, or lists these two — then `python3 scripts/measure_ground_reach.py --only CommandSummon,TermTable --apply-manifest` per its own help text.

- [ ] **Step 7: Commit**

```bash
git add remotion/src/shots/CommandSummon.tsx remotion/src/shots/TermTable.tsx tests/test_caret.py remotion/register_energy.json remotion/prop_reach.json
git commit -m "CommandSummon and TermTable carets run on frames: solid while typing, 16-frame phases after

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

(Add `remotion/_ground_reach.json` to the `git add` only if Step 6 changed it.)

---

### Task 9: DeviceDemo

**Files:**
- Scaffold, then write: `remotion/src/shots/DeviceDemo.tsx`, `remotion/cards/DeviceDemo.md`
- Modified by the scaffold: `remotion/src/registry.ts`, `remotion/src/Root.tsx`, `remotion/src/runtime/shotLuma.ts`, `scripts/shot_director.py`, `remotion/LIBRARY.md`
- Test: `tests/test_device_demo.py`

**Interfaces:**
- Consumes: Tasks 5–7 (`deviceGeometry`, `defaultLook`, `isTouch`, `Device`, `ScreenImage`, `ScreenVideo`, `scrollRangePx`, `flingAt`, `typeChunks`, `typedCount`, `caretOn`, `framesBetween`, `TapRipple`, `CursorArrow`); `pageCam2D.camAt`, `clampToPage`; `layout.textWidthPx`, `TITLE_Y`.
- Produces: the register `DeviceDemo` with props `device, look, steps, camera, placement, kicker`, and the exported type `Step` (prepared fields: `t0, ta, t1, focus, textFrac, captionPx, field, imageW, imageH, spans`).

- [ ] **Step 1: Scaffold the register at every sync point**

Run:
```bash
python3 scripts/register_shot.py DeviceDemo A --use-when "one operation performed on the product's own screens, each step on the narration's words" --provenance product-ui
python3 scripts/register_shot.py DeviceDemo --check
```
Expected: the stub `remotion/src/shots/DeviceDemo.tsx` exists and `--check` reports nothing missing.

- [ ] **Step 2: Write the failing render tests** — `tests/test_device_demo.py`:

```python
"""DeviceDemo on real frames: the tap lands on its target, the caret stays at the typing head, a scroll ends
with no blank past the last row, and the push-in makes the target's text as tall as a caption.

Each of these is a defect the design mockups themselves shipped before they were caught by a screenshot —
so each is measured on the render, never inferred from the code."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")
FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")
ACCENT_PRODUCT = None     # read from the rendered pixels, not restated


def _screenshot(path, h=2532, rows=12):
    im = Image.new("RGB", (1170, h), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    d.text((110, 232), "搜索反馈", fill=(140, 147, 160), font=f)
    for i in range(rows):
        y = 420 + i * 180
        d.text((90, y), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
        d.line([(60, y + 120), (1110, y + 120)], fill=(222, 226, 232), width=3)
    im.save(path)
    return path


def _render(tmp_path, props, frame, name, aspect="16:9"):
    pf = tmp_path / (name + ".json")
    pf.write_text(json.dumps(dict(props, dna="product", aspect=aspect), ensure_ascii=False), encoding="utf-8")
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceDemo", png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + str(pf), "--public-dir=" + str(tmp_path)],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    return png


def _geom(W=1920, H=1080, kind="phone", look="flat"):
    import device_geometry as dg
    return dg.geometry(kind, look, W, H)["screen"]


def _accent_centroid(png):
    np = pytest.importorskip("numpy")
    a = np.asarray(Image.open(png).convert("RGB"), dtype=int)
    blue = (a[..., 2] > 150) & (a[..., 2] - a[..., 0] > 70) & (a[..., 2] - a[..., 1] > 30)
    ys, xs = np.nonzero(blue)
    return (float(xs.mean()), float(ys.mean())) if len(xs) > 40 else None


BASE = {"device": "phone", "look": "flat", "camera": "still"}


@needs_toolchain
def test_the_tap_lands_on_its_target(tmp_path):
    _screenshot(str(tmp_path / "ui.png"))
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.3, 0.2], "t0": 0.3, "ta": 0.4, "t1": 0.7}]
    png = _render(tmp_path, dict(BASE, steps=steps), 72, "tap")
    s = _geom()
    c = _accent_centroid(png)
    assert c is not None, "no tap ring was drawn"
    tx, ty = s["x"] + 0.3 * s["w"], s["y"] + 0.2 * s["h"]
    assert abs(c[0] - tx) < s["w"] * 0.06 and abs(c[1] - ty) < s["h"] * 0.03, (c, (tx, ty))


@needs_toolchain
def test_the_caret_sits_at_the_typing_head(tmp_path):
    np = pytest.importorskip("numpy")
    _screenshot(str(tmp_path / "ui.png"))
    field = {"box": [60 / 1170, 200 / 2532, 1110 / 1170, 320 / 2532], "bg": "#eef1f4", "ink": "#111111",
             "textFrac": 46 / 1170}
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"type": "上周的客户反馈", "into": [0.5, 0.1], "field": field, "t0": 0.25, "ta": 0.3, "t1": 0.7}]
    png = _render(tmp_path, dict(BASE, steps=steps), 100, "type")
    s = _geom()
    a = np.asarray(Image.open(png).convert("RGB"), dtype=int)
    y0, y1 = int(s["y"] + s["h"] * 200 / 2532), int(s["y"] + s["h"] * 320 / 2532)
    band = a[y0:y1, s["x"]:s["x"] + s["w"]]
    dark = (band.sum(axis=2) < 200).any(axis=0)
    blue = ((band[..., 2] > 150) & (band[..., 2] - band[..., 0] > 70)).any(axis=0)
    assert dark.any() and blue.any(), "no typed text or no caret in the field"
    text_right, caret_x = int(np.flatnonzero(dark).max()), int(np.flatnonzero(blue).mean())
    assert 0 <= caret_x - text_right <= max(8, s["w"] * 0.02), (text_right, caret_x)


@needs_toolchain
def test_long_typed_text_stays_inside_its_field(tmp_path):
    np = pytest.importorskip("numpy")
    _screenshot(str(tmp_path / "ui.png"))
    field = {"box": [60 / 1170, 200 / 2532, 1110 / 1170, 320 / 2532], "bg": "#eef1f4", "ink": "#111111",
             "textFrac": 46 / 1170}
    long = "上周所有产品线的客户反馈以及它们最常提到的问题"
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"type": long, "into": [0.5, 0.1], "field": field, "t0": 0.2, "ta": 0.25, "t1": 0.8}]
    png = _render(tmp_path, dict(BASE, steps=steps), 120, "long")      # mid-typing: the caret is solid
    s = _geom()
    a = np.asarray(Image.open(png).convert("RGB"), dtype=int)
    y0, y1 = int(s["y"] + s["h"] * 200 / 2532), int(s["y"] + s["h"] * 320 / 2532)
    band = a[y0:y1, :]
    blue = ((band[..., 2] > 150) & (band[..., 2] - band[..., 0] > 70)).any(axis=0)
    xs = np.flatnonzero(blue)
    right = s["x"] + s["w"] * 1110 / 1170
    assert len(xs) and xs.max() <= right, "the caret left the field (x=%d, field ends %d)" % (xs.max(), right)


@needs_toolchain
def test_a_scroll_ends_with_the_last_row_on_the_screen_and_no_blank(tmp_path):
    np = pytest.importorskip("numpy")
    _screenshot(str(tmp_path / "long.png"), h=6000, rows=30)
    steps = [{"screen": {"image": "long.png"}, "imageW": 1170, "imageH": 6000, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"scroll": 1.0, "t0": 0.2, "ta": 0.3, "t1": 0.7}]
    png = _render(tmp_path, dict(BASE, steps=steps), 170, "scroll")
    s = _geom()
    a = np.asarray(Image.open(png).convert("L"), dtype=int)
    bottom = a[s["y"] + int(s["h"] * 0.9):s["y"] + s["h"] - 2, s["x"] + 10:s["x"] + s["w"] - 10]
    assert (bottom < 200).any(), "the bottom tenth of the screen is empty after the scroll settled"


@needs_toolchain
def test_the_push_in_makes_the_target_text_caption_tall(tmp_path):
    import screen_media as sm
    ui = _screenshot(str(tmp_path / "ui.png"))
    cap = sm.caption_ink_px("zh", 1920, 1080)
    y = (420 + 6 * 180 + 30) / 2532                     # a mid-screen row: the camera clamp does not move it
    ink = sm.text_band_px(ui, 0.3, y)                    # measured, exactly as prepare() measures it
    steps = [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06, "ta": 0.06, "t1": 0.2},
             {"tap": [0.3, y], "t0": 0.3, "ta": 0.45, "t1": 0.75, "focus": [0.3, y],
              "textFrac": ink / 1170, "captionPx": cap}]
    props = {"device": "phone", "look": "flat", "steps": steps}
    png = _render(tmp_path, props, 100, "zoom")
    band = sm.text_band_px(png, 0.5, 0.5)
    assert band is not None and band >= cap * 0.85, (band, cap)


@needs_toolchain
def test_the_standalone_demo_renders_without_a_script(tmp_path):
    _render(tmp_path, {}, 90, "demo")
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_device_demo.py -q`
Expected: FAIL (the stub draws its own name; no ring, no field, no scroll).

- [ ] **Step 4: Write `remotion/src/shots/DeviceDemo.tsx`** (replacing the stub entirely)

```tsx
// SHOT · DeviceDemo — one operation, performed on a drawn device, on the words the narration says. Family A.
//
// THE ARGUMENT SHAPE: "here, this is what you do." A product film that says "search last week's feedback,
// open the summary, scroll to the pattern" makes a claim about an interface — that it works in these steps.
// This shows the product's OWN screens (the user's screenshots or recording) inside a phone, tablet, laptop
// or monitor, and performs each step when the voice names it
// (docs/superpowers/specs/2026-09-26-device-layer-design.md).
//
// The script is PREPARED before it reaches here (scripts/device_script.py): every target is a point on the
// screen, every step has its window (t0, ta, t1), every gesture its text height and the caption height it must
// reach, every typed field its box and colours. This register draws that schedule and invents none of it.
// Without `steps` it draws its own demo — skeleton bars on a code-drawn screen, no text — so a standalone
// preview renders and no demo copy exists that could leak into a film.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, ENTRY_T, ReducedMotionContext, clamp01, seg, easeInOutCubic, easeCursor} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {camAt, clampToPage, type CamKey} from '../runtime/pageCam2D';
import {textWidthPx, TITLE_Y} from '../runtime/layout';
import {deviceGeometry, defaultLook, isTouch, Device, type DeviceKind, type DeviceLook, type Placement} from '../runtime/device';
import {ScreenImage, ScreenVideo, scrollRangePx, flingAt, type VideoSpan} from '../runtime/screen';
import {typeChunks, typedCount, caretOn, framesBetween, TapRipple, CursorArrow} from '../runtime/gesture';
import spec from '../runtime/deviceSpec.json';

export const DURATION = 180;

type Pt = [number, number];
type Field = {box: [number, number, number, number]; bg: string; ink: string; textFrac: number | null};
type ScreenSrc = {image?: string; video?: string; page?: 'demo'; from?: number; to?: number};
export type Step = {
  screen?: ScreenSrc; via?: 'push' | 'fade';
  type?: string | string[]; into?: Pt; tap?: Pt; click?: Pt; scroll?: number; drag?: {from: Pt; to: Pt};
  mark?: Pt; at?: number; video?: number;
  // written by scripts/device_script.prepare — never authored
  t0?: number; ta?: number; t1?: number; focus?: Pt; textFrac?: number; captionPx?: number;
  field?: Field; imageW?: number; imageH?: number; spans?: VideoSpan[];
};

const DEMO_STEPS: Step[] = [{screen: {page: 'demo'}}, {tap: [0.5, 0.355]}];
const KINDS = ['screen', 'type', 'tap', 'click', 'scroll', 'drag', 'mark'] as const;
const kindOf = (s: Step): string => KINDS.find((k) => k in s) ?? '';

/** The prepared schedule when every step carries one, else an even spread (the standalone demo). */
const scheduled = (steps: Step[]): Step[] => {
  if (steps.every((s) => typeof s.t0 === 'number' && typeof s.ta === 'number' && typeof s.t1 === 'number')) return steps;
  const slot = (1 - ENTRY_T) / steps.length;
  return steps.map((s, i) => ({...s, t0: ENTRY_T + i * slot, ta: ENTRY_T + (i + 0.35) * slot, t1: ENTRY_T + (i + 0.9) * slot}));
};

const DemoPage: React.FC<{w: number; h: number; ink: string; ground: string}> = ({w, h, ink, ground}) => (
  <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, background: ground}}>
    {Array.from({length: 7}).map((_, i) => (   // @decor: skeleton rows of the register's own demo screen — no film ever sees them
      <div key={i} style={{position: 'absolute', left: w * 0.08, top: h * (0.12 + i * 0.1), width: w * 0.84,
        height: h * 0.07, borderRadius: h * 0.012, background: mix(ground, ink, 0.07)}} />
    ))}
  </div>
);

export const DeviceDemo: React.FC<{
  device?: DeviceKind;   // phone | tablet | laptop | monitor
  look?: DeviceLook;     // flat | real | screen — absent: real on a dark beat, flat on a light one
  steps?: Step[];        // the script, prepared by scripts/device_script.py — absent: the register's own demo
  camera?: 'still';      // turn the legibility push-in off
  placement?: Placement; // where the device stands: center | left | right
  kicker?: string;       // an optional spaced label above the device
}> = ({device = 'phone', look, steps: STEPS = DEMO_STEPS, camera, placement = 'center', kicker = ''} = {}) => {
  const t = useT();
  const span = useAnimSpan();
  const reduced = React.useContext(ReducedMotionContext);
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  if (!Array.isArray(STEPS) || !STEPS.length || kindOf(STEPS[0]) !== 'screen') {
    throw new Error('DeviceDemo needs `steps` opening with a `screen` step — the device would arrive showing ' +
      'nothing. Write the script in the storyboard; scripts/device_script.py checks and schedules it.');
  }
  const steps = scheduled(STEPS);
  const lk: DeviceLook = look ?? defaultLook(dna);
  const g = deviceGeometry(device, lk, W, H, placement, Boolean(kicker));
  const s = g.screen;
  const INK = dna?.fg ?? '#14171c', GROUND = dna?.bg ?? '#eef1f4', ACC = dna?.accent ?? '#3563e9';
  const BODY_FONT = dna?.fontBody ?? '"Inter", "Noto Sans SC", system-ui, sans-serif';
  const touch = isTouch(device);

  // ── which screen is up, and how far each long screenshot has scrolled ─────────────────────────────────
  const screens = steps.map((st, i) => ({st, i})).filter((x) => kindOf(x.st) === 'screen');
  const curIdx = Math.max(0, screens.reduce((acc, x, k) => ((x.st.t0 ?? 0) <= t ? k : acc), 0));
  const cur = screens[curIdx], prev = screens[curIdx - 1];
  const change = prev ? clamp01(seg(t, cur.st.t0!, cur.st.t1!)) : 1;
  const nextScreenAt = (i: number) => steps.findIndex((x, k) => k > i && kindOf(x) === 'screen');
  const offsetFor = (i: number): number => {
    const sc = steps[i];
    if (!sc.screen?.image || !sc.imageW || !sc.imageH) return 0;
    const range = scrollRangePx(sc.imageW, sc.imageH, s.w, s.h);
    const end = nextScreenAt(i) < 0 ? steps.length : nextScreenAt(i);
    let off = 0;
    for (let k = i + 1; k < end; k++) {
      const st = steps[k];
      if (kindOf(st) !== 'scroll') continue;
      const to = Math.min(range, off + (st.scroll ?? 0) * range);
      off = off + (to - off) * flingAt(seg(t, st.ta!, st.t1!));
    }
    return off;
  };
  const layer = (x: {st: Step; i: number}) => {
    const src = x.st.screen!;
    if (src.image) {
      if (!x.st.imageW || !x.st.imageH) {
        throw new Error('DeviceDemo: a screen image needs its size (`imageW`, `imageH`) — scripts/device_script.py ' +
          'reads it from the file; render through render_remotion.py.');
      }
      return <ScreenImage src={src.image} imageW={x.st.imageW} imageH={x.st.imageH} w={s.w} h={s.h} offsetPx={offsetFor(x.i)} />;
    }
    if (src.video) return <ScreenVideo src={src.video} spans={x.st.spans ?? []} w={s.w} h={s.h} />;
    return <DemoPage w={s.w} h={s.h} ink={INK} ground={dna?.surface ?? '#ffffff'} />;
  };
  const push = cur.st.via !== 'fade';

  // ── the gestures of the current screen ────────────────────────────────────────────────────────────────
  const end = nextScreenAt(cur.i) < 0 ? steps.length : nextScreenAt(cur.i);
  const gestures = steps.slice(cur.i + 1, end);
  const P = (p: Pt) => ({x: p[0] * s.w, y: p[1] * s.h});
  const cursorAt = (): {x: number; y: number; press: number} | null => {
    if (touch) return null;
    let pos = {x: s.w * 0.72, y: s.h * 0.86}, press = 0, seen = false;
    for (const st of gestures) {
      const k = kindOf(st);
      if (k !== 'click' && k !== 'tap' && k !== 'drag') continue;
      seen = true;
      const from = k === 'drag' ? P(st.drag!.from) : P((st.click ?? st.tap)!);
      const to = k === 'drag' ? P(st.drag!.to) : from;
      if (t < st.t0!) break;
      if (t < st.ta!) {
        const u = easeCursor(seg(t, st.t0!, st.ta!));
        return {x: pos.x + (from.x - pos.x) * u, y: pos.y + (from.y - pos.y) * u, press: 0};
      }
      const v = easeInOutCubic(seg(t, st.ta!, st.t1!));
      press = k === 'drag' ? (t <= st.t1! ? 1 : 0) : clamp01(1 - Math.abs(t - st.ta!) / Math.max(1e-6, (st.t1! - st.ta!) * 0.3));
      pos = {x: from.x + (to.x - from.x) * v, y: from.y + (to.y - from.y) * v};
    }
    return seen ? {...pos, press} : null;
  };
  const overlays: React.ReactNode[] = [];
  gestures.forEach((st, n) => {
    const k = kindOf(st);
    const u = seg(t, st.ta!, st.t1!);
    const size = touch ? s.w * 0.14 : s.w * 0.06;
    if (k === 'tap' || k === 'click' || k === 'mark') {
      const p = P((st.tap ?? st.click ?? st.mark)!);
      overlays.push(<TapRipple key={`g${n}`} x={p.x} y={p.y} u={u} color={ACC} size={size} />);
    } else if (k === 'drag' && touch && t >= st.ta! && t <= st.t1!) {
      const a = P(st.drag!.from), b = P(st.drag!.to), v = easeInOutCubic(u);
      overlays.push(<TapRipple key={`g${n}`} x={a.x + (b.x - a.x) * v} y={a.y + (b.y - a.y) * v} u={0.5} color={ACC} size={size} />);
    } else if (k === 'scroll' && touch && u > 0 && u < 0.35) {
      const v = u / 0.35;
      overlays.push(<TapRipple key={`g${n}`} x={s.w * 0.5} y={s.h * (0.72 - 0.3 * v)} u={0.5} color={ACC} size={size} />);
    } else if (k === 'type' && t >= st.ta!) {
      const f = st.field;
      if (!f) throw new Error('DeviceDemo: a `type` step needs its `field` — scripts/device_script.py measures it.');
      const chunks = typeChunks(st.type!);
      const text = chunks.slice(0, typedCount(t, st.ta!, st.t1!, chunks)).join('');   // @truncates: the typing reveal — every chunk is on screen by t1
      const [x0, y0, x1, y1] = f.box;
      const fw = (x1 - x0) * s.w, fh = (y1 - y0) * s.h;
      const px = f.textFrac ? f.textFrac * s.w : fh * 0.42;
      const pad = Math.min(fw, fh) * 0.35, caretW = Math.max(2, px * 0.08);
      const inset = Math.min(fw, fh) * 0.12;
      const shift = Math.max(0, textWidthPx(text, px) - (fw - 2 * pad - caretW * 3));
      const lit = caretOn(t < st.t1! ? null : framesBetween(st.t1!, t, span, ENTRY_T), reduced);
      overlays.push(
        <div key={`g${n}`} style={{position: 'absolute', left: x0 * s.w + inset, top: y0 * s.h + inset,
          width: fw - 2 * inset, height: fh - 2 * inset, background: f.bg, overflow: 'hidden',
          borderRadius: (fh - 2 * inset) * 0.3}}>
          <div style={{position: 'absolute', left: pad - inset - shift, top: 0, height: '100%', display: 'flex',
            alignItems: 'center', whiteSpace: 'pre', color: f.ink, font: `500 ${px}px/1 ${BODY_FONT}`}}>
            {text}
            <span style={{display: 'inline-block', width: caretW, height: px * 1.15, marginLeft: caretW,
              background: ACC, opacity: lit ? 1 : 0}} />
          </div>
        </div>);
    }
  });
  const cursor = cursorAt();
  if (cursor) overlays.push(<CursorArrow key="cursor" x={cursor.x} y={cursor.y} size={s.w * 0.035} press={cursor.press} />);

  // ── the legibility push-in, computed from what prepare() measured ─────────────────────────────────────
  const keys: CamKey[] = [{at: 0, x: W / 2, y: H / 2, s: 1}];
  if (camera !== 'still' && !reduced) {
    steps.forEach((st, i) => {
      if (!st.focus || !st.textFrac || !st.captionPx) return;
      const zoom = Math.min(spec.maxZoom, Math.max(1, st.captionPx / (st.textFrac * s.w)));
      if (zoom <= 1.01) return;
      const fx = s.x + st.focus[0] * s.w, fy = s.y + st.focus[1] * s.h;
      const last = keys[keys.length - 1];
      keys.push({at: st.t0!, x: last.x, y: last.y, s: last.s});
      keys.push({at: st.ta!, x: fx, y: fy, s: zoom});
      keys.push({at: st.t1!, x: fx, y: fy, s: zoom});
      const next = steps[i + 1];
      if (!next || !next.focus) keys.push({at: Math.min(1, st.t1! + (st.ta! - st.t0!)), x: W / 2, y: H / 2, s: 1});
    });
  }
  const cam = clampToPage(camAt(keys, t, easeInOutCubic), W, H, W, H);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? GROUND, overflow: 'hidden'}}>
      <AbsoluteFill style={{transformOrigin: '0 0',
        transform: `translate(${W / 2 - cam.x * cam.s}px, ${H / 2 - cam.y * cam.s}px) scale(${cam.s})`}}>
        <Device g={g} dna={dna}>
          {prev && change < 1 ? (
            <div style={{position: 'absolute', inset: 0, transform: push ? `translateX(${-change * s.w * 0.3}px)` : undefined}}>
              {layer(prev)}
            </div>
          ) : null}
          <div style={{position: 'absolute', inset: 0, opacity: push ? 1 : change,
            transform: push && prev ? `translateX(${(1 - change) * s.w}px)` : undefined}}>
            {layer(cur)}
          </div>
          {overlays}
        </Device>
      </AbsoluteFill>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', color: dna?.dim ?? '#5b6472',
          font: `600 ${Math.round(Math.min(W, H) * 0.022)}px/1 ${dna?.fontMono ?? 'ui-monospace, monospace'}`,
          letterSpacing: dna?.labelSpacing ?? '0.12em', textTransform: dna?.uppercaseLabels ? 'uppercase' : 'none'}}>
          {kicker}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 5: Run the render tests**

Run: `python3 -m pytest tests/test_device_demo.py -q`
Expected: all pass. If a geometry assertion is off, compare `device_geometry.geometry()` with the render's screen by eye in the saved PNG under the pytest tmp dir before touching either side — the parity test in Task 5 already holds the two geometries together.

- [ ] **Step 6: Write the card** — `remotion/cards/DeviceDemo.md`:

```markdown
# DeviceDemo

**Identity:** a phone, tablet, laptop or monitor showing the product's OWN screens — the user's screenshots or recording — and performing one operation on them: type into a field, tap, scroll, drag. Each step happens on the word the narration says; the camera pushes in wherever a screenshot's text would be too small to read.

**Use when:** the beat's claim is how an interface is USED — "search, open, scroll to it" — and real screens exist. **Not when:** there are no real screens (a concept, an unbuilt product — use an interface register such as `SurfaceCarousel`, or wait for the app templates); not a list of features in one place (`PointerTour`); not the product as an object with nothing done on it (`DeviceHero`).

**Motion core:** the device arrives with its first screen; then only the steps move — a ripple where a finger lands, typed words at the caret, a fling that settles. The push-in is computed, not styled: it zooms exactly as far as the target's text needs to match the caption, capped at 4×.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, tablet, laptop or monitor | touch devices tap with a ring; laptop and monitor move a cursor |
| `look` | flat, real or screen | absent: real on a dark beat, flat on a light one; `screen` drops the body entirely |
| `steps` | the script — `screen`, `type`, `tap`/`click`, `scroll`, `drag`, `mark` — prepared by `scripts/device_script.py` | each step on its cue; too many for the beat is a refusal in seconds, never a squeeze |
| `camera` | `"still"` turns the push-in off | the whole device stays in frame; small text stays small |
| `placement` | center, left or right | where the device stands in the content zone |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- A text target that is not in the screenshot, or is there twice without `nth`, is refused with the text that WAS recognised — the ring must land on what the film names.
- A `type` step paints the field's own background over its placeholder before typing; without that the placeholder and the typed words both show.
- A long screenshot scrolls only within its real overflow; a fling may overshoot 4% and springs back.
- The standalone demo is skeleton bars with no text, so no demo copy exists to leak into a film.

**Reference:** `remotion/src/shots/DeviceDemo.tsx`

**Provenance:** product-ui. **Family:** A.
```

Leave the `**Measured:**` line and the `**Ground:**` part for Task 12, which writes them from the measurements.

- [ ] **Step 7: Fill the LIBRARY entry the scaffold wrote**

In `remotion/LIBRARY.md`, family A, replace the scaffold's placeholder line for DeviceDemo with:

```markdown
N. **DeviceDemo** — a phone, tablet, laptop or monitor showing the product's OWN screenshots or recording, performing one operation on them — type, tap, scroll, drag — each on the narration's words, the camera pushing in wherever the text would be too small. *Use: how an interface is used, when real screens exist.* `device, look, steps, camera, placement, kicker` · steps are prepared by `scripts/device_script.py`; too many for the beat is refused in seconds.
```

(keep the number `N` the scaffold assigned).

- [ ] **Step 8: Run the library tests**

Run: `python3 -m pytest tests/test_shot_cards.py tests/test_library_signatures.py tests/test_device_demo.py -q && python3 scripts/content_contract_qa.py DeviceDemo && python3 scripts/register_shot.py DeviceDemo --check`
Expected: all pass; no contract finding; `--check` reports nothing missing.

- [ ] **Step 9: Commit**

```bash
git add remotion/src/shots/DeviceDemo.tsx remotion/cards/DeviceDemo.md remotion/src/registry.ts remotion/src/Root.tsx remotion/src/runtime/shotLuma.ts scripts/shot_director.py remotion/LIBRARY.md tests/test_device_demo.py
git commit -m "DeviceDemo: one operation on the product's own screens, each step on the narration's words

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 10: DeviceHero

**Files:**
- Scaffold, then write: `remotion/src/shots/DeviceHero.tsx`, `remotion/cards/DeviceHero.md`
- Modified by the scaffold: `registry.ts`, `Root.tsx`, `shotLuma.ts`, `shot_director.py`, `LIBRARY.md`
- Test: `tests/test_device_hero.py`

**Interfaces:**
- Consumes: Tasks 5–6; `motion.useT`, `seg`, `easeOutCubic`, `ENTRY_T`.
- Produces: the register `DeviceHero` with props `device, look, screen, placement, kicker`; `screen` is `{image, imageW, imageH}` or `{video, spans}` (prepared) or `{page: 'demo'}`.

- [ ] **Step 1: Scaffold**

Run:
```bash
python3 scripts/register_shot.py DeviceHero A --use-when "the product itself on its device, one screen shown whole — the beat that says this is it" --provenance product-ui
python3 scripts/register_shot.py DeviceHero --check
```

- [ ] **Step 2: Write the failing tests** — `tests/test_device_hero.py`:

```python
"""DeviceHero: the device settles and shows its screen; a recording plays the moment the beat maps to it."""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")


def _still(tmp_path, props, frame, name):
    pf = tmp_path / (name + ".json")
    pf.write_text(json.dumps(dict(props, dna="product"), ensure_ascii=False), encoding="utf-8")
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceHero", png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + str(pf), "--public-dir=" + str(tmp_path)],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
    return png


@needs_toolchain
def test_a_recording_shows_the_moment_its_span_maps_to(tmp_path):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    import device_geometry as dg
    v = str(tmp_path / "rec.mp4")
    # each frame's grey level encodes its index (N*2), so the rendered colour says which moment is showing
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=390x844:r=30:d=4,geq=lum='min(255,N*2)':cb=128:cr=128", "-pix_fmt", "yuv420p", v],
                   check=True)
    screen = {"video": "rec.mp4", "spans": [{"f0": 0, "f1": 150, "v0": 1.0, "v1": 3.0}]}
    png = _still(tmp_path, {"device": "phone", "look": "flat", "screen": screen}, 75, "vid")
    s = dg.geometry("phone", "flat", 1920, 1080)["screen"]
    a = np.asarray(Image.open(png).convert("L"), dtype=float)
    centre = a[s["y"] + s["h"] // 2 - 5:s["y"] + s["h"] // 2 + 5, s["x"] + s["w"] // 2 - 5:s["x"] + s["w"] // 2 + 5]
    # frame 75 of the beat maps to 1.0 + 75/150 * 2.0 = 2.0 s = source frame 60 -> grey 120
    assert abs(float(centre.mean()) - 120) < 12, centre.mean()


@needs_toolchain
def test_the_standalone_demo_renders(tmp_path):
    _still(tmp_path, {}, 120, "demo")
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_device_hero.py -q`
Expected: FAIL (the stub draws its name).

- [ ] **Step 4: Write `remotion/src/shots/DeviceHero.tsx`** (replacing the stub)

```tsx
// SHOT · DeviceHero — the product on its device, its screen shown whole: the beat that says "this is it".
// Family A. The device rises into place and, in the realistic look, turns a few degrees toward the viewer and
// settles; nothing is performed on it (that is DeviceDemo). The screen is the user's screenshot or recording,
// prepared by scripts/device_script.py, or — standalone — the register's own skeleton page with no text.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic, ENTRY_T} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {TITLE_Y} from '../runtime/layout';
import {deviceGeometry, defaultLook, Device, type DeviceKind, type DeviceLook, type Placement} from '../runtime/device';
import {ScreenImage, ScreenVideo, type VideoSpan} from '../runtime/screen';

export const DURATION = 150;

type HeroScreen = {image?: string; imageW?: number; imageH?: number; video?: string; spans?: VideoSpan[]; page?: 'demo'};

export const DeviceHero: React.FC<{
  device?: DeviceKind;   // phone | tablet | laptop | monitor
  look?: DeviceLook;     // flat | real | screen — absent: real on a dark beat, flat on a light one
  screen?: HeroScreen;   // the screenshot or recording, prepared by scripts/device_script.py
  placement?: Placement; // center | left | right
  kicker?: string;       // an optional spaced label above the device
}> = ({device = 'laptop', look, screen: SCREEN = {page: 'demo'}, placement = 'center', kicker = ''} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const lk: DeviceLook = look ?? defaultLook(dna);
  const g = deviceGeometry(device, lk, W, H, placement, Boolean(kicker));
  const s = g.screen;
  const enter = easeOutCubic(seg(t, ENTRY_T, 0.32));
  const turn = lk === 'real' ? 14 - 9 * enter : 0;
  if (SCREEN.image && (!SCREEN.imageW || !SCREEN.imageH)) {
    throw new Error('DeviceHero: a screen image needs its size (`imageW`, `imageH`) — scripts/device_script.py ' +
      'reads it from the file; render through render_remotion.py.');
  }
  const content = SCREEN.image
    ? <ScreenImage src={SCREEN.image} imageW={SCREEN.imageW!} imageH={SCREEN.imageH!} w={s.w} h={s.h} />
    : SCREEN.video
      ? <ScreenVideo src={SCREEN.video} spans={SCREEN.spans ?? []} w={s.w} h={s.h} />
      : (
        <div style={{position: 'absolute', left: 0, top: 0, width: s.w, height: s.h, background: dna?.surface ?? '#ffffff'}}>
          {Array.from({length: 6}).map((_, i) => (   // @decor: skeleton rows of the register's own demo screen — no film ever sees them
            <div key={i} style={{position: 'absolute', left: s.w * 0.08, top: s.h * (0.14 + i * 0.12), width: s.w * 0.84,
              height: s.h * 0.07, borderRadius: s.h * 0.012, background: mix(dna?.surface ?? '#ffffff', dna?.fg ?? '#14171c', 0.07)}} />
          ))}
        </div>
      );
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? '#eef1f4', perspective: Math.round(W * 1.2)}}>
      <AbsoluteFill style={{opacity: enter, transformOrigin: `${s.x + s.w / 2}px ${s.y + s.h / 2}px`,
        transform: `translateY(${(1 - enter) * H * 0.04}px) rotateY(${turn}deg)`}}>
        <Device g={g} dna={dna}>{content}</Device>
      </AbsoluteFill>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', color: dna?.dim ?? '#5b6472',
          font: `600 ${Math.round(Math.min(W, H) * 0.022)}px/1 ${dna?.fontMono ?? 'ui-monospace, monospace'}`,
          letterSpacing: dna?.labelSpacing ?? '0.12em', textTransform: dna?.uppercaseLabels ? 'uppercase' : 'none'}}>
          {kicker}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest tests/test_device_hero.py -q`
Expected: all pass.

- [ ] **Step 6: Write the card** — `remotion/cards/DeviceHero.md`:

```markdown
# DeviceHero

**Identity:** the product on its device — phone, tablet, laptop or monitor — rising into place with its screen shown whole: the user's own screenshot or recording. In the realistic look it turns a few degrees toward the viewer and settles.

**Use when:** the beat says THIS is the product — an introduction, a reveal, a return to the product after an argument. **Not when:** something is done on the screen (`DeviceDemo`); not several surfaces of one product (`SurfaceCarousel`); not when there is no real screen to show.

**Motion core:** one rise and, in the realistic look, one small turn — both finished by a third of the beat; then the device holds and the screen carries the frame (a recording keeps playing).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `device` | phone, tablet, laptop or monitor | the laptop is the default: a hero is usually the whole product |
| `look` | flat, real or screen | only `real` turns; absent: real on a dark beat, flat on a light one |
| `screen` | the screenshot or recording, prepared by `scripts/device_script.py` | a recording is spread over the beat, at most 2× speed |
| `placement` | center, left or right | where the device stands |
| `kicker` | a spaced label above the device | moves the device below the title band |

**Known traps:**
- A screenshot wider than the device's screen is refused: it is a capture of another device.
- A recording longer than the beat can hold at 2× is refused rather than sped past legibility.

**Reference:** `remotion/src/shots/DeviceHero.tsx`

**Provenance:** product-ui. **Family:** A.
```

- [ ] **Step 7: Fill the LIBRARY entry** (family A, the scaffold's number):

```markdown
N. **DeviceHero** — the product on its device with its own screenshot or recording shown whole; it rises into place and, in the realistic look, turns a few degrees and settles. *Use: "this is the product" — an introduction or a reveal.* `device, look, screen, placement, kicker` · the screen is prepared by `scripts/device_script.py`.
```

- [ ] **Step 8: Run the library tests**

Run: `python3 -m pytest tests/test_shot_cards.py tests/test_library_signatures.py tests/test_device_hero.py -q && python3 scripts/content_contract_qa.py DeviceHero && python3 scripts/register_shot.py DeviceHero --check`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add remotion/src/shots/DeviceHero.tsx remotion/cards/DeviceHero.md remotion/src/registry.ts remotion/src/Root.tsx remotion/src/runtime/shotLuma.ts scripts/shot_director.py remotion/LIBRARY.md tests/test_device_hero.py
git commit -m "DeviceHero: the product on its device, its own screen shown whole

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 11: prepare() — from the storyboard to what the registers draw

**Files:**
- Modify: `scripts/device_script.py` (add `prepare`, `check_slide`)
- Modify: `scripts/render_remotion.py` (`build_scenes` gains `frame=(W, H)` and `lang` keyword args and calls `prepare`; `film_props` passes them)
- Modify: `scripts/validate.py` (`_check_remotion`, beside the unknown-prop check)
- Test: `tests/test_device_wiring.py`

**Interfaces:**
- Consumes: Tasks 1–4 (`check_shape`, `schedule`, `DeviceScriptError`, `screen_media.*`, `screen_text.recognize`, `find_text`), Task 5 (`device_geometry.geometry`), `render_remotion.resolve_cue_props`, `frame_at_t`, `_caption_band.aspect_table`.
- Produces: `prepare(props, *, shot, out_dir, dur_frames, fps, W, H, lang, recognizer=None) -> (props, warnings)`; `check_slide(slide, out_dir, meta) -> (errors: list[str], warnings: list[str])`.

- [ ] **Step 1: Write the failing tests** — `tests/test_device_wiring.py`:

```python
"""From the storyboard to what the registers draw: every text target becomes a point, every step a window,
every field a box, every recording a mapping — or the beat is refused with every reason at once."""
import json
import os
import sys

import pytest
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import device_script as ds          # noqa: E402

FONT = os.path.join(_ROOT, "assets", "fonts", "NotoSansSC-Subset.ttf")
FPS = 30


def _ui(tmp_path, name="ui.png", h=2532):
    im = Image.new("RGB", (1170, h), "white")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    d.text((110, 232), "搜索反馈", fill=(140, 147, 160), font=ImageFont.truetype(FONT, 46))
    d.text((90, 700), "反馈汇总", fill=(20, 23, 28), font=ImageFont.truetype(FONT, 46))
    (tmp_path / "ui").mkdir(exist_ok=True)
    im.save(str(tmp_path / "ui" / name))
    return "ui/" + name


def _fake_recognizer(path):
    return [{"text": "搜索反馈", "box": [110 / 1170, 232 / 2532, 300 / 1170, 280 / 2532]},
            {"text": "反馈汇总", "box": [90 / 1170, 700 / 2532, 290 / 1170, 750 / 2532]}]


def test_prepare_fills_everything_the_register_needs(tmp_path):
    img = _ui(tmp_path)
    props = {"device": "phone", "steps": [
        {"screen": {"image": img}}, {"type": "上周的反馈", "into": {"text": "搜索反馈"}},
        {"tap": {"text": "反馈汇总"}, "at": 0.7}]}
    out, warns = ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS,
                            W=1920, H=1080, lang="zh", recognizer=_fake_recognizer)
    s0, s1, s2 = out["steps"]
    assert s0["imageW"] == 1170 and s0["imageH"] == 2532
    assert isinstance(s1["into"], list) and s1["field"]["bg"].startswith("#") and s1["field"]["ink"] == "#111111"
    assert isinstance(s2["tap"], list) and abs(s2["tap"][1] - 725 / 2532) < 0.01
    assert all(k in s2 for k in ("t0", "ta", "t1", "focus", "textFrac", "captionPx"))
    assert s2["ta"] == pytest.approx(0.7, abs=2e-3)


def test_every_problem_is_reported_at_once(tmp_path):
    props = {"device": "phone", "steps": [{"screen": {"image": "missing.png"}}, {"tap": {"text": "不在图里"}}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=180, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "missing.png" in str(e.value)


def test_a_target_scrolled_out_of_view_is_refused(tmp_path):
    img = _ui(tmp_path, "long.png", h=6000)
    props = {"device": "phone", "steps": [{"screen": {"image": img}}, {"scroll": 1.0}, {"tap": [0.5, 0.1]},
                                          {"tap": {"text": "反馈汇总"}}]}
    with pytest.raises(ds.DeviceScriptError) as e:
        ds.prepare(props, shot="DeviceDemo", out_dir=str(tmp_path), dur_frames=300, fps=FPS, W=1920, H=1080,
                   lang="zh", recognizer=_fake_recognizer)
    assert "scroll" in str(e.value) and "view" in str(e.value)


def test_validate_reports_a_device_beat_by_name(tmp_path):
    import validate as v
    img = _ui(tmp_path)
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    board = {"meta": {"language": "zh", "renderer": "remotion", "design_dna": "product", "captions": False},
             "slides": [{"index": 1, "shot": "DeviceDemo", "narration": "先搜索。", "audio": "audio/01.mp3",
                         "duration": 1.0, "image": "ui/ui.png",
                         "shot_props": {"device": "phone", "steps": [{"screen": {"image": img}}] +
                                        [{"tap": [0.5, 0.5]}] * 6}}]}
    errs = v.evaluate(board, str(tmp_path))["errors"]
    assert any("scene #1" in e and "beat" in e for e in errs), errs
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_device_wiring.py -q`
Expected: FAIL — `module 'device_script' has no attribute 'prepare'`.

- [ ] **Step 3: Add `prepare` and `check_slide` to `scripts/device_script.py`**

```python
def _viewport(y_img, image_w, image_h, device, acc):
    """Image fraction y -> fraction of the VISIBLE screen, after `acc` of the overflow has been scrolled."""
    rw, rh = SPEC["screenRatio"][device]
    disp_over_screen = (float(image_h) / image_w) * (float(rw) / rh)       # displayed image height / screen height
    return y_img * disp_over_screen - acc * max(0.0, disp_over_screen - 1.0)


def _image_y(y_view, image_w, image_h, device, acc):
    rw, rh = SPEC["screenRatio"][device]
    d = (float(image_h) / image_w) * (float(rw) / rh)
    return (y_view + acc * max(0.0, d - 1.0)) / d


def prepare(props, *, shot, out_dir, dur_frames, fps, W, H, lang, recognizer=None):
    """Authored props (cues already turned into useT times by render_remotion.resolve_cue_props) -> the props
    the register draws, and the legibility warnings. Raises DeviceScriptError with EVERY problem found."""
    import subprocess
    import render_remotion as rr
    import screen_media as sm
    import screen_text as stx
    import device_geometry as dg
    device = props.get("device", "phone" if shot == "DeviceDemo" else "laptop")
    probs, warns = [], []
    if shot == "DeviceHero":
        src = dict(props.get("screen") or {"page": "demo"})
        p = os.path.join(out_dir, str(src.get("image") or src.get("video") or ""))
        if src.get("image"):
            if not os.path.isfile(p):
                raise DeviceScriptError(["the screen image %s does not exist" % src["image"]])
            f = sm.image_facts(p)
            sm.fit_kind(f, device)
            src.update(imageW=f["w"], imageH=f["h"])
        elif src.get("video"):
            if not os.path.isfile(p):
                raise DeviceScriptError(["the recording %s does not exist" % src["video"]])
            f = sm.video_facts(p)
            frm, to = float(src.get("from", 0)), float(src.get("to", f["duration"]))
            probs += sm.check_video(f, device, frm, to)
            beat_s = dur_frames / float(fps)
            if (to - frm) / beat_s > SPEC["maxVideoRate"] + 1e-6:
                probs.append("the recording's %.1f s would play at %.1fx to fit a %.1f s beat — trim it (the cap is %.0fx)"
                             % (to - frm, (to - frm) / beat_s, beat_s, SPEC["maxVideoRate"]))
            src = {"video": src["video"], "spans": [{"f0": 0, "f1": dur_frames, "v0": frm, "v1": to}]}
        if probs:
            raise DeviceScriptError(probs)
        return dict(props, screen=src), warns

    probs += check_shape(props)
    if probs:
        raise DeviceScriptError(probs)
    rec = recognizer or (lambda path: stx.recognize(path, cache_dir=os.path.join(out_dir, ".cache")))
    steps = [dict(s) for s in props["steps"]]
    cur, cur_path, acc, facts = None, None, 0.0, {}
    screen_w = dg.geometry(device, props.get("look") or "flat", W, H)["screen"]["w"]
    caption = sm.caption_ink_px(lang, W, H)
    measured, gestures = 0, 0
    for i, st in enumerate(steps):
        k, where = step_kind(st), "step %d (%s)" % (i + 1, step_kind(st))
        if k == "screen":
            src = st["screen"]
            cur, acc = src, 0.0
            if "image" in src:
                cur_path = os.path.join(out_dir, src["image"])
                if not os.path.isfile(cur_path):
                    probs.append("%s: the screenshot %s does not exist" % (where, src["image"]))
                    cur_path = None
                    continue
                try:
                    f = facts[cur_path] = sm.image_facts(cur_path)
                    sm.fit_kind(f, device)
                    st.update(imageW=f["w"], imageH=f["h"])
                except DeviceScriptError as e:
                    probs += ["%s: %s" % (where, p) for p in e.problems]
            elif "video" in src:
                cur_path = None
                vp = os.path.join(out_dir, src["video"])
                if not os.path.isfile(vp):
                    probs.append("%s: the recording %s does not exist" % (where, src["video"]))
                else:
                    f = sm.video_facts(vp)
                    probs += ["%s: %s" % (where, p) for p in
                              sm.check_video(f, device, float(src.get("from", 0)), float(src["to"]))]
            else:
                cur_path = None
            continue
        if k == "scroll":
            acc = min(1.0, acc + float(st["scroll"]))
            continue
        if cur_path is None or cur_path not in facts:
            if k in ("type", "tap", "click", "drag", "mark") and any(isinstance(v, dict) and "text" in v
                                                                    for v in (st.get(k), st.get("into"))):
                probs.append("%s: a text target needs a screenshot on the screen" % where)
            continue
        f = facts[cur_path]
        key = "into" if k == "type" else ("drag" if k == "drag" else k)
        targets = [st[key]["from"], st[key]["to"]] if k == "drag" else [st[key]]
        resolved = []
        for tg in targets:
            if isinstance(tg, dict):
                try:
                    hit = stx.find_text(rec(cur_path), tg["text"], tg.get("nth"))
                except DeviceScriptError as e:
                    probs += ["%s: %s" % (where, p) for p in e.problems]
                    continue
                y = _viewport(hit["y"], f["w"], f["h"], device, acc)
                if not 0 <= y <= 1:
                    probs.append("%s: %r is out of view at this point in the scroll — scroll first" % (where, tg["text"]))
                    continue
                resolved.append(([hit["x"], y], (hit["box"][3] - hit["box"][1]) * f["h"]))
            else:
                resolved.append((list(tg), None))
        if len(resolved) != len(targets):
            continue
        if k == "drag":
            st["drag"] = {"from": resolved[0][0], "to": resolved[1][0]}
        else:
            st[key] = resolved[0][0]
        (x, y), ocr_h = resolved[0]
        y_img = _image_y(y, f["w"], f["h"], device, acc)
        text_px = ocr_h if ocr_h else sm.text_band_px(cur_path, x, y_img)
        gestures += 1
        if k == "type":
            fld = sm.field_at(cur_path, x, y_img)
            b = fld["box"]
            st["field"] = {"box": [b[0], _viewport(b[1], f["w"], f["h"], device, acc), b[2],
                                   _viewport(b[3], f["w"], f["h"], device, acc)],
                           "bg": fld["bg"], "ink": fld["ink"],
                           "textFrac": (fld["textPx"] / f["w"]) if fld["textPx"] else None}
            text_px = fld["textPx"] or text_px
        if text_px:
            measured += 1
            st.update(focus=[x, y], textFrac=text_px / f["w"], captionPx=caption)
            need = caption / (text_px * screen_w / f["w"])
            if need > SPEC["maxZoom"] and props.get("camera") != "still":
                warns.append("%s: the text there needs a %.1fx push-in to reach caption size; the cap is %.0fx — "
                             "use a tighter screenshot or a larger device" % (where, need, SPEC["maxZoom"]))
    if probs:
        raise DeviceScriptError(probs)
    if gestures and measured < gestures:
        warns.append("legibility: measured %d of %d gesture targets — the rest have no text height and get no "
                      "push-in" % (measured, gestures))
    steps = schedule(steps, dur_frames, fps)
    for i, st in enumerate(steps):
        src = st.get("screen") or {}
        if "video" in src:
            nxt = next((s for s in steps[i + 1:] if step_kind(s) == "screen"), None)
            f_end = rr.frame_at_t(dur_frames, nxt["t0"]) if nxt else float(dur_frames)
            pts = [(rr.frame_at_t(dur_frames, st["ta"]), float(src.get("from", 0)))]
            for m in steps[i + 1:]:
                if step_kind(m) == "screen":
                    break
                if step_kind(m) == "mark" and isinstance(m.get("video"), (int, float)):
                    pts.append((rr.frame_at_t(dur_frames, m["ta"]), float(m["video"])))
            pts.append((f_end, float(src["to"])))
            spans = []
            for (f0, v0), (f1, v1) in zip(pts, pts[1:]):
                rate = (v1 - v0) / max(1e-6, (f1 - f0) / float(fps))
                if v1 < v0 or rate > SPEC["maxVideoRate"] + 1e-6:
                    raise DeviceScriptError(["step %d (screen): the recording would run at %.1fx between frames %d "
                                             "and %d — the cap is %.0fx and it may not run backwards"
                                             % (i + 1, rate, f0, f1, SPEC["maxVideoRate"])])
                spans.append({"f0": f0, "f1": f1, "v0": v0, "v1": v1})
            st["spans"] = spans
            # A mark pushes in by the same rule as a tap — the text height at its point — measured on the
            # frame the recording is showing at that moment (a recording has no other text to measure).
            vp = os.path.join(out_dir, src["video"])
            vw = sm.video_facts(vp)["w"]
            for m in steps[i + 1:]:
                if step_kind(m) == "screen":
                    break
                if step_kind(m) != "mark":
                    continue
                fm = rr.frame_at_t(dur_frames, m["ta"])
                sp = next((x for x in spans if x["f0"] <= fm <= x["f1"]), spans[-1])
                vt = sp["v0"] + (sp["v1"] - sp["v0"]) * (fm - sp["f0"]) / max(1e-6, sp["f1"] - sp["f0"])
                still = os.path.join(out_dir, ".cache", "device", "%s-%.3f.png" % (os.path.basename(vp), vt))
                os.makedirs(os.path.dirname(still), exist_ok=True)
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % vt, "-i", vp, "-frames:v", "1",
                                still], check=True)
                px = sm.text_band_px(still, m["mark"][0], m["mark"][1])
                if px:
                    m.update(focus=list(m["mark"]), textFrac=px / float(vw), captionPx=caption)
    return dict(props, steps=steps), warns


def check_slide(slide, out_dir, meta):
    """(errors, warnings) for one device beat, exactly as a render would meet them."""
    import render_remotion as rr
    from _caption_band import aspect_table
    shot, sp = slide.get("shot"), slide.get("shot_props") or {}
    dur, audio = slide.get("duration"), slide.get("audio")
    if not dur:
        return [], []                                   # pre-TTS: timing is checked once the audio exists
    fps = 30
    W, H = aspect_table().get(str(meta.get("aspect") or "16:9"), (1920, 1080))
    try:
        props = rr.resolve_cue_props(sp, out_dir, audio, slide.get("narration") or "", float(dur), fps)
        _out, warns = prepare(props, shot=shot, out_dir=out_dir, dur_frames=int(round(float(dur) * fps)), fps=fps,
                              W=W, H=H, lang=meta.get("language") or "zh")
        return [], warns
    except SystemExit as e:
        return [str(e)], []
    except DeviceScriptError as e:
        return ["device beat: " + p for p in e.problems], []
```

- [ ] **Step 4: Wire the build** — in `scripts/render_remotion.py`:

Change the `build_scenes` signature to `def build_scenes(slides, out_dir, valid, fps=30, frame=(1920, 1080), lang="zh"):` and, directly after the existing line `props = resolve_cue_props(props, out_dir, audio, s.get("narration") or s.get("script") or "", dur, fps)`, add:

```python
        if shot in ("DeviceDemo", "DeviceHero"):
            import device_script as _ds
            try:
                props, _warns = _ds.prepare(props, shot=shot, out_dir=out_dir, dur_frames=int(round(dur * fps)),
                                            fps=fps, W=frame[0], H=frame[1], lang=lang)
            except _ds.DeviceScriptError as e:
                raise RuntimeError("scene #%s (%s): %s" % (idx, shot, "; ".join(e.problems)))
            for w in _warns:
                print("[render_remotion] scene #%s: %s" % (idx, w))
```

In `film_props`, compute the frame and pass it: before `scenes = build_scenes(...)` add

```python
    from _caption_band import aspect_table
    _aspect = "9:16" if vertical else str((data.get("meta") or {}).get("aspect") or "16:9")
    _frame = aspect_table().get(_aspect, (1920, 1080))
```

and call `build_scenes(slides, out_dir, valid, fps, frame=_frame, lang=(data.get("meta") or {}).get("language") or "zh")`.

- [ ] **Step 5: Wire validate** — in `scripts/validate.py`, inside `_check_remotion`, directly after the block that reports `{shot} has no prop` (the `if isinstance(sp, dict) and shot in _declared_props_library():` block), add:

```python
        # A DEVICE BEAT'S SCRIPT is checked the way the render will meet it: shapes, files, text targets, time.
        if shot in ("DeviceDemo", "DeviceHero") and isinstance(sp, dict) and out_dir:
            import device_script as _dsx
            _derr, _dwarn = _dsx.check_slide(s, out_dir, meta)
            errors.extend(f"{tag}: {m}" for m in _derr)
            warnings.extend(f"{tag}: {m}" for m in _dwarn)
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_device_wiring.py tests/test_device_script.py tests/test_cue_lists.py -q`
Expected: all pass.

- [ ] **Step 7: Mutation check — each guard's test must fail against its mutant**

Run this from the repo root. It applies one mutant at a time, runs the test that claims to guard it, requires a
FAILURE, and restores the file even if interrupted. A mutant that SURVIVES is a test that cannot fail: fix the
test (or show the mutant is equivalent — the change cannot alter any output — and say why) before committing.

```bash
python3 - <<'EOF'
import subprocess
MUTANTS = [
  ("scripts/device_script.py", "        if slack < -1e-6:\n", "        if False:\n",
   "tests/test_device_script.py::test_a_short_beat_says_how_much_time_is_missing"),
  ("scripts/device_script.py", "    return y_img * disp_over_screen - acc * max(0.0, disp_over_screen - 1.0)",
   "    return y_img * disp_over_screen", "tests/test_device_wiring.py::test_a_target_scrolled_out_of_view_is_refused"),
  ("scripts/screen_text.py", "    if nth is None and len(hits) > 1:", "    if False:",
   "tests/test_screen_text.py::test_text_found_twice_needs_nth_and_nth_picks"),
  ("scripts/render_remotion.py", "                pos = p + len(phrase)", "                pos = 0",
   "tests/test_cue_lists.py::test_a_cue_said_only_before_the_previous_one_is_an_error"),
  ("scripts/screen_media.py", "    if a > s * (1 + tol):", "    if False:",
   "tests/test_screen_media.py::test_a_long_screenshot_is_long_and_a_wide_one_is_refused"),
]
for path, a, b, test in MUTANTS:
    src = open(path, encoding="utf-8").read()
    assert src.count(a) == 1, (path, a)
    try:
        open(path, "w", encoding="utf-8").write(src.replace(a, b, 1))
        r = subprocess.run(["python3", "-m", "pytest", "-q", test], capture_output=True, text=True)
        print("%-9s %s" % ("KILLED" if r.returncode else "SURVIVED", test))
    finally:
        open(path, "w", encoding="utf-8").write(src)
EOF
```
Expected: five lines, every one `KILLED`.

- [ ] **Step 8: Commit**

```bash
git add scripts/device_script.py scripts/render_remotion.py scripts/validate.py tests/test_device_wiring.py
git commit -m "Device beats are prepared from the storyboard: targets to points, steps to windows, fields measured

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

---

### Task 12: Library integration, measurements, guidance

**Files:**
- Modify: `remotion/register_energy.json`, `remotion/prop_reach.json`, `remotion/_ground_luma.json`, `remotion/_ground_reach.json`, `remotion/src/runtime/shotLuma.ts` (via the measurement scripts)
- Modify: `remotion/cards/DeviceDemo.md`, `DeviceHero.md` (Measured / Ground lines)
- Modify: `scripts/shot_director.py` (`CANDIDATES`), `agents/shot-director.md`, `SKILL.md`

**Interfaces:**
- Consumes: everything above.
- Produces: fully measured, registered registers; guidance that reaches the shot director and the interview.

- [ ] **Step 1: Measure the new registers** (nothing else may be editing registers or sweeping)

Run:
```bash
python3 scripts/measure_ground_luma.py --only DeviceDemo,DeviceHero --luma --emit
python3 scripts/measure_ground_luma.py --only DeviceDemo,DeviceHero --emit
python3 scripts/register_energy.py --only DeviceDemo,DeviceHero
python3 scripts/prop_reach.py --only DeviceDemo,DeviceHero
python3 scripts/measure_ground_reach.py --stale
python3 scripts/cjk_type_qa.py --only DeviceDemo --all-aspects
python3 scripts/cjk_type_qa.py --only DeviceHero --all-aspects
```
Expected: the SHOT_LUMA and DNA_GROUND_TOKEN placeholders for both are replaced with measured values; both manifests gain two rows; `--stale` lists nothing (apply per its help text if it lists these two); `cjk_type_qa` reports no finding (the demo screens carry no text).

- [ ] **Step 2: Write the measured lines into both cards**

Read the two rows in `remotion/register_energy.json` and append to each card, in the exact form the other cards use:

```markdown
**Measured:** <ink>% ink (clip median) · <footprint>% footprint · <motion> motion · <settled ink>% ink on the settled frame.
```

and complete the provenance line with `**Ground:** \`<token>\` (\`DNA_GROUND_TOKEN\`), measured <luma>.` from `shotLuma.ts`. Copy the numbers from the files; do not round or restate them from memory.

- [ ] **Step 3: Let the shot director reach them** — in `scripts/shot_director.py`, add `"DeviceDemo"` to the `"sequence"` list in `CANDIDATES` and `"DeviceHero"` to the `"statement"` list. Then add to `agents/shot-director.md`, as its own section after the register-choice guidance:

```markdown
## Device beats — when the narration performs something in the product

Cast `DeviceDemo` when the beat says how the product is USED ("search last week's feedback, open the summary,
scroll to the pattern") AND the film has the product's real screens (screenshots or a recording in the out
dir). Write `shot_props.steps` as a script: open with `{"screen": {"image": "..."}}`, then one step per action
the narration names, each with `"at": {"cue": "<the words>"}`. Target by text where you can
(`{"tap": {"text": "反馈汇总"}}`), by `[x, y]` otherwise. Cast `DeviceHero` for "this is the product" with one
screen. Never invent a screen: with no real screenshots, choose an interface register instead and say so.
`scripts/device_script.py <out_dir>` prints every device beat's schedule and every problem before a render.
```

- [ ] **Step 4: Document the registers and ask for the material** — in `SKILL.md`:

1. In the cinematic-tier entry (after the per-beat render paragraph), add:

```markdown
  **DEVICES AND THE PRODUCT'S OWN SCREENS.** `DeviceDemo` performs one operation — type, tap, scroll, drag — on
  a phone, tablet, laptop or monitor showing the user's own screenshots or recording, each step on the words
  the narration says; `DeviceHero` shows the product on its device with one screen whole. The step script is
  written in `shot_props.steps` and checked and scheduled by `scripts/device_script.py` (text targets are found
  in the screenshot on a Mac; too many steps for a beat is refused in seconds). Spec:
  `docs/superpowers/specs/2026-09-26-device-layer-design.md`.
```

2. In interview question ⑥ (Grounding), after its menu, add one sentence: `When the purpose is a how-to or a launch of a real product, ask for screenshots or a screen recording of the flow the film describes — the device registers draw the product's OWN screens and will not invent one.`

- [ ] **Step 5: Run the whole suite on this exact tree**

Run: `python3 -m pytest tests -q -p no:cacheprovider`
Expected: every test passes (report the count and the skipped count in the commit message).

- [ ] **Step 6: Commit**

```bash
git add remotion/register_energy.json remotion/prop_reach.json remotion/_ground_luma.json remotion/src/runtime/shotLuma.ts remotion/cards/DeviceDemo.md remotion/cards/DeviceHero.md scripts/shot_director.py agents/shot-director.md SKILL.md
git commit -m "Device registers measured, reachable by the shot director, and asked for in the interview

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

(Add `remotion/_ground_reach.json` only if Step 1 changed it.)

---

### Task 13: Look at it — contact sheet and a real film

**Files:**
- Create: `scripts/device_contact_sheet.py`
- Output (not committed): `<scratch>/device-contact-sheet.png`, a scratch film

**Interfaces:**
- Consumes: everything above.
- Produces: `python3 scripts/device_contact_sheet.py <out_png>` — the three looks × 16:9 and 9:16, settled frames, one sheet.

- [ ] **Step 1: Write the sheet script**

```python
#!/usr/bin/env python3
"""Every look x aspect of DeviceDemo on one sheet, settled — for a person to LOOK at before calling it done."""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")
FONT = os.path.join(_HERE, "..", "assets", "fonts", "NotoSansSC-Subset.ttf")


def _ui(path):
    im = Image.new("RGB", (1170, 2532), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    for i in range(10):
        d.text((90, 420 + i * 180), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
    im.save(path)


def main(out_png):
    tmp = tempfile.mkdtemp(prefix="devsheet_")
    _ui(os.path.join(tmp, "ui.png"))
    tiles = []
    for aspect in ("16:9", "9:16"):
        for look in ("flat", "real", "screen"):
            props = {"device": "phone", "look": look, "aspect": aspect, "dna": "product", "camera": "still",
                     "steps": [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06,
                                "ta": 0.06, "t1": 0.2},
                               {"tap": [0.3, 0.2], "t0": 0.3, "ta": 0.4, "t1": 0.7}]}
            pf = os.path.join(tmp, "%s-%s.json" % (look, aspect.replace(":", "x")))
            json.dump(props, open(pf, "w", encoding="utf-8"))
            png = pf[:-5] + ".png"
            subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceDemo", png, "--frame=72",
                            "--gl=angle", "--log=error", "--scale=0.5", "--props=" + pf, "--public-dir=" + tmp],
                           cwd=_REM, check=True)
            tiles.append(("%s %s" % (look, aspect), png))
    ims = [Image.open(p).convert("RGB") for _, p in tiles]
    w = max(i.width for i in ims)
    sheet = Image.new("RGB", (w * 3 + 40, sum(max(i.height for i in ims[r * 3:r * 3 + 3]) + 40 for r in range(2))), "white")
    d, y = ImageDraw.Draw(sheet), 0
    for r in range(2):
        row = ims[r * 3:r * 3 + 3]
        for c, im in enumerate(row):
            d.text((10 + c * (w + 10), y + 5), tiles[r * 3 + c][0], fill="black")
            sheet.paste(im, (10 + c * (w + 10), y + 30))
        y += max(i.height for i in row) + 40
    sheet.save(out_png)
    print(out_png)


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 2: Render and LOOK at the sheet**

Run: `python3 scripts/device_contact_sheet.py /tmp/device-contact-sheet.png` and open the image. Check with your own eyes, and write down what you see for each of the six tiles: the device reads as a phone in its look; the screenshot is whole and undistorted; the ring sits on 「第1条反馈」's row; nothing enters the caption band; at 9:16 the phone fills the zone. A gate being green is not this step.

- [ ] **Step 3: Render a real three-beat film end to end**

In a scratch out_dir: a storyboard with `meta.renderer: "remotion"`, `language: "zh"`, three beats whose narration names the steps (e.g. 「先在上面搜索上周的反馈。」「点开反馈汇总。」「往下看，最常提到的是导出太慢。」), `DeviceDemo` shot_props using the sheet script's screenshot and cues on those words; then run, in order: `python3 scripts/tts.py <out>`, `python3 scripts/validate.py <out>`, `python3 scripts/render_remotion.py <out>`. Extract the frames at each step's action moment and confirm: the ring on the named row, the typed words at the caret, the push-in making the row as tall as the caption. Record the frame numbers and what you saw.

- [ ] **Step 4: Commit the sheet script**

```bash
git add scripts/device_contact_sheet.py
git commit -m "Device layer: a contact sheet of every look and aspect, to look at before calling it done

Claude-Session: https://claude.ai/code/session_01KAsNZXT8wNP3ecdRaiNVfx"
```

- [ ] **Step 5: Report** — the commits made, the suite count, what the sheet and the real film showed (with the frame numbers), and anything that did not work. Nothing is pushed.
