#!/usr/bin/env python3
"""promo_film — a product promo film from a SHOT TABLE over real product captures (references/promo-film.md).

    python3 scripts/promo_film.py <film_dir> [--spec=promo.json] [--check] [--stills=120,400] [--no-sound]
                                  [--bgm=auto|none|<file>] [--out=out.mp4]

<film_dir> holds the captures and the spec; it is the render's public dir, so every `src` in the spec is a path
relative to it. Steps: CHECK the table (files, boxes inside their capture, zoom within the capture's density, keys
in order, shot lengths) — a defect stops here, by name; RENDER the picture (remotion composition `PromoFilm`); PIN
the sound to the same table (a cue per action: air through each carried cut, whoosh on a camera move, pop on an
element landing, keys under typing, click on a click, swell → impact as the closing lockup forms) unless the spec lists its own `sfx`
[{f, cue, gain}]; MIX (a generated score under the cues by default — a promo is scored; `--bgm=none` for SFX only,
`--bgm=<file>` for the user's own track) → <film_dir>/out.mp4, and the cue list
actually used → <film_dir>/promo_sfx.json.

WHY. The study (references/craft-standard.md, promo-film.md): the showcase product films are a different KIND of
film from a narrated explainer — the product as itself under a 2.5D camera, serif title cards as breaths, one look,
1.5-6 s shots, flash cuts, sound pinned to each action. This is that kind of film as data, so a director writes a
table and the layer does the craft the same way every time.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import argflag, refuse_unknown  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "remotion")
FPS = 30
MAX_ZOOM = 2.0            # a 2x capture: past this the texture is upsampled (PageCam clamps and warns)
TITLE_BAND = (40, 80)     # a title card is a breath: long enough to read, short enough to stay one
SHOT_BAND = (36, 240)
SHOT_BAND_NOTE = "1.2-8 s; the reference films' product shots run 1.5-6 s"
ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "4:3": (1440, 1080)}  # = remotion/src/Root.tsx ASPECTS


class SpecError(ValueError):
    pass


def _png_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def check(spec, film_dir):
    """Errors (list) and advisories (list) for a promo table. Errors stop the render."""
    errs, adv = [], []
    if spec.get("aspect", "16:9") not in ASPECTS:
        errs.append("aspect %r is not one of %s" % (spec.get("aspect"), ", ".join(ASPECTS)))
    frame_w = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])[0]
    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots:
        return ["spec has no shots"], adv
    sizes = {}

    def cap(src, where):
        p = os.path.join(film_dir, src)
        if not os.path.isfile(p):
            errs.append("%s: %s does not exist in the film dir" % (where, src))
            return None
        if src not in sizes and src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            sizes[src] = _png_size(p)
        return sizes.get(src)

    def inside(box, w, h, where):
        if not all(k in box for k in ("x", "y", "w", "h")):
            errs.append("%s: box needs x, y, w, h" % where)
            return
        if box["w"] <= 0 or box["h"] <= 0 or box["x"] < 0 or box["y"] < 0 or box["x"] + box["w"] > w + 1 or box["y"] + box["h"] > h + 1:
            errs.append("%s: box %s is outside its %dx%d capture" % (where, box, w, h))

    for i, s in enumerate(shots, 1):
        where = "shot %d (%s)" % (i, s.get("kind"))
        d = s.get("dur")
        if not isinstance(d, (int, float)) or d <= 0:
            errs.append("%s: dur must be a positive number of frames" % where)
            continue
        k = s.get("kind")
        if k == "title":
            if not (TITLE_BAND[0] <= d <= TITLE_BAND[1]):
                adv.append("%s: a title card of %d frames (band %d-%d)" % (where, d, *TITLE_BAND))
            if not str(s.get("text", "")).strip():
                errs.append("%s: no text" % where)
        elif k == "page":
            sz = cap(s.get("src", ""), where)
            w, h = s.get("w"), s.get("h")
            if sz and (abs(sz[0] / 2 - w) > 2 or abs(sz[1] / 2 - h) > 2):
                errs.append("%s: w/h %sx%s is not the capture's CSS size %dx%d (a 2x capture is shown at half its pixels)" % (where, w, h, sz[0] // 2, sz[1] // 2))
            if not (SHOT_BAND[0] <= d <= SHOT_BAND[1]):
                adv.append("%s: %d frames (product shots run %d-%d)" % (where, d, *SHOT_BAND))
            keys = s.get("keys") or []
            if not keys:
                errs.append("%s: no camera keys" % where)
            last = -1
            mz = s.get("maxZoom", MAX_ZOOM)
            for kk in keys:
                if kk.get("f", -1) < last:
                    errs.append("%s: camera keys out of order at f=%s" % (where, kk.get("f")))
                last = kk.get("f", last)
                eff = kk.get("zoom", 1) * frame_w / 1920.0       # zoom is authored at a 1920-wide reference
                # past the page's density only onto a MACRO (a 4x capture of the element the close-up looks at)
                macro_ok = any(m.get("kind") == "macro" and eff <= float(m.get("scale", 4)) + 1e-6
                               and m["box"]["x"] <= kk.get("cx", -1) <= m["box"]["x"] + m["box"]["w"]
                               and m["box"]["y"] <= kk.get("cy", -1) <= m["box"]["y"] + m["box"]["h"]
                               for m in (s.get("layers") or s.get("acts") or []) if isinstance(m.get("box"), dict))
                if eff > mz + 1e-6 and not macro_ok:
                    errs.append("%s: key f=%s zoom %.2f is %.2f screen px per CSS px on this %dpx-wide frame, past the capture's density %.1f "
                                "(the texture would be upsampled; a close-up past it needs a `macro` act — a 4x capture of the element at (cx, cy))"
                                % (where, kk.get("f"), kk["zoom"], eff, frame_w, mz))
                frame_h = ASPECTS.get(spec.get("aspect", "16:9"), ASPECTS["16:9"])[1]
                tilt = abs(kk.get("rx", 0)) + abs(kk.get("ry", 0)) + abs(kk.get("rz", 0))
                if w and h and eff > 0 and tilt < 2 and s.get("contain", True) is not False:
                    vw, vh = frame_w / eff, frame_h / eff
                    if (vw < w and (kk.get("cx", 0) - vw / 2 < -1 or kk.get("cx", 0) + vw / 2 > w + 1)) or \
                       (vh < h and (kk.get("cy", 0) - vh / 2 < -1 or kk.get("cy", 0) + vh / 2 > h + 1)):
                        adv.append("%s: key f=%s frames past the page's edge — containment will pull the view in (aim the "
                                   "key inside, or set contain: false for a deliberate edge)" % (where, kk.get("f")))
                if w and h and not (0 <= kk.get("cx", 0) <= w and 0 <= kk.get("cy", 0) <= h):
                    errs.append("%s: key f=%s aims off the capture (%s, %s)" % (where, kk.get("f"), kk.get("cx"), kk.get("cy")))
            for j, l in enumerate(s.get("layers") or s.get("acts") or [], 1):
                lw = "%s layer %d (%s)" % (where, j, l.get("kind"))
                if l.get("kind") not in ("pop", "lift", "focus", "ring", "type", "cursor", "callout", "note", "macro", "deal", "write"):
                    errs.append("%s: unknown layer kind" % lw)
                if l.get("kind") == "macro":
                    msz = cap(l.get("src", ""), lw)
                    b, sc = l.get("box") or {}, float(l.get("scale", 4))
                    if msz and b and (abs(msz[0] - b.get("w", 0) * sc) > 3 or abs(msz[1] - b.get("h", 0) * sc) > 3):
                        errs.append("%s: %s is %dx%d px, not its box %sx%s at %gx — it would be stretched"
                                    % (lw, l.get("src"), msz[0], msz[1], b.get("w"), b.get("h"), sc))
                if l.get("kind") in ("pop", "lift", "focus", "ring", "type", "macro", "write"):
                    inside(l.get("box", {}), w, h, lw)
                for bj, bb in enumerate(l.get("boxes") or []):
                    inside(bb, w, h, "%s box %d" % (lw, bj + 1))
                if l.get("kind") == "pop" and l.get("src") and l.get("src") != s.get("src"):
                    osz = cap(l["src"], lw)
                    if osz:
                        sb = dict(l.get("srcBox") or l["box"])
                        sb["w"], sb["h"] = l["box"]["w"], l["box"]["h"]
                        inside(sb, osz[0] / 2, osz[1] / 2, lw + " srcBox")
                at = l.get("at", (l.get("path") or [{}])[0].get("f", 0))
                if isinstance(at, (int, float)) and at >= d:
                    adv.append("%s: starts at %s, after the shot ends (%d)" % (lw, at, d))
        elif k in ("brand", "outro"):
            cap(s.get("mark", ""), where)
            for j in s.get("recall") or []:
                if not (isinstance(j, int) and 0 <= j < len(shots) and shots[j].get("kind") == "page"):
                    errs.append("%s: recall %r is not the index of a page shot (0-based)" % (where, j))
            if k == "outro" and not any(x.get("kind") == "page" for x in shots):
                errs.append("%s: the outro recalls the film's page shots and there are none" % where)
        elif k == "statement":
            if not str(s.get("text", "")).strip():
                errs.append("%s: no text" % where)
            if s.get("ground") not in (None, "paper", "accent", "ink"):
                errs.append("%s: ground must be paper, accent or ink" % where)
        elif k in ("compare", "montage"):
            regions = [s.get("a"), s.get("b")] if k == "compare" else list(s.get("items") or [])
            if not regions or any(not isinstance(r, dict) for r in regions):
                errs.append("%s: needs %s" % (where, "a and b regions" if k == "compare" else "items (regions)"))
            for j, r in enumerate(r for r in regions if isinstance(r, dict)):
                rsz = cap(r.get("src", ""), "%s region %d" % (where, j))
                if rsz:
                    inside(r.get("box", {}), rsz[0] / 2, rsz[1] / 2, "%s region %d" % (where, j))
        else:
            errs.append("%s: unknown kind" % where)
        if s.get("cut") not in (None, "carry", "flash", "hard", "through"):
            errs.append("%s: cut must be carry, flash, hard or through" % where)
        if s.get("say") is not None and not str(s.get("say")).strip():
            errs.append("%s: an empty `say`" % where)
    if spec.get("cut") not in (None, "carry", "flash", "hard", "through"):
        errs.append("cut must be carry, flash, hard or through")
    adv += skeleton_advice(spec, film_dir)
    look = derive_look(spec.get("look"))
    for key in ("accent", "accentInk"):
        v = look.get(key)
        if v is not None and not (isinstance(v, str) and len(v) == 7 and v.startswith("#")):
            errs.append("look.%s must be #rrggbb" % key)
    if look.get("accentInk") and look.get("paper"):
        r = _contrast(look["accentInk"], look["paper"])
        if r < 4.5:
            errs.append("look.accentInk %s on paper %s is %.2f:1 (type needs 4.5:1)" % (look["accentInk"], look["paper"], r))
    return errs, adv


def _contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


def derive_look(look):
    """The film's ONE look from as little as its accent: `{accent, mode: light|dark}`. Fields given are kept; the
    rest are derived — a near-neutral ground and paper tinted 3-5 % toward the accent, ink and muted ink, and
    `accentInk`, the accent walked toward the ink until it reads at 4.5:1 on the paper (type in the accent stays
    legible on any brand colour)."""
    look = dict(look or {})
    acc = look.get("accent", "#3a7bd5")
    dark = look.get("mode") == "dark" or (look.get("paper") and _contrast(look["paper"], "#000000") < 7)
    if dark:
        base = {"ground": _mix("#121215", acc, 0.06), "groundEdge": _mix("#2a2a30", acc, 0.1), "paper": _mix("#0d0d10", acc, 0.05),
                "ink": "#f3f2ee", "muted": "#9c9a94"}
    else:
        base = {"ground": _mix("#ecebe7", acc, 0.04), "groundEdge": _mix("#d8d6cf", acc, 0.06), "paper": _mix("#f6f5f2", acc, 0.03),
                "ink": "#151513", "muted": "#67655f"}
    for k, v in base.items():
        look.setdefault(k, v)
    look.setdefault("accent", acc)
    if "accentInk" not in look:
        ink = acc
        for i in range(41):
            ink = _mix(acc, look["ink"], i / 40)
            if _contrast(ink, look["paper"]) >= 4.6:
                break
        look["accentInk"] = ink
    look.pop("mode", None)
    return look


LEDGER = os.environ.get("TOPIC_TO_VIDEO_PROMO_LEDGER") or os.path.expanduser("~/.topic-to-video/promo_skeletons.json")


def skeleton(spec):
    """The film's STRUCTURE as a word: one letter per shot kind (+ narrated or not), cuts ignored. Two films with the
    same skeleton are the same film with different pictures — the template feel the user named on Squoosh vs WorkBuddy."""
    letter = {"brand": "B", "title": "C", "page": "P", "outro": "O", "statement": "S", "compare": "V", "montage": "M"}
    return "".join(letter.get(sh.get("kind"), "?") for sh in spec.get("shots") or []) + ("+vo" if narrated(spec) else "")


def skeleton_advice(spec, film_dir):
    """Advise when this film's structure repeats another film's (ledger outside the repo, one row per film folder)."""
    import difflib
    me = skeleton(spec)
    try:
        led = json.load(open(LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    out = []
    for other, sk in led.items():
        if os.path.abspath(other) == os.path.abspath(film_dir):
            continue
        r = difflib.SequenceMatcher(None, me, sk).ratio()
        if r >= 0.8:
            out.append("structure %s repeats %s (%s, %.0f %% alike) — design this film's own arc (references/promo-film.md "
                       "§design): its hook, its proof, its payoff come from THIS product" % (me, os.path.basename(other.rstrip("/")), sk, r * 100))
    return out


def record_skeleton(spec, film_dir):
    try:
        led = json.load(open(LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    led[os.path.abspath(film_dir)] = skeleton(spec)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), indent=1)


def narrated(spec):
    """A film is narrated when it says so, or (no `narrate`) when any shot carries a line to `say`. Whether a film
    SHOULD speak is the director's call per film: a how-it-works story speaks, a mood or brand piece does not."""
    n = spec.get("narrate")
    return bool(n) if n is not None else any(str(sh.get("say") or "").strip() for sh in spec.get("shots") or [])


VO_LEAD, VO_TAIL = 0.3, 0.45      # s: a line starts a breath into its shot and ends a breath before the cut


def voice_pass(film_dir, spec):
    """Voice every `say` (edge-tts), lengthen each shot to hold its line, and time the subtitles from the voice's own
    word boundaries. Returns (resolved spec, [(start_s, mp3)]). Cached by text + voice."""
    import hashlib
    import math
    if not narrated(spec):
        return spec, []
    import tts
    voice = spec.get("voice") or "en-US-AndrewNeural"
    voice = voice.split(":", 1)[1] if voice.startswith("edge:") else voice
    rate = spec.get("voice_rate", "+0%")
    adir = os.path.join(film_dir, "audio")
    os.makedirs(adir, exist_ok=True)
    out = json.loads(json.dumps(spec))
    clips, subs, t = [], [], 0
    for i, sh in enumerate(out["shots"]):
        line = str(sh.get("say") or "").strip()
        d = int(round(sh["dur"]))
        if line:
            h = hashlib.sha1(("%s|%s|%s" % (voice, rate, line)).encode("utf-8")).hexdigest()[:12]
            mp3 = os.path.join(adir, "say_%02d_%s.mp3" % (i, h))
            if not os.path.isfile(mp3):
                tts._edge(line, mp3, voice, rate)
            secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                                        capture_output=True, text=True).stdout.strip() or 0)
            need = int(math.ceil((VO_LEAD + secs + VO_TAIL) * FPS))
            if need > d:
                sh["dur"] = d = need
            st = t / FPS + VO_LEAD
            clips.append((st, mp3))
            # the frame already SAYS it (a statement or a card whose type is the line): the subtitle yields
            norm = lambda x: re.sub(r"[^\w]+", " ", str(x).replace("*", "")).strip().lower()
            if not (sh.get("kind") in ("statement", "title") and norm(sh.get("text", "")) == norm(line)):
                subs += _subtitle_chunks(line, os.path.splitext(mp3)[0] + ".words.json", st, secs)
        t += d
    out["subtitles"] = [{"from": int(round(a * FPS)), "to": int(round(b * FPS)), "text": x} for a, b, x in subs]
    return out, clips


def _subtitle_chunks(line, words_json, start_s, secs, max_chars=64):
    """The line in readable pieces (a sentence, or a clause when long), each shown from its first word to the next."""
    import re as _re
    parts = [p.strip() for p in _re.split(r"(?<=[.!?。！？])\s+|(?<=[,;，；])\s+(?=\S{12,})", line) if p.strip()]
    if not parts:
        return []
    try:
        words = json.load(open(words_json, encoding="utf-8"))
    except (OSError, ValueError):
        words = []
    out, wi = [], 0
    starts_ = []
    for p in parts:
        starts_.append(words[wi]["t"] if wi < len(words) else (len(starts_) / len(parts)) * secs)
        wi += len(p.split()) if words else 0
    for k, p in enumerate(parts):
        a = start_s + starts_[k]
        b = start_s + (starts_[k + 1] if k + 1 < len(parts) else secs) + (0.25 if k + 1 == len(parts) else 0)
        out.append((a, b, p))
    return out


def starts(spec):
    t, out = 0, []
    for s in spec["shots"]:
        out.append(t)
        t += int(round(s["dur"]))
    return out, t


def plan_sfx(spec):
    """[(frame, cue, gain)] pinned to the table's actions. Restraint: a burst of pops is one sound per 3 frames,
    fading; a camera key only sounds when the camera really travels."""
    cues = []
    st, _ = starts(spec)
    film_cut = spec.get("cut", "carry")
    for idx, (s, a) in enumerate(zip(spec["shots"], st)):
        k = s["kind"]
        if idx and (s.get("cut") or film_cut) in ("carry", "flash"):
            cues.append((a, "whoosh", 0.34))                       # the cut carries a move: one air sound through it
        if k == "brand":
            cues += [(a + 14, "drop", 0.5), (a + 22, "whoosh", 0.2)]
        elif k == "title":
            cues.append((a + 14, "select", 0.22))                   # the accent fill arrives
        elif k == "outro":
            sa = a + int(s.get("stampAt", 46))
            cues += [(a + 6, "swell", 0.4), (sa + 10, "impact", 0.8)]
            if s.get("cta"):
                cues.append((sa + 46, "select", 0.3))
        elif k == "page":
            keys = s.get("keys") or []
            for k0, k1 in zip(keys, keys[1:]):
                travel = abs(k1["cx"] - k0["cx"]) + abs(k1["cy"] - k0["cy"]) + 400 * abs(k1.get("zoom", 1) - k0.get("zoom", 1)) \
                    + 6 * (abs(k1.get("rx", 0) - k0.get("rx", 0)) + abs(k1.get("ry", 0) - k0.get("ry", 0)))
                if travel > 120 and k1["f"] - k0["f"] <= 60:
                    cues.append((a + int((k0["f"] + k1["f"]) / 2), "whoosh", min(0.5, 0.22 + travel / 2000)))
            last_pop, npop = -99, 0
            for l in s.get("layers") or s.get("acts") or []:
                kind = l.get("kind")
                if kind == "pop":
                    f = a + int(l["at"] + l.get("dur", 14) * 0.4)
                    if f - last_pop >= 3:
                        cues.append((f, "drop", max(0.12, 0.36 * (0.85 ** npop))))
                        last_pop, npop = f, npop + 1
                elif kind == "deal":
                    for bj in range(len(l.get("boxes") or [])):
                        f = a + int(l["at"] + bj * l.get("every", 3) + l.get("dur", 18) * 0.8)
                        if f - last_pop >= 3:
                            cues.append((f, "deal", max(0.12, 0.3 * (0.88 ** bj))))
                            last_pop = f
                    cues.append((a + int(l["at"]) - 4, "whoosh", 0.3))
                elif kind == "write":
                    n = max(1, round(l["box"]["h"] / l.get("lineH", 24)))
                    for li in range(0, n, 2):
                        cues.append((a + int(l["at"] + li * l.get("every", 5)), "key", 0.18))
                elif kind == "lift":
                    cues += [(a + int(l["at"]) + 6, "whoosh", 0.36), (a + int(l["at"]) + 18, "glass", 0.22),
                             (a + int(l["until"]) + 14, "drop", 0.35)]
                elif kind == "type":
                    cpf = float(l.get("cpf", 0.5))
                    n = len(l.get("text", ""))
                    for c in range(0, n, 2):
                        cues.append((a + int(l["at"] + c / cpf), "key", 0.22))
                elif kind == "cursor":
                    for c in l.get("clicks") or []:
                        cues.append((a + int(c) + 2, "click", 0.6))
                elif kind == "ring":
                    cues.append((a + int(l["at"]) + 4, "select", 0.25))
                elif kind == "focus":
                    cues.append((a + int(l["at"]) + 6, "select", 0.18))
                elif kind in ("note", "callout"):
                    cues.append((a + int(l["at"]) + 4, "select", 0.24))
    return sorted(cues)


def render_picture(film_dir, spec_path, out, frames=None):
    # absolute paths: remotion runs from its own folder, so a relative film dir pointed it at nothing
    film_dir, spec_path, out = os.path.abspath(film_dir), os.path.abspath(spec_path), os.path.abspath(out)
    spec = json.load(open(spec_path, encoding="utf-8"))
    spec["look"] = derive_look(spec.get("look"))
    props = os.path.join(film_dir, "_promo_props.json")          # the table as rendered: the derived look filled in
    json.dump(spec, open(props, "w"), indent=0)
    cmd = ["npx", "remotion", "render" if frames is None else "still", "src/index.ts", "PromoFilm", out,
           "--props=" + props, "--public-dir=" + film_dir]
    if frames is not None:
        cmd.append("--frame=%d" % frames)
    else:
        cmd += ["--codec=h264", "--crf=16", "--concurrency=6"]
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("[promo_film] render failed:\n" + (r.stderr or r.stdout)[-3000:])


# RECORDED takes for the UI sounds (Kenney "Interface Sounds", CC0 — assets/sfx/kenney/LICENSE.txt); the noise-built
# cues (whoosh, swell, impact) stay synthesised. A synthesised bell or chime reads as a demo's beeps (HyperFrames'
# sound reference: "no synthesised tones, chimes, or dings"); a real click, drop or select reads as a product.
_KENNEY = os.path.join(ROOT, "assets", "sfx", "kenney")
BANK = {"click": ["click_005"], "key": ["click_002", "click_003"], "drop": ["drop_002", "drop_003"], "deal": ["drop_001"],
        "select": ["select_001", "select_002"], "glass": ["glass_002"]}


# a social film's loudness (-16..-14 LUFS), true peak under -1.5 dBTP: measured, the unnormalised mix sat at -24 LUFS
LOUD = "loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.7:level=false"   # single-pass loudnorm and the AAC encode overshoot (-0.5/-0.6 dBTP measured); the limiter holds -3 dBFS


def _voice_track(clips, secs, out_wav):
    """Every line placed at its second on one mono 48 kHz track."""
    import numpy as np
    import wave
    sr = 48000
    buf = np.zeros(int((secs + 1) * sr), np.float32)
    for st, mp3 in clips:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
        i = int(st * sr)
        buf[i:i + len(a)] += a[: max(0, len(buf) - i)]
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sr)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())


def mix(film_dir, silent, cues, total_frames, out, bgm="auto", climax_s=None, vo_clips=()):
    import sfx
    secs = total_frames / FPS
    wav = os.path.join(film_dir, "_promo_sfx.wav")
    bank = sfx.load_bank({k: [os.path.join(_KENNEY, n + ".wav") for n in v] for k, v in BANK.items()})
    if not sfx.build_sfx_track([(f / FPS, c, g) for f, c, g in cues], secs, wav, bank=bank):
        raise SystemExit("[promo_film] numpy is needed to synthesise the sound")
    inputs = ["-i", silent, "-i", wav]
    if bgm == "auto":
        # a promo is SCORED (a film over ~15 s that tells something gets a bed): the generated score on a beat grid,
        # its riser and peak placed on the outro's stamp
        import beatgrid
        import score
        g = beatgrid.BeatGrid(112.5, 0.0)
        sc = score.render(g, secs + 1.0, climax_s=climax_s, seed=7)
        pad = os.path.join(film_dir, "_promo_bgm.wav")
        score.write_wav(pad, sc["bed"] + sc["pulse"])
        inputs += ["-i", pad]
    elif bgm and bgm != "none":
        inputs += ["-i", bgm]
    has_bed = len(inputs) == 6
    if vo_clips:
        # THE VOICE LEADS: the bed ducks under it (sidechain), the cues sit lower than in a music-only film
        vo = os.path.join(film_dir, "_promo_vo.wav")
        _voice_track(vo_clips, secs, vo)
        inputs += ["-i", vo]
        vi = 3 if has_bed else 2
        if has_bed:
            graph = ("[%d:a]asplit=2[v][vk];[1:a]highpass=f=120,volume=0.6[s];[2:a]volume=0.42,afade=t=in:d=0.4,afade=t=out:st=%.2f:d=2[b0];"
                     "[b0][vk]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=400[b];"
                     "[v][s][b]amix=inputs=3:normalize=0,%s[a]" % (vi, max(0, secs - 2), LOUD))
        else:
            graph = "[%d:a]anull[v];[1:a]highpass=f=120,volume=0.6[s];[v][s]amix=inputs=2:normalize=0,%s[a]" % (vi, LOUD)
    elif has_bed:
        # the hits sit 3-6 dB over the bed; the bed fades in and closes on a 2 s fade under the end card
        graph = ("[1:a]highpass=f=120,volume=1.0[s];[2:a]volume=0.42,afade=t=in:d=0.4,"
                 "afade=t=out:st=%.2f:d=2[b];[s][b]amix=inputs=2:normalize=0,%s[a]" % (max(0, secs - 2), LOUD))
    else:
        graph = "[1:a]highpass=f=120,%s[a]" % LOUD
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "%.3f" % secs, out]
    subprocess.run(cmd, check=True)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[0])
        return 2
    refuse_unknown(argv[1:], valued=("spec", "stills", "bgm", "out"), switches=("check", "no-sound", "remix", "sheet"))
    film = os.path.abspath(argv[0])
    spec_path = os.path.join(film, argflag(argv, "spec", "promo.json"))
    spec = json.load(open(spec_path, encoding="utf-8"))
    errs, adv = check(spec, film)
    for a in adv:
        print("  ADVISORY  " + a)
    if errs:
        for e in errs:
            print("  ERROR     " + e)
        return 1
    _, total = starts(spec)
    print("[promo_film] %d shots, %d frames (%.1f s)" % (len(spec["shots"]), total, total / FPS))
    if "--check" in argv:
        return 0
    stills = argflag(argv, "stills", None)
    if stills:
        os.makedirs(os.path.join(film, "_stills"), exist_ok=True)
        for f in [int(x) for x in stills.split(",") if x]:
            p = os.path.join(film, "_stills", "f%04d.png" % f)
            render_picture(film, spec_path, p, frames=f)
            print("  still " + p)
        return 0
    out = os.path.join(film, argflag(argv, "out", "out.mp4"))
    # NARRATION FIRST: the voice decides how long a speaking shot lasts, so the table is resolved before the picture
    spec, vo_clips = voice_pass(film, spec)
    if vo_clips:
        spec_path = os.path.join(film, "_promo_resolved_%s.json" % os.path.splitext(os.path.basename(out))[0])
        json.dump(spec, open(spec_path, "w"), indent=0)
        _, total = starts(spec)
        print("[promo_film] narrated: %d line(s), the film now %d frames (%.1f s)" % (len(vo_clips), total, total / FPS))
    record_skeleton(spec, film)
    # the picture, kept per output so two films in one folder (a 16:9 and a 9:16) never share it; `--remix` re-mixes the
    # sound over the picture already rendered
    silent = os.path.join(film, "_promo_silent_%s" % os.path.basename(out))
    if "--remix" in argv and os.path.isfile(silent):
        print("[promo_film] --remix: the picture is the one already rendered (%s)" % os.path.basename(silent))
    else:
        render_picture(film, spec_path, silent)
    if "--no-sound" in argv:
        os.replace(silent, out)
    else:
        cues = spec.get("sfx")
        cues = [(int(c["f"]), c["cue"], float(c.get("gain", 0.4))) for c in cues] if cues else plan_sfx(spec)
        json.dump([{"f": f, "cue": c, "gain": round(g, 3)} for f, c, g in cues], open(os.path.join(film, "promo_sfx.json"), "w"), indent=0)
        st, _ = starts(spec)
        outro = [(a, sh) for a, sh in zip(st, spec["shots"]) if sh.get("kind") == "outro"]
        climax = (outro[-1][0] + int(outro[-1][1].get("stampAt", 46))) / FPS if outro else None
        mix(film, silent, cues, total, out, argflag(argv, "bgm", "auto"), climax, vo_clips)
    print("[promo_film] wrote " + out)
    # THE PICTURE GLIDES, MEASURED: a page under a moving camera that steps instead (re-laid out per frame, a raster
    # re-chosen per render tab, a corner in the camera's path) is what a viewer sees as 抖动 — say so on every render
    if "--sheet" in argv:
        sheet(film, spec_path, out)
    rc = glide_check(film, spec_path, out)
    if rc == 1:
        print("[promo_film] the CAMERA steps or shimmers on a page shot (above) — fix it before delivery")
    return rc                                   # a film whose camera fails is written, and the run still says so


def sheet(film, spec_path, video, out_name="_sheet.jpg"):
    """One frame per shot at 90 % of it (the settled frame), labelled with its table index and kind — the contact
    sheet a review starts from."""
    from PIL import Image, ImageDraw
    spec = json.load(open(spec_path, encoding="utf-8"))
    st, _ = starts(spec)
    tiles = []
    for i, (a, sh) in enumerate(zip(st, spec["shots"])):
        f = a + int(round(sh["dur"] * 0.9))
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "select=eq(n\\,%d),scale=480:-2" % f, "-vsync", "0",
                            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        import io
        im = Image.open(io.BytesIO(r.stdout)).convert("RGB") if r.stdout else Image.new("RGB", (480, 270), "black")
        tiles.append((i, sh.get("kind"), f, im))
    cols = 4
    tw, th = tiles[0][3].size
    out = Image.new("RGB", (cols * (tw + 8), ((len(tiles) + cols - 1) // cols) * (th + 22)), (16, 16, 16))
    d = ImageDraw.Draw(out)
    for k, (i, kind, f, im) in enumerate(tiles):
        x, y = (k % cols) * (tw + 8), (k // cols) * (th + 22)
        out.paste(im, (x, y))
        d.text((x + 4, y + th + 4), "%02d %s f%d" % (i, kind, f), fill=(220, 220, 220))
    p = os.path.join(film, out_name)
    out.save(p, quality=85)
    print("[promo_film] contact sheet " + p)
    return p


def glide_check(film, spec_path, video):
    """picture_glide_qa on every page shot; a shot that fails is re-judged on a CAMERA-ONLY proxy (its acts removed).
    A sparse page whose only texture is the elements popping in measures the acts' own motion — a pop's overshoot, a
    lift — not the camera (an Excalidraw sketch: 0.34 px with its acts, 0.10 camera-only; its slit-scan smooth). So the
    verdict is the camera's; the acts are named as what moved."""
    import tempfile
    import picture_glide_qa as pg
    spec = json.load(open(spec_path, encoding="utf-8"))
    W, H, _n, fps = pg._probe(video)
    bad = []
    for beat, a, b in pg.spans_of(film, spec_path):
        if b - a < 14:
            continue
        r = pg.judge_span(video, a, b, W, H, fps)
        if r is None or r.get("rms") is None:
            print("  shot %2d  not judged (%s)" % (beat - 1, "nothing moving" if r is None else "too little texture"))
            continue
        fails = r["rms"] > pg.FAIL_RMS or (r.get("shimmer") or 0) > pg.FAIL_SHIMMER
        line = "  shot %2d  %.3f px RMS · shimmer %s" % (beat - 1, r["rms"], "%.1f%%" % (r["shimmer"] * 100) if r.get("shimmer") is not None else "n/a")
        if not fails:
            print(line + "  ok")
            continue
        shot = dict(spec["shots"][beat - 1])
        if not (shot.get("layers") or shot.get("acts")):
            print(line + "   <- the CAMERA steps or shimmers")
            bad.append(beat - 1)
            continue
        # the camera-only proxy keeps the shot's MACROS: they are part of what the camera films (a push past the page's
        # 2x is onto them), and without them a macro close-up was re-judged as a push into a soft page
        keep = [l for l in (shot.get("layers") or shot.get("acts") or []) if l.get("kind") == "macro"]
        shot.pop("layers", None), shot.pop("acts", None), shot.pop("caption", None)
        shot["layers"] = keep
        proxy = dict(spec, shots=[shot])
        tmp = tempfile.mkdtemp(prefix="promo_cam_")
        pj = os.path.join(film, "_promo_cam_%d.json" % beat)
        json.dump(proxy, open(pj, "w"))
        mp4 = os.path.join(tmp, "cam.mp4")
        try:
            render_picture(film, pj, mp4)
            rc_ = pg.judge_span(mp4, 8, int(round(shot["dur"])) - 8, W, H, fps)
        finally:
            os.remove(pj)
        cam_bad = rc_ is not None and rc_.get("rms") is not None and (rc_["rms"] > pg.FAIL_RMS or (rc_.get("shimmer") or 0) > pg.FAIL_SHIMMER)
        if cam_bad:
            print(line + "   <- the CAMERA steps or shimmers (camera-only: %.3f px, shimmer %s)"
                  % (rc_["rms"], "%.1f%%" % (rc_["shimmer"] * 100) if rc_.get("shimmer") is not None else "n/a"))
            bad.append(beat - 1)
        else:
            print(line + "   camera-only %s — the camera glides; what moved is the shot's acts"
                  % ("%.3f px" % rc_["rms"] if rc_ and rc_.get("rms") is not None else "still"))
    print("[promo_film] glide (shots numbered as in the table, from 0): %s" % ("FAIL on shot(s) %s" % bad if bad else "OK — every page shot's camera glides"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
