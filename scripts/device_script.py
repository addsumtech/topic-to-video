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
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7a3]")

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
        return float(sum(ms["typeCjkWord"] if _CJK.search(c) else ms["typeLatinKey"] for c in type_chunks(step["type"])))
    return float(ms[k])


def needs_lead(step):
    return step_kind(step) in GESTURES


def _target_problem(t, where):
    if isinstance(t, (list, tuple)):
        if len(t) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in t):
            return None
        return "%s: a position is [x, y] with both in 0..1 of the screen (got %r)" % (where, t)
    if isinstance(t, dict) and set(t) <= {"text", "nth"} and str(t.get("text", "")).strip():
        n = t.get("nth")
        if n is None or (isinstance(n, int) and not isinstance(n, bool) and n >= 1):
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
