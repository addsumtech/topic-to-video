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

HTML / image tier, overlay captions (render.py burns them). A REMOTION film is read differently, from its type census
(check_remotion: the ground beside the caption block, column by column — see the note above RM_STRIP). Not read: band
mode (its own strip), a clip rendered before the manifest existed. A platform-safe film is read like
any other: its records hold frame coordinates.
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


# WHY THE REMOTION TIER WAS NOT READ (2026-10-31) — superseded by check_remotion below, which needs no glyph mask. Film.tsx's CaptionTrack picks its ink from
# the beat's GROUND TOKEN (light.tsx captionInk(dnaGroundY / groundAt)) — a design-time luminance, not the pixels
# under the caption — and a register reserves the caption band, so that token IS the ground except on the registers
# remotion/band_debt.json lists (full-bleed photos and fields). The browser cannot read its own composited pixels, so
# measuring them means a second pass: render each chunk's window WITHOUT captions (`captions: false`, three stills a
# chunk through the segment cache), measure the pixels under the caption block, and hand the chunk's ink, outline and
# highlight to Film.tsx as props (CaptionTrack today has one ink and a text-shadow in the ground token). And this
# gate would need the caption's glyph places from the film — the type census (textSafe.tsx) lists the caption HUD's
# lines but not its glyph masks, and PIL cannot draw Chrome's bundled webfont at Chrome's positions; the record would
# have to come from the DOM. Roughly: a stills pass (~3 stills x chunks, minutes a film), a props channel, a census
# record of the caption's lines and face, and a mask drawn in Chrome. Until then this gate says NOT MEASURED.
REMOTION_WHY = ("a Remotion film: Film.tsx picks its caption ink from the beat's ground token, not from pixels, and "
                "nothing records where its glyphs sit — this gate does not read it (see REMOTION_WHY in "
                "scripts/caption_contrast_qa.py for what it would take)")


# THE REMOTION TIER, READ AFTER ALL (2026-11-12) — without a glyph mask. WorkBuddy beat 6: the caption's first word sat
# on a Blender laptop's black bezel, dark ink on a dark bar, "Wo" melted — and no gate looked. The census records each
# caption line's box (Film.tsx's caption spans, in the caption band); the GROUND is read in thin strips just above the
# block's first line and below its last, where no glyph is, column by column. A column melts where the ground on BOTH
# sides is under MIN_CONTRAST against the ink (an object that runs behind the line — a bar, an edge, a dark field — is
# there on both sides; a glyph's own neighbourhood is not sampled). The ink is whichever of Film's two caption inks
# (light.tsx CAPTION_INK_DARK / _LIGHT) stands out from the block's ground — the one Film picked. A LETTER is lost when a
# letter-wide window (the caption's font size) is mostly melted.
RM_STRIP = (3, 8)          # px (full frame) between the line box and the strip, and the strip's far edge
RM_EVERY = 5               # judge every 5th frame
RM_LETTER_ERROR, RM_LETTER_WARN = 0.5, 0.3
RM_SCALE = 2               # decode at half size: a 3:1 ground read needs no glyph detail


def _hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64)


def _caption_inks():
    import re as _re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "src", "runtime", "light.tsx"),
               encoding="utf-8").read()
    got = [_re.search(r"export const %s = '(#[0-9a-fA-F]{6})'" % n, src) for n in ("CAPTION_INK_DARK", "CAPTION_INK_LIGHT")]
    if not all(got):
        raise RuntimeError("CAPTION_INK_DARK / CAPTION_INK_LIGHT not found in runtime/light.tsx")
    return [_hex_rgb(m.group(1)) for m in got]


def caption_blocks(lines, W, H):
    """The caption's lines on one census frame, as one block: [(x0, x1, top, bottom, px)] per line, top to bottom —
    the census lines that sit in the caption band (Film's caption spans; a line's lit and unlit spans merged)."""
    from _caption_band import caption_band_px
    band_top = H - caption_band_px(W, H)
    rows = {}
    for ln in lines:
        if ln.get("o", 1) < 0.5 or ln["y"] < band_top or not str(ln.get("t", "")).strip():
            continue
        k = int(round(ln["y"]))
        r = rows.setdefault(k, [ln["x"], ln["x"] + ln["w"], ln["y"], ln["y"] + ln["h"], ln.get("px") or ln["h"] * 0.8])
        r[0], r[1] = min(r[0], ln["x"]), max(r[1], ln["x"] + ln["w"])
    return [tuple(v) for _k, v in sorted(rows.items())]


GLYPH_MIN = 0.02   # share of the line boxes on one side of their own median ground that is letters
GLYPH_STEP = 24.0  # grey levels from the ground's median that put a pixel on one side of it


def judge_caption_block(frame, block, inks, scale=1):
    """(worst letter-wide melted share, ink rgb, x of that window) of one caption block on one frame, or None."""
    if not block:
        return None
    Hh, Ww = frame.shape[:2]
    a, b = RM_STRIP
    top, bot = block[0][2], block[-1][3]
    x0, x1 = min(r[0] for r in block), max(r[1] for r in block)
    c0, c1 = max(0, int(x0 / scale)), min(Ww, int(x1 / scale))
    ya = (max(0, int((top - b) / scale)), max(0, int((top - a) / scale)))
    yb = (min(Hh, int((bot + a) / scale)), min(Hh, int((bot + b) / scale)))
    if c1 - c0 < 8 or ya[1] <= ya[0] or yb[1] <= yb[0]:
        return None
    above = _lum(frame[ya[0]:ya[1], c0:c1].reshape(-1, 3)).reshape(ya[1] - ya[0], c1 - c0)
    below = _lum(frame[yb[0]:yb[1], c0:c1].reshape(-1, 3)).reshape(yb[1] - yb[0], c1 - c0)
    # THE INK FILM DREW, read off the glyphs — not the better of the two for this ground. Film picks its ink from the
    # beat's ground TOKEN (Film.tsx captionInk), not from the pixels, so "the ink that would contrast best" passed a
    # caption drawn in the wrong one. Film's two inks are a dark and a light one, so the letters are told by which
    # SIDE of their ground they sit on — the ground being the line boxes' own median (letters cover well under half of
    # a line box; the strips above and below can hold a panel the line sits under). Direction, not an exact colour:
    # anti-aliasing at the decode scale, a caption fading out and karaoke's unlit words all move a glyph's colour but
    # never its side. When neither side shows letters, the census says a caption is there and none can be seen: it
    # has melted whole, and is judged so.
    inside = np.concatenate([frame[max(0, int(r[2] / scale)):min(Hh, int(r[3] / scale)),
                                   max(0, int(r[0] / scale)):min(Ww, int(r[1] / scale))].reshape(-1, 3) for r in block])
    if not len(inside):
        return None
    gi = inside.astype(np.float64).mean(axis=1)
    g0 = float(np.median(gi))
    dark, light = float((gi < g0 - GLYPH_STEP).mean()), float((gi > g0 + GLYPH_STEP).mean())
    by_lum = sorted(inks, key=lambda c: float(c.mean()))           # [the dark ink, the light ink]
    if max(dark, light) < GLYPH_MIN:
        ink = min(inks, key=lambda c: abs(float(c.mean()) - g0))
        return 1.0, ink, c0 * scale
    ink = by_lum[0] if dark >= light else by_lum[-1]
    li = _lum(ink[None, :])[0]
    melt = (np.median(_contrast(li, above), axis=0) < MIN_CONTRAST) & (np.median(_contrast(li, below), axis=0) < MIN_CONTRAST)
    win = max(4, int(round(max(r[4] for r in block) / scale)))
    if len(melt) < win:
        return None
    share = np.convolve(melt.astype(np.float64), np.ones(win) / win, mode="valid")
    k = int(np.argmax(share))
    return float(share[k]), ink, (c0 + k) * scale


def check_remotion(out_dir, video=None):
    """The Remotion tier: every RM_EVERY-th frame clear of a seam, every caption block, its worst letter-wide window."""
    import jitter_qa as jq
    import remotion_segments as _rs
    video = video or os.path.join(out_dir, "out.mp4")
    state, _b, why = _rs.render_currency(out_dir, video)
    if state == "stale":
        return {"skipped": "out.mp4 is not a render of the board as it is now: %s — re-render, then judge" % why,
                "rows": [], "unmeasured": True}
    frames_c, segs = jq.film_census(out_dir)
    seams = jq.film_seams(out_dir)
    W, H = _probe_wh(video)
    inks = _caption_inks()
    want = [f for f in sorted(frames_c) if f % RM_EVERY == 0 and f not in seams and caption_blocks(
        frames_c[f].get("lines") or [], W, H)]
    dec = _decode_scaled(video, want, W // RM_SCALE, H // RM_SCALE)
    rows = []
    cap_beats = sorted({next((k + 1 for k, (a, b) in enumerate(segs) if a <= f <= b), None) for f in want} - {None})
    for f in want:
        if f not in dec:
            continue
        block = caption_blocks(frames_c[f].get("lines") or [], W, H)
        got = judge_caption_block(dec[f], block, inks, RM_SCALE)
        if got is None:
            continue
        share, ink, x = got
        beat = next((k + 1 for k, (a, b) in enumerate(segs) if a <= f <= b), None)
        text = " / ".join(" ".join(str(l.get("t", "")) for l in (frames_c[f].get("lines") or [])
                                    if abs(l["y"] - r[2]) < 1) for r in block)
        rows.append({"beat": beat, "text": text, "word": None, "melt": round(share, 3), "frame": f, "x": x,
                     "ink": [int(v) for v in ink], "level": "error" if share >= RM_LETTER_ERROR else
                     "warn" if share >= RM_LETTER_WARN else "ok"})
    keep = {}
    for r in rows:                                     # one row per beat and caption text: its worst frame
        k = (r["beat"], r["text"])
        if k not in keep or r["melt"] > keep[k]["melt"]:
            keep[k] = r
    # COVERAGE IS COUNTED IN BEATS. `jobs` was len(rows), so a film where no caption block was found (or none could be
    # read) printed "OK — 0 caption chunk(s)" and exited 0: unmeasured read as clean. A narrated beat with no caption
    # in the census, or one whose caption could not be read on any frame, is listed and the run is not clean.
    import render_remotion as _rr
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}

    def burns(sl):        # Film burns this beat's caption — unless its own headline sets the line (captionOnScreen)
        cap = (sl.get("caption") or _rr._caption_for_eye(sl.get("narration") or sl.get("script") or "")).strip()
        return bool(cap) and not (meta.get("caption_on_screen") is not False and _rr.caption_on_screen(
            {"shot": sl.get("shot"), "props": sl.get("shot_props") or {}, "caption": cap}))
    spoken = [k + 1 for k, sl in enumerate(board.get("slides") or []) if burns(sl)]
    judged = {r["beat"] for r in keep.values()}
    unseen = [{"beat": b, "text": "(no caption read on this beat%s)" % ("" if b in cap_beats else " — none in the census")}
              for b in spoken if b not in judged]
    return {"skipped": None, "rows": list(keep.values()), "jobs": len(keep) + len(unseen), "unseen": unseen,
            "no_record": [], "remotion": True}


def _probe_wh(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def _decode_scaled(video, wanted, W, H):
    want, out = set(wanted), {}
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=%d:%d" % (W, H), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n, last = 0, max(want) if want else -1
    while n <= last:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        if n in want:
            out[n] = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        n += 1
    p.kill()
    return out


PRESENT = 0.6     # share of the glyph cores that must carry one ink for the caption to be "there" on a frame


def judge_frame(frame, core, edge):
    """(melting share of the edge, ink rgb) on one decoded frame, or (None, None) when the caption is not there: its
    cores do not carry one ink (a karaoke word in its highlight is a minority; a different caption, or none, is not)."""
    if core.sum() < 20 or edge.sum() < 20:
        return None, None
    px = frame[core].astype(np.float64)
    ink = np.median(px, axis=0)
    near = np.abs(px - ink).max(axis=1) <= 40
    inks = [ink]
    if near.mean() < PRESENT:
        # A SHORT CHUNK HALF IN ITS HIGHLIGHT carries two inks, neither a majority (「叫定位方块。」 with 定位 lit: the QR
        # film's three short chunks were never read). The second ink is the median of what the first leaves; the
        # caption is there when the two together carry the cores, and the worse of the two is its verdict.
        rest = px[~near]
        ink2 = np.median(rest, axis=0)
        near2 = np.abs(px - ink2).max(axis=1) <= 40
        if (near | near2).mean() < PRESENT or near2.mean() < 0.15 or near.mean() < 0.15:
            return None, None
        inks = [ink, ink2]
    g = _lum(frame[edge])
    worst = max(((float((_contrast(_lum(k[None, :])[0], g) < MIN_CONTRAST).mean()), k) for k in inks), key=lambda t: t[0])
    return worst


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
    if not os.path.exists(os.path.join(out_dir, "storyboard.json")):
        # a promo film (promo.json) burns no caption; anything else without a board cannot be read
        if os.path.exists(os.path.join(out_dir, "promo.json")):
            return {"skipped": "a promo film: no burned captions", "rows": []}
        return {"skipped": "no storyboard.json in %s" % out_dir, "rows": [], "unmeasured": True}
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = dict(board.get("meta") or {}, _out=out_dir)
    slides = board.get("slides") or []
    if meta.get("captions") is False:
        return {"skipped": "captions are off", "rows": []}
    if str(meta.get("renderer") or "local").lower().startswith("remotion"):
        return check_remotion(out_dir, video)
    if meta.get("captions") is False:
        return {"skipped": "captions are off", "rows": []}
    if rd._caption_band_px(meta, int(meta.get("width") or 1920), int(meta.get("height") or 1080)):
        return {"skipped": "band mode: the caption sits on its own strip", "rows": []}
    fps = meta.get("fps", 30)
    video = video or os.path.join(out_dir, "out.mp4")
    if not os.path.exists(video):
        return {"skipped": "no %s" % os.path.basename(video), "rows": [], "unmeasured": True}
    # the frame the captions were burned on is the DELIVERED frame: a --vertical render with no meta.width/height was
    # decoded at 1920x1080 and every caption mask landed in the wrong place
    W, H = _probe_wh(video)
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
            unseen.append({"beat": j["beat"], "text": j.get("word") or j["text"], "word": bool(j.get("word"))})
    # one row per caption and per spoken word: keep the worst of each
    keep = {}
    for r in rows:
        k = (r["beat"], r["text"], r["word"])
        if k not in keep or r["melt"] > keep[k]["melt"]:
            keep[k] = r
    rows = list(keep.values())
    return {"skipped": None, "rows": rows, "jobs": len(jobs), "unseen": unseen, "no_record": no_record}


def _unmeasured(rep):
    """a chunk or beat not read (karaoke word layers aside), or a clip with no caption manifest"""
    return bool(rep.get("no_record")) or any(not u.get("word") for u in rep.get("unseen") or [])


def main(argv):
    import argparse
    if not argv:
        print(__doc__.strip())
        return 2
    ap = argparse.ArgumentParser(description="Is every burned caption legible on the ground it was burned on?")
    ap.add_argument("out_dir")
    ap.add_argument("--video", help="the film to measure (default <out_dir>/out.mp4)")
    ap.add_argument("--json", help="also write the report to this path")
    a = ap.parse_args(argv)
    video, jp = a.video, a.json
    rep = check(a.out_dir, video)
    if jp:
        json.dump(rep, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if rep["skipped"]:
        print("[caption_contrast] NOT MEASURED: %s" % rep["skipped"])
        return 2 if rep.get("unmeasured") else 0
    for r in rep["rows"]:
        if r["level"] != "ok" and rep.get("remotion"):
            print("[caption_contrast] %s beat %s: a letter-wide stretch of the caption is %.0f%% on ground under %.0f:1 "
                  "against its ink %s (frame %d, x %d) — something in the picture runs behind the line: keep it out "
                  "of the caption band — 「%s」" % (r["level"].upper(), r["beat"], r["melt"] * 100, MIN_CONTRAST,
                                                  "#%02x%02x%02x" % tuple(r["ink"]), r["frame"], r["x"], r["text"][:40]))
        elif r["level"] != "ok":
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
          % ("FAIL" if errs else "NOT FULLY MEASURED" if _unmeasured(rep) else "OK", n, worst * 100, ERROR_FRAC * 100, WARN_FRAC * 100))
    # a caption CHUNK (or a beat) nobody could read is NOT MEASURED, not clean: 2 — it was 0 unless nothing at all was
    # read. A karaoke WORD read at its one mid-window frame is a finer look at a chunk already judged; missing it is said
    # above, not a refusal (the QR film: 24 of 483 such words, every chunk measured)
    return 1 if errs else (2 if _unmeasured(rep) else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
