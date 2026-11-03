#!/usr/bin/env python3
"""SHOT-OWNED SOUND — the sounds a beat's own picture makes, as events for sfx.plan_cues.

Three sources, all resolved BEFORE the mix and none of them by rendering:

  1. a REGISTER's declaration — `export const SOUNDS = [...]` in its .tsx (remotion/src/runtime/sound.ts says the
     grammar and why it is a static literal rather than a DOM census). Each point is a t on the register's own clock;
     it is mapped to the beat frame useT reaches it on (`frame_at_t`, the arithmetic of runtime/optics useFrameAtT) and
     through the beat's sync warp (sync_qa.unwarp_frame) to the film second the picture actually does it.
  2. a STAGE step's `sound` (scripts/stage_runs.sound_events — a step arrives at its resolved `t`).
  3. the BOARD's own `slide.sounds`: [{kind, at: <seconds into the beat> | {"cue": "<words>"}, gain?}], or "none" —
     silence under this beat (sfx.plan_cues then plays nothing whose time falls in it).

    python3 scripts/shot_sounds.py <Shot>            # print a register's declaration, parsed
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")
_SHOTS = os.path.join(_REM, "src", "shots")
_SOUND_TS = os.path.join(_REM, "src", "runtime", "sound.ts")
_MOTION_TS = os.path.join(_REM, "src", "runtime", "motion.ts")


class SoundDeclError(ValueError):
    pass


def sound_kinds():
    """SOUND_KINDS read from runtime/sound.ts — the one definition the runtime and the mix share."""
    src = open(_SOUND_TS, encoding="utf-8").read()
    m = re.search(r"export const SOUND_KINDS = \[([^\]]*)\]", src)
    if not m:
        raise RuntimeError("runtime/sound.ts no longer exports SOUND_KINDS — shot sounds cannot be checked")
    return tuple(re.findall(r"'(\w+)'", m.group(1)))


def _motion_consts():
    src = open(_MOTION_TS, encoding="utf-8").read()
    seam = re.search(r"export const SEAM_FRAMES = (\d+);", src)
    entry = re.search(r"export const ENTRY_T = ([0-9.]+);", src)
    if not (seam and entry):
        raise RuntimeError("runtime/motion.ts no longer exports SEAM_FRAMES / ENTRY_T as literals — shot sounds "
                           "cannot be placed on the frames useT reaches them on")
    return int(seam.group(1)), float(entry.group(1))


SEAM_FRAMES, ENTRY_T = _motion_consts()


def frame_at_t(T, dur):
    """The beat frame at which useT() reaches T — runtime/optics useFrameAtT, line for line (useT holds its pads at
    both edges, so t=0 is not frame 0 and t=1 is not the last frame)."""
    dur = int(dur)
    pad = min(SEAM_FRAMES, (max(0, dur - 1)) // 3)
    span = max(1, dur - 1 - 2 * pad)
    x = min(1.0, max(0.0, (float(T) - ENTRY_T) / (1.0 - ENTRY_T)))
    return int(round(pad + span * x))


# ── the literal parser ──────────────────────────────────────────────────────────────────────────────────────────
_KEYS = {"kind", "at", "to", "each", "gain", "type", "ease"}


def _js_literal_to_json(txt):
    """A JS array-of-object LITERAL as JSON text: comments dropped, keys quoted, 'strings' double-quoted, trailing
    commas removed. Anything else (an identifier, an expression, a spread) survives as invalid JSON and is refused."""
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    txt = re.sub(r"//[^\n]*", "", txt)
    txt = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: json.dumps(m.group(1)), txt)
    txt = re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', txt)
    txt = re.sub(r",\s*([}\]])", r"\1", txt)
    return txt


def parse_sounds(src, where="SOUNDS"):
    """The `export const SOUNDS = [...]` of a register's source, parsed and checked, or [] when it declares none."""
    m = re.search(r"^export const SOUNDS\s*(?::[^=]+)?=\s*\[", src, re.M)
    if not m:
        return []
    i, depth = m.end() - 1, 0
    for j in range(i, len(src)):
        if src[j] == "[":
            depth += 1
        elif src[j] == "]":
            depth -= 1
            if depth == 0:
                break
    else:
        raise SoundDeclError("%s: SOUNDS has no closing bracket" % where)
    body = src[i:j + 1]
    try:
        decls = json.loads(_js_literal_to_json(body))
    except ValueError as e:
        raise SoundDeclError("%s: SOUNDS must be a LITERAL list of {kind, at, to?, each?, gain?} — numbers and "
                             "'strings' only (%s): %s" % (where, e, body[:200]))
    return check_decls(decls, where)


def check_decls(decls, where="SOUNDS"):
    kinds = sound_kinds()
    if not isinstance(decls, list):
        raise SoundDeclError("%s: SOUNDS is a list" % where)
    for k, d in enumerate(decls):
        if not isinstance(d, dict):
            raise SoundDeclError("%s[%d]: each sound is an object" % (where, k))
        extra = set(d) - _KEYS
        if extra:
            raise SoundDeclError("%s[%d]: unknown key(s) %s — kind, at, to, each, type, ease, gain" % (where, k, sorted(extra)))
        if d.get("kind") not in kinds:
            raise SoundDeclError("%s[%d]: kind %r is not one of %s" % (where, k, d.get("kind"), ", ".join(kinds)))
        at = d.get("at")
        if isinstance(at, bool) or not (isinstance(at, str) and at or isinstance(at, (int, float)) and 0 <= at <= 1):
            raise SoundDeclError("%s[%d]: at is a point on the register's clock (0..1) or the name of a prop holding "
                                 "one, got %r" % (where, k, at))
        if "each" in d and not (isinstance(d["each"], str) and d["each"]):
            raise SoundDeclError("%s[%d]: each names a list prop" % (where, k))
        if "type" in d and not (isinstance(d["type"], str) and d["type"]):
            raise SoundDeclError("%s[%d]: type names a string prop the register types" % (where, k))
        if "type" in d and "each" in d:
            raise SoundDeclError("%s[%d]: a sound per character (type) or per item (each), not both" % (where, k))
        if "ease" in d and (d.get("ease") not in ("linear", "out-cubic") or "type" not in d):
            raise SoundDeclError("%s[%d]: ease is 'linear' or 'out-cubic', with type" % (where, k))
        if "to" in d and (isinstance(d["to"], bool) or not isinstance(d["to"], (int, float)) or not 0 <= d["to"] <= 1):
            raise SoundDeclError("%s[%d]: to is a point on the clock, 0..1" % (where, k))
        g = d.get("gain", 1.0)
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not 0 < g <= 1:
            raise SoundDeclError("%s[%d]: gain is (0, 1]" % (where, k))
    return decls


def register_sounds(shot, out_dir=None):
    """A register's declared sounds — the library's .tsx, else the film's workshop shot — [] when it declares none."""
    cands = [os.path.join(_SHOTS, "%s.tsx" % shot)]
    if out_dir:
        cands.append(os.path.join(out_dir, "workshop", "shots", "%s.tsx" % shot))
    for p in cands:
        if os.path.isfile(p):
            return parse_sounds(open(p, encoding="utf-8").read(), where="%s SOUNDS" % shot)
    return []


def decl_ts(decl, props):
    """The t's at which one declaration sounds against these props — runtime/sound.ts soundTs, line for line."""
    at = props.get(decl["at"]) if isinstance(decl["at"], str) else decl["at"]
    if at is None:
        return []
    if isinstance(at, bool) or not isinstance(at, (int, float)) or not 0 <= at <= 1:
        raise SoundDeclError("%s at %r — the prop %r must hold a point on the clock, 0..1"
                             % (decl["kind"], at, decl["at"]))
    if "type" in decl:
        text = props.get(decl["type"])
        if not isinstance(text, str) or not text:
            return []
        to = float(decl.get("to", at))
        if to < at or to > 1:
            raise SoundDeclError("%s type %s: to (%s) must be in [at, 1]" % (decl["kind"], decl["type"], to))
        n = len(text)                                   # code points, as Array.from counts them
        cubic = decl.get("ease") == "out-cubic"
        inv = (lambda q: 1.0 - (1.0 - q) ** (1.0 / 3.0)) if cubic else (lambda q: q)
        return [float(at) + (to - float(at)) * inv((i + 1) / float(n)) for i in range(n)]
    if "each" not in decl:
        return [float(at)]
    items = props.get(decl["each"])
    if not isinstance(items, list) or not items:
        return []
    to = float(decl.get("to", at))
    if to < at:
        raise SoundDeclError("%s each %s: to (%s) before at (%s)" % (decl["kind"], decl["each"], to, at))
    n = len(items)
    return [float(at) if n == 1 else at + (to - at) * i / (n - 1.0) for i in range(n)]


def scene_events(scene, fps, out_dir=None):
    """[{t (seconds into the scene), name, gain, src}] — the sounds this beat's register declares, on the frames its
    picture makes them. A stage-run beat has no register clock (the stage's steps carry their own sounds)."""
    if (scene or {}).get("stage"):
        return []
    decls = register_sounds(scene.get("shot") or "", out_dir)
    if not decls:
        return []
    import sync_qa
    props = scene.get("props") or {}
    dur = int(scene.get("durF") or 0)
    if dur < 2:
        return []
    out = []
    for d in decls:
        for T in decl_ts(d, props):
            f = sync_qa.unwarp_frame(frame_at_t(T, dur), scene.get("warp"))
            out.append({"t": round(f / float(fps), 6), "name": d["kind"], "gain": float(d.get("gain", 1.0)),
                        "src": "shot"})
    return out


def board_events(slide, out_dir, fps):
    """The board's own sounds for a beat: [{t, name, gain, src}] or the string "none" (silence under it). Cue phrases
    are resolved on the beat's own word times, in SECONDS (render_remotion.resolve_cue_props)."""
    sd = (slide or {}).get("sounds")
    if sd is None:
        return []
    if sd == "none":
        return "none"
    if not isinstance(sd, list):
        raise SoundDeclError("slide %s: sounds is a list of {kind, at, gain?} or \"none\"" % slide.get("index"))
    kinds = sound_kinds()
    for k, ev in enumerate(sd):
        if not isinstance(ev, dict) or ev.get("kind") not in kinds or "at" not in ev or set(ev) - {"kind", "at", "gain"}:
            raise SoundDeclError("slide %s: sounds[%d] must be {kind: one of %s, at: seconds | {\"cue\": words}, gain?}"
                                 % (slide.get("index"), k, ", ".join(kinds)))
    import render_remotion as _rr
    dur = float(slide.get("duration") or 0)
    res = _rr.resolve_cue_props({"sounds": sd}, out_dir, slide.get("audio"), slide.get("narration") or
                                slide.get("script") or "", dur, fps, seconds=True)["sounds"]
    out = []
    for ev in res:
        t = ev["at"]
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= max(dur, 0):
            raise SoundDeclError("slide %s: a sound at %r — seconds into the beat (0..%.2f)" % (slide.get("index"), t, dur))
        g = ev.get("gain", 1.0)
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not 0 < g <= 1:
            raise SoundDeclError("slide %s: sound gain is (0, 1]" % slide.get("index"))
        out.append({"t": float(t), "name": ev["kind"], "gain": float(g), "src": "board"})
    return out


def problems(slides, out_dir=None):
    """What validate.py reports: every register declaration that cannot be read, every board `sounds` that is
    malformed. [] when all is well. (Cue phrases are checked where they are resolved, at render.)"""
    out = []
    seen = set()
    kinds = sound_kinds()
    for s in slides or []:
        shot = s.get("shot")
        if shot and shot not in seen:
            seen.add(shot)
            try:
                register_sounds(shot, out_dir)
            except SoundDeclError as e:
                out.append(str(e))
        sd = s.get("sounds")
        if sd is None or sd == "none":
            continue
        if not isinstance(sd, list):
            out.append("slide %s: sounds is a list of {kind, at, gain?} or \"none\"" % s.get("index"))
            continue
        for k, ev in enumerate(sd):
            ok = isinstance(ev, dict) and ev.get("kind") in kinds and "at" in ev and not set(ev) - {"kind", "at", "gain"}
            at = ev.get("at") if isinstance(ev, dict) else None
            ok = ok and (isinstance(at, (int, float)) and not isinstance(at, bool) and at >= 0 or
                         isinstance(at, dict) and isinstance(at.get("cue"), str) and at["cue"].strip())
            if ok and isinstance(at, dict):
                import cues as _cues
                if _cues._anchor_pos(s.get("narration") or s.get("script") or "", at["cue"].strip()) < 0:
                    out.append("slide %s: sounds[%d] cues %r, which this beat's narration does not say"
                               % (s.get("index"), k, at["cue"]))
                    continue
            if not ok:
                out.append("slide %s: sounds[%d] must be {kind: one of %s, at: seconds | {\"cue\": words}, gain?}"
                           % (s.get("index"), k, ", ".join(kinds)))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(__doc__)
        sys.exit(2)
    print(json.dumps(register_sounds(sys.argv[1]), indent=1))
