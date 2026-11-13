#!/usr/bin/env python3
"""promo_film — a product promo film from a SHOT TABLE over real product captures (references/promo-film.md).

    python3 scripts/promo_film.py <film_dir> [--spec=promo.json] [--check] [--stills=120,400] [--no-sound]
                                  [--bgm=<file>|auto] [--out=out.mp4]

<film_dir> holds the captures and the spec; it is the render's public dir, so every `src` in the spec is a path
relative to it. Steps: CHECK the table (files, boxes inside their capture, zoom within the capture's density, keys
in order, shot lengths) — a defect stops here, by name; RENDER the picture (remotion composition `PromoFilm`); PIN
the sound to the same table (a cue per action: whoosh on a camera move, pop on an element landing, keys under
typing, click on a click, riser → impact → sparkle on the outro's stamp) unless the spec lists its own `sfx`
[{f, cue, gain}]; MIX (SFX only by default, `--bgm` adds a bed under it) → <film_dir>/out.mp4, and the cue list
actually used → <film_dir>/promo_sfx.json.

WHY. The study (references/craft-standard.md, promo-film.md): the showcase product films are a different KIND of
film from a narrated explainer — the product as itself under a 2.5D camera, serif title cards as breaths, one look,
1.5-6 s shots, flash cuts, sound pinned to each action. This is that kind of film as data, so a director writes a
table and the layer does the craft the same way every time.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import argflag, refuse_unknown  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION = os.path.join(ROOT, "remotion")
FPS = 30
MAX_ZOOM = 2.0            # a 2x capture: past this the texture is upsampled (PageCam clamps and warns)
TITLE_BAND = (40, 80)     # a title card is a breath: long enough to read, short enough to stay one
SHOT_BAND = (36, 240)     # 1.2-8 s; the reference films' product shots run 1.5-6 s


class SpecError(ValueError):
    pass


def _png_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def check(spec, film_dir):
    """Errors (list) and advisories (list) for a promo table. Errors stop the render."""
    errs, adv = [], []
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
                if kk.get("zoom", 1) > mz + 1e-6:
                    errs.append("%s: key f=%s zoom %.2f is past the capture's density %.1f (the texture would be upsampled)" % (where, kk.get("f"), kk["zoom"], mz))
                if w and h and not (0 <= kk.get("cx", 0) <= w and 0 <= kk.get("cy", 0) <= h):
                    errs.append("%s: key f=%s aims off the capture (%s, %s)" % (where, kk.get("f"), kk.get("cx"), kk.get("cy")))
            for j, l in enumerate(s.get("layers") or [], 1):
                lw = "%s layer %d (%s)" % (where, j, l.get("kind"))
                if l.get("kind") in ("pop", "lift", "focus", "ring", "type"):
                    inside(l.get("box", {}), w, h, lw)
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
            for j, p in enumerate(s.get("pieces") or [], 1):
                psz = cap(p.get("src", ""), "%s piece %d" % (where, j))
                if psz:
                    inside(p.get("box", {}), psz[0] / 2, psz[1] / 2, "%s piece %d" % (where, j))
        else:
            errs.append("%s: unknown kind" % where)
    look = spec.get("look") or {}
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
    for s, a in zip(spec["shots"], st):
        k = s["kind"]
        if k == "brand":
            cues += [(a + 12, "reveal", 0.7), (a + 22, "whoosh", 0.25)]
        elif k == "title":
            cues.append((a + 6, "whoosh", 0.32))
        elif k == "outro":
            sa = a + int(s.get("stampAt", 46))
            n = len(s.get("pieces") or [])
            for i in range(n):
                at = a + 2 + i * (28 / max(1, n - 1))
                cues.append((int(at + 10), "whoosh", 0.22))
            cues += [(sa - 2, "riser", 0.55), (sa + 3, "impact", 0.9), (sa + 18, "sparkle", 0.4)]
        elif k == "page":
            keys = s.get("keys") or []
            for k0, k1 in zip(keys, keys[1:]):
                travel = abs(k1["cx"] - k0["cx"]) + abs(k1["cy"] - k0["cy"]) + 400 * abs(k1.get("zoom", 1) - k0.get("zoom", 1)) \
                    + 6 * (abs(k1.get("rx", 0) - k0.get("rx", 0)) + abs(k1.get("ry", 0) - k0.get("ry", 0)))
                if travel > 120 and k1["f"] - k0["f"] <= 60:
                    cues.append((a + int((k0["f"] + k1["f"]) / 2), "whoosh", min(0.5, 0.22 + travel / 2000)))
            last_pop, npop = -99, 0
            for l in s.get("layers") or []:
                kind = l.get("kind")
                if kind == "pop":
                    f = a + int(l["at"] + l.get("dur", 14) * 0.4)
                    if f - last_pop >= 3:
                        cues.append((f, "pop", max(0.12, 0.36 * (0.85 ** npop))))
                        last_pop, npop = f, npop + 1
                elif kind == "lift":
                    cues += [(a + int(l["at"]) + 6, "whoosh", 0.4), (a + int(l["at"]) + 16, "sparkle", 0.3),
                             (a + int(l["until"]) + 14, "settle", 0.45)]
                elif kind == "type":
                    cpf = float(l.get("cpf", 0.5))
                    n = len(l.get("text", ""))
                    for c in range(0, n, 2):
                        cues.append((a + int(l["at"] + c / cpf), "key", 0.22))
                elif kind == "cursor":
                    for c in l.get("clicks") or []:
                        cues.append((a + int(c) + 2, "click", 0.6))
                elif kind == "ring":
                    cues.append((a + int(l["at"]) + 4, "tick", 0.25))
                elif kind == "focus":
                    cues.append((a + int(l["at"]) + 6, "focus", 0.3))
                elif kind == "note":
                    cues.append((a + int(l["at"]) + 4, "chime", 0.25))
    return sorted(cues)


def render_picture(film_dir, spec_path, out, frames=None):
    cmd = ["npx", "remotion", "render" if frames is None else "still", "src/index.ts", "PromoFilm", out,
           "--props=" + spec_path, "--public-dir=" + film_dir]
    if frames is not None:
        cmd.append("--frame=%d" % frames)
    else:
        cmd += ["--codec=h264", "--crf=16", "--concurrency=6"]
    r = subprocess.run(cmd, cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("[promo_film] render failed:\n" + (r.stderr or r.stdout)[-3000:])


def mix(film_dir, silent, cues, total_frames, out, bgm=None):
    import sfx
    secs = total_frames / FPS
    wav = os.path.join(film_dir, "_promo_sfx.wav")
    if not sfx.build_sfx_track([(f / FPS, c, g) for f, c, g in cues], secs, wav):
        raise SystemExit("[promo_film] numpy is needed to synthesise the sound")
    inputs = ["-i", silent, "-i", wav]
    if bgm == "auto":
        pad = os.path.join(film_dir, "_promo_bgm.wav")
        sfx._write_wav(pad, sfx.synth_pad(secs + 1))
        inputs += ["-i", pad]
    elif bgm:
        inputs += ["-i", bgm]
    if len(inputs) == 6:
        graph = ("[1:a]highpass=f=120,volume=1.0[s];[2:a]lowpass=f=4000,volume=0.28,afade=t=in:d=1.5,"
                 "afade=t=out:st=%.2f:d=2[b];[s][b]amix=inputs=2:normalize=0,alimiter=limit=0.89[a]" % max(0, secs - 2))
    else:
        graph = "[1:a]highpass=f=120,alimiter=limit=0.89[a]"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "%.3f" % secs, out]
    subprocess.run(cmd, check=True)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[0])
        return 2
    refuse_unknown(argv[1:], valued=("spec", "stills", "bgm", "out"), switches=("check", "no-sound"))
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
    silent = os.path.join(film, "_promo_silent.mp4")
    render_picture(film, spec_path, silent)
    out = os.path.join(film, argflag(argv, "out", "out.mp4"))
    if "--no-sound" in argv:
        os.replace(silent, out)
    else:
        cues = spec.get("sfx")
        cues = [(int(c["f"]), c["cue"], float(c.get("gain", 0.4))) for c in cues] if cues else plan_sfx(spec)
        json.dump([{"f": f, "cue": c, "gain": round(g, 3)} for f, c, g in cues], open(os.path.join(film, "promo_sfx.json"), "w"), indent=0)
        mix(film, silent, cues, total, out, argflag(argv, "bgm", None))
    print("[promo_film] wrote " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
