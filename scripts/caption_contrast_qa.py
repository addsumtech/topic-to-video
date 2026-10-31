#!/usr/bin/env python3
"""Does every burned caption read against the pixels right around it — on the delivered film, over its whole window?

    python3 scripts/caption_contrast_qa.py <out_dir> [--json PATH] [--video PATH]

WHY. An overlay caption sits on the frame's own ground: no strip, no scrim, no white halo — the standing rule. On a
flat page that is easy; on a photograph the ground is a thousand colours and moves under a Ken Burns. A validation
film (蜂巢, 1:1, 2026-10-31) burned a dark caption over a bright amber bee close-up and a busy frame of cells and bees,
with every gate green — no gate looked at a caption's contrast — and its author painted a scrim into the photos by
hand to make it read. render.py now measures the pixels under each caption (_caption_inks); this gate measures what
was DELIVERED, from out.mp4, the way a reader meets it.

HOW. render.py writes, beside every scene clip, the record of each caption it burned (.clips/clip_NN.mp4.captions.json:
lines, face, places, window, inks). For every caption chunk, three frames inside its window (clear of the scene's
seams) are decoded from out.mp4; the glyphs are located by drawing the recorded lines with the recorded face at the
recorded places (a mask, no outline); the INK is the median of the frame under the glyphs' cores; the EDGE is every pixel within the outline's
width + 1 px outside the glyphs — the zone that separates a stroke from what is behind it, which is exactly what an
outline in the ground's own far tone is for. A pixel of that edge whose WCAG contrast with the ink is under 3:1 (AA for
large text) is a place where the letter melts into the picture.

  ERROR  more than 25% of a caption's edge melts on some frame of its window
  WARN   more than 10%

HTML / image tier, overlay captions (render.py burns them). Not read here, and said so: a Remotion film (Film.tsx
draws its captions), band mode (its own strip), a platform-safe film, a clip rendered before the manifest existed.
Exit 1 on an ERROR, 2 when nothing could be measured.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ERROR_FRAC, WARN_FRAC = 0.25, 0.10
MIN_CONTRAST = 3.0
SEAM_PAD = 0.35            # s kept clear of a scene's start and end (its dip / seam fades the whole frame)


def _lum(a):
    a = a.astype(np.float64) / 255.0
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def _contrast(l1, l2):
    hi, lo = np.maximum(l1, l2), np.minimum(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def caption_mask(rec, W, H, runs=None):
    """(core, edge) boolean masks of one caption AS IT WAS DRAWN — its manifest record (render.py
    _write_caption_manifest: lines, face, places): the glyphs' cores (eroded 1 px) and the edge zone (the outline's
    width + 1 px outside the glyphs). `runs` ([x, y, text], the record's `hl_runs`) masks only those runs — the
    spoken word, judged in the colour it was drawn in."""
    from PIL import Image, ImageDraw, ImageFilter
    import render as rd
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    path, size = rec["font"]
    font = rd._load_font(int(size), path)
    for x, y, ln in (runs if runs is not None else [(x, y, ln) for ln, (x, y) in zip(rec["lines"], rec["xy"])]):
        d.text((x, y), ln, font=font, fill=255)
    glyph = m.point(lambda v: 255 if v >= 128 else 0)
    sw = int(rec.get("outline_px") or rd.caption_outline_px(font))
    core = glyph.filter(ImageFilter.MinFilter(3))
    near = glyph.filter(ImageFilter.MaxFilter(3))
    far = glyph.filter(ImageFilter.MaxFilter(2 * (sw + 1) + 1))
    edge = np.asarray(far) > 0
    edge &= ~(np.asarray(near) > 0)
    return np.asarray(core) > 0, edge


PRESENT = 0.6     # share of the glyph cores that must carry one ink for the caption to be "there" on a frame


def judge_frame(frame, core, edge):
    """(melting share of the edge, ink rgb) on one decoded frame, or (None, None) when the caption is not there: its
    cores do not carry one ink (a karaoke word in its highlight is a minority; a different caption, or none, is not)."""
    if core.sum() < 20 or edge.sum() < 20:
        return None, None
    px = frame[core].astype(np.float64)
    ink = np.median(px, axis=0)
    if (np.abs(px - ink).max(axis=1) <= 40).mean() < PRESENT:
        return None, None
    c = _contrast(_lum(ink[None, :])[0], _lum(frame[edge]))
    return float((c < MIN_CONTRAST).mean()), ink


def _decode(video, wanted, W, H):
    """{frame index: rgb array} for the wanted frames, by sequential decode (a seek can land frames off)."""
    want, out = set(wanted), {}
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    n, last = 0, max(want) if want else -1
    while n <= last:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        if n in want:
            out[n] = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        n += 1
    p.kill()
    return out


def check(out_dir, video=None):
    import render as rd
    import jitter_html as jh
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = dict(board.get("meta") or {}, _out=out_dir)
    slides = board.get("slides") or []
    if str(meta.get("renderer") or "local").lower().startswith("remotion"):
        return {"skipped": "a Remotion film: Film.tsx draws its captions (not read by this gate)", "rows": []}
    if meta.get("captions") is False:
        return {"skipped": "captions are off", "rows": []}
    if rd._caption_band_px(meta, int(meta.get("width") or 1920), int(meta.get("height") or 1080)):
        return {"skipped": "band mode: the caption sits on its own strip", "rows": []}
    W, H = int(meta.get("width") or 1920), int(meta.get("height") or 1080)
    if rd._platform_safe(meta, W, H):
        return {"skipped": "a platform-safe film: its caption sits on the page's own band (not read by this gate)",
                "rows": []}
    fps = meta.get("fps", 30)
    video = video or os.path.join(out_dir, "out.mp4")
    if not os.path.exists(video):
        return {"skipped": "no %s" % os.path.basename(video), "rows": [], "unmeasured": True}
    counts, _src = jh.scene_frames(out_dir, slides, fps, jh.video_frames(video))
    counts = list(counts)
    starts = np.cumsum([0] + counts[:-1]).tolist()
    jobs, no_record = [], []
    for i, s in enumerate(slides):
        dur = counts[i] / float(fps)
        mp = rd.caption_manifest_path(os.path.join(out_dir, ".clips", "clip_%02d.mp4" % s.get("index", i + 1)))
        if not os.path.exists(mp):
            no_record.append(i + 1)
            continue
        # ONE job per caption CHUNK, over its whole window: karaoke burns a chunk as one layer per word, a few frames
        # each — the chunk's own lines, in the ink most of its words carry
        by = {}
        for rec in json.load(open(mp, encoding="utf-8")).get("captions") or []:
            if rec.get("band") or not rec.get("lines"):
                continue
            j = by.setdefault(rec["text"], {"rec": rec, "a": rec["start"], "b": rec["end"]})
            if j["rec"].get("hl_runs") and not rec.get("hl_runs"):
                j["rec"] = rec                          # the plain layer, when there is one, for the base ink
            j["a"], j["b"] = min(j["a"], rec["start"]), max(j["b"], rec["end"])
            # THE SPOKEN WORD, in its own colour: its own layer's window, its own glyphs
            if rec.get("hl_runs"):
                a, b = max(rec["start"], SEAM_PAD), min(rec["end"], dur - SEAM_PAD)
                if b > a:
                    jobs.append({"beat": i + 1, "text": rec["text"], "frames": [starts[i] + int(round((a + b) / 2 * fps))],
                                 "rec": rec, "runs": rec["hl_runs"],
                                 "word": "".join(r[2] for r in rec["hl_runs"])})
        for text, j in by.items():
            a, b = max(j["a"], SEAM_PAD), min(j["b"], dur - SEAM_PAD)
            if b <= a:
                continue
            fs = sorted({starts[i] + int(round((a + (b - a) * q) * fps)) for q in (0.2, 0.5, 0.8)})
            jobs.append({"beat": i + 1, "text": text, "frames": fs, "rec": j["rec"]})
    frames = _decode(video, [f for j in jobs for f in j["frames"]], W, H)
    rows, unseen = [], []
    for j in jobs:
        core, edge = caption_mask(j["rec"], W, H, j.get("runs"))
        worst, seen = None, 0
        for f in j["frames"]:
            if f not in frames:
                continue
            melt, ink = judge_frame(frames[f], core, edge)
            if melt is None:
                continue
            seen += 1
            if worst is None or melt > worst[0]:
                worst = (melt, f, [int(x) for x in ink])
        if worst:
            rows.append({"beat": j["beat"], "text": j["text"], "word": j.get("word"), "melt": round(worst[0], 3),
                         "frame": worst[1], "ink": worst[2], "level": "error" if worst[0] > ERROR_FRAC else
                         "warn" if worst[0] > WARN_FRAC else "ok"})
        else:
            unseen.append({"beat": j["beat"], "text": j.get("word") or j["text"]})
    # one row per caption and per spoken word: keep the worst of each
    keep = {}
    for r in rows:
        k = (r["beat"], r["text"], r["word"])
        if k not in keep or r["melt"] > keep[k]["melt"]:
            keep[k] = r
    rows = list(keep.values())
    return {"skipped": None, "rows": rows, "jobs": len(jobs), "unseen": unseen, "no_record": no_record}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    video = next((a.split("=", 1)[1] for a in argv if a.startswith("--video=")), None)
    jp = next((a.split("=", 1)[1] for a in argv if a.startswith("--json=")), None)
    rep = check(argv[0], video)
    if jp:
        json.dump(rep, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if rep["skipped"]:
        print("[caption_contrast] NOT MEASURED: %s" % rep["skipped"])
        return 2 if rep.get("unmeasured") else 0
    for r in rep["rows"]:
        if r["level"] != "ok":
            print("[caption_contrast] %s beat %d: %.0f%% of the %s edge is under %.0f:1 against its ink %s "
                  "(frame %d) — 「%s」" % (r["level"].upper(), r["beat"], r["melt"] * 100,
                                          "highlighted word 「%s」's" % r["word"] if r.get("word") else "caption's",
                                          MIN_CONTRAST, "#%02x%02x%02x" % tuple(r["ink"]), r["frame"], r["text"][:24]))
    n = len(rep["rows"])
    if rep.get("no_record"):
        print("[caption_contrast] NOT MEASURED beat(s) %s: no caption manifest beside the clip (rendered before "
              "render.py wrote one — re-render to measure them)" % ", ".join(map(str, rep["no_record"])))
    if n < rep["jobs"]:
        print("[caption_contrast] coverage: %d of %d caption chunks measured — NOT measured (the caption was not "
              "found where this render's layout puts it; was out.mp4 rendered by another version?):" % (n, rep["jobs"]))
        for u in rep.get("unseen") or []:
            print("    beat %d 「%s」" % (u["beat"], u["text"][:30]))
    worst = max((r["melt"] for r in rep["rows"]), default=0.0)
    errs = [r for r in rep["rows"] if r["level"] == "error"]
    print("[caption_contrast] %s — %d caption chunk(s), worst edge melt %.0f%% (ERROR > %.0f%%, WARN > %.0f%%)"
          % ("FAIL" if errs else "OK", n, worst * 100, ERROR_FRAC * 100, WARN_FRAC * 100))
    return 1 if errs else (2 if not n and rep["jobs"] else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
