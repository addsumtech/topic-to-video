#!/usr/bin/env python3
"""Every object in the film, at the frame where it is LARGEST, cropped at 100% from the delivered frames.

    python3 scripts/object_closeups.py <out_dir> [--every=N]     # writes <out_dir>/_object_closeups.png (+ .json)

EXIT 0 = sheet written · 2 = not measured (no out.mp4, the census died, or no frame could be read).

WHY THIS EXISTS. A product film put an Apple Watch and a MacBook side by side. Three review rounds judged the
watch at 100% — it was the hero — and nobody looked at the laptop beside it: its lid turned in 3D while its base
stayed a flat front-on sliver, no deck, no keys, a dead dark screen. Every gate was green, and the critic's sheets
(the contact sheet, a frame per beat; the fidelity sheet, only for objects the film DECLARED real) both let it
pass: on the contact sheet the laptop was a 300 px thumbnail, and it was not a declared built thing. The user had
to ask three times that EVERY object be refined and accurate.

THE SHEET. The Film is rendered once with the DOM census armed (runtime/mediaRes.tsx, which reports the boxes of
every object as well as every picture): every device the kit draws (`data-device-body`, named by its model), every
screen on one (`data-device-screen`) and every element a shot marks `data-object="<name>"` (a built thing, a bot, a
dial — anything that depicts something). For each object in each beat the frame where it is drawn largest (at
least half opaque) is pulled from the delivered out.mp4 and the object's box is cropped at 100% — never scaled — so
the sheet shows exactly the pixels the viewer gets. Each crop is labelled with its name, beat and timecode.

The critic gives EVERY object on it a verdict (agents/shot-critic.md S16), and the maker looks at it before
delivery (SKILL.md). It also feeds device_fidelity_qa's DEAD-SCREEN check: `_object_closeups.json` keeps every
sampled box of every device screen, so the screen's pixels can be read over its whole time on screen.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SHEET = "_object_closeups.png"
RECORD = "_object_closeups.json"
MIN_SIDE = 24            # an object drawn smaller than this on both sides is a mark, not something to look at
MIN_OPACITY = 0.5        # fainter than this it is arriving or leaving
PAD = 0.06               # the crop's margin around the box, of its larger side
SHEET_W = 2400           # crops are packed into rows no wider than this (a wider crop gets a row of its own)
LABEL_H = 34
LABEL_FONTS = ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
               "/System/Library/Fonts/STHeiti Medium.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
               "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc")


def film_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def pick(frames, beat_of, W, H):
    """{(beat, name): {"frame", "box", "area", "seen"}} — each object's largest drawn box per beat. `frames` is
    {frame: census}, a census's `o` rows being [name, x, y, w, h, opacity]. A box is clipped to the frame first;
    one under MIN_SIDE on both sides or fainter than MIN_OPACITY is not looked at. `seen` counts the frames it was.
    An object that holds its size (a device standing still) is taken at the MIDDLE of its frames at that size —
    its settled picture, not the first frame it reached it. And an object a seam carries into the next beat's first
    frames at the size it had (the same box, seen on fewer frames there) is shown once, in the beat it belongs to."""
    seen = {}
    for f in sorted(frames):
        for row in frames[f].get("o") or []:
            name, x, y, w, h, op = row[:6]
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(W, x + w), min(H, y + h)
            cw, ch = x1 - x0, y1 - y0
            if cw <= 0 or ch <= 0 or (cw < MIN_SIDE and ch < MIN_SIDE) or op < MIN_OPACITY:
                continue
            seen.setdefault((beat_of(f), name), []).append((f, cw * ch, [x0, y0, cw, ch]))
    best = {}
    for k, rows in seen.items():
        top = max(a for _, a, _ in rows)
        near = [r for r in rows if r[1] >= 0.98 * top]
        f, area, box = near[len(near) // 2]
        best[k] = {"frame": f, "box": box, "area": area, "seen": len(rows)}
    for (beat, name) in sorted(best):
        here = best.get((beat, name))
        for other in (beat - 1, beat + 1):
            o = best.get((other, name))
            if here is None or o is None:
                continue
            same = all(abs(a - b) <= 3 for a, b in zip(here["box"][2:], o["box"][2:]))
            if same and here["seen"] < o["seen"]:
                del best[(beat, name)]
                here = None
    return best


def screens(frames, beat_label=lambda f: None):
    """{name: [[frame, x, y, w, h, beat], ...]} — every sampled box of every device screen (`screen:` rows)."""
    out = {}
    for f in sorted(frames):
        for row in frames[f].get("o") or []:
            if str(row[0]).startswith("screen:") and row[5] >= MIN_OPACITY:
                out.setdefault(row[0], []).append([f] + [int(round(v)) for v in row[1:5]] + [beat_label(f)])
    return out


def crop_box(box, W, H):
    x, y, w, h = box
    p = PAD * max(w, h)
    x0, y0 = max(0, int(x - p)), max(0, int(y - p))
    return x0, y0, min(W, int(x + w + p + 0.999)), min(H, int(y + h + p + 0.999))


def pack(sizes, max_w=SHEET_W, gap=16):
    """Top-left positions for tiles of `sizes` [(w, h)] packed left to right into rows no wider than max_w; and the
    sheet's (w, h). A tile wider than max_w gets a row of its own — it is never scaled."""
    pos, x, y, row_h, width = [], gap, gap, 0, 0
    for w, h in sizes:
        if x > gap and x + w + gap > max_w:
            x, y, row_h = gap, y + row_h + gap, 0
        pos.append((x, y))
        x += w + gap
        row_h = max(row_h, h)
        width = max(width, x)
    return pos, (max(width, 2 * gap), y + row_h + gap)


def frame_png(video, frame, fps, dest):
    t = (frame + 0.5) / fps
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.4f" % t, "-i", video, "-frames:v", "1", dest],
                       capture_output=True, text=True)
    return r.returncode == 0 and os.path.isfile(dest)


def video_fps(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    first = (r.stdout.strip().splitlines() or ["30/1"])[0].strip().strip(",")
    num, _, den = first.partition("/")
    try:
        fps = float(num) / float(den or 1)
    except ValueError:
        raise SystemExit("[object_closeups] ffprobe gave no frame rate for %s: %r" % (video, r.stdout))
    if not fps > 0:
        raise SystemExit("[object_closeups] ffprobe gave a frame rate of %r for %s" % (first, video))
    return fps


def build_sheet(items, frame_files, out_path):
    """items: [{"name", "beat", "label", "frame", "box"}]; frame_files: {frame: png}. Writes the sheet."""
    from PIL import Image, ImageDraw, ImageFont
    tiles = []
    for it in items:
        with Image.open(frame_files[it["frame"]]) as im:
            W, H = im.size
            c = im.convert("RGB").crop(crop_box(it["box"], W, H))
        tiles.append((it, c))
    font = None
    for path in LABEL_FONTS:                     # a CJK face: an object's name may be in the film's language
        try:
            font = ImageFont.truetype(path, 20)
            break
        except OSError:
            continue
    if font is None:
        print("[object_closeups] note: no CJK font found (%s) — labels in the default face" % ", ".join(LABEL_FONTS))
        font = ImageFont.load_default()
    # a tile is as wide as its crop or its label, whichever is wider: a label never runs into the next tile
    sizes = [(max(c.width, int(font.getlength(it["label"])) + 12), c.height + LABEL_H) for it, c in tiles]
    pos, (sw, sh) = pack(sizes)
    sheet = Image.new("RGB", (sw, sh), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    for (it, c), (x, y) in zip(tiles, pos):
        d.text((x, y + 6), it["label"], fill=(235, 238, 242), font=font)
        sheet.paste(c, (x, y + LABEL_H))
    sheet.save(out_path)
    return sheet.size


def run(out_dir, every=3):
    import media_res_qa as mr
    video = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(video):
        return None, "no out.mp4 — render the film first (render_remotion.py)"
    fps = video_fps(video)                      # read first: a census is minutes, a bad file should fail at once
    res, segs, slides, total = mr.census_film(out_dir, every)
    want = (total - 1) // every + 1
    import text_safe_qa as ts
    why = ts._glide_measured(res, want)
    if why:
        return None, why
    frames = res["frames"]
    if not any(r.get("o") for r in frames.values()):
        return None, ("the census reports no object box on any frame — the runtime predates the object census, "
                      "or nothing marks data-device-body / data-object")

    def beat_of(frame):
        for k, (a, b) in enumerate(segs):
            if a <= frame <= b:
                return k
        return len(segs) - 1

    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="closeups_")
    first = frame_png(video, 0, fps, os.path.join(tmp, "probe.png"))
    if not first:
        return None, "ffmpeg could not read a frame of out.mp4"
    with Image.open(os.path.join(tmp, "probe.png")) as im:
        W, H = im.size
    best = pick(frames, beat_of, W, H)
    labels = [s.get("index", i + 1) for i, s in enumerate(slides)]
    shots = [s.get("shot") or "?" for s in slides]
    items = []
    for (beat, name), b in sorted(best.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        t = b["frame"] / fps
        items.append({"name": name, "beat": labels[beat] if beat < len(labels) else beat + 1,
                      "shot": shots[beat] if beat < len(shots) else "?", "frame": b["frame"], "t": round(t, 2),
                      "box": [int(round(v)) for v in b["box"]], "seen": b["seen"],
                      "label": "%s · beat %s %s · %d:%05.2f · %dx%d px" % (
                          name, labels[beat] if beat < len(labels) else beat + 1,
                          shots[beat] if beat < len(shots) else "?", int(t // 60), t % 60, b["box"][2], b["box"][3])})
    files = {}
    for it in items:
        if it["frame"] not in files:
            p = os.path.join(tmp, "f%06d.png" % it["frame"])
            if not frame_png(video, it["frame"], fps, p):
                return None, "ffmpeg could not read frame %d of out.mp4" % it["frame"]
            files[it["frame"]] = p
    size = build_sheet(items, files, os.path.join(out_dir, SHEET)) if items else None
    rec = {"film": film_sha(video), "fps": fps, "frame_size": [W, H], "every": every, "sampled": len(frames),
           "objects": [{k: v for k, v in it.items() if k != "label"} for it in items],
           "screens": screens(frames, lambda f: labels[beat_of(f)] if beat_of(f) < len(labels) else beat_of(f) + 1), "sheet": SHEET if items else None}
    with open(os.path.join(out_dir, RECORD), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    return {"items": items, "size": size, "record": rec}, None


def status(out_dir):
    """'missing' | 'stale' (out.mp4 changed since the sheet) | 'ok' — for critic_brief."""
    rp, video = os.path.join(out_dir, RECORD), os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(rp) or not os.path.isfile(os.path.join(out_dir, SHEET)):
        return "missing"
    try:
        rec = json.load(open(rp, encoding="utf-8"))
    except (OSError, ValueError):
        return "missing"
    if not os.path.isfile(video) or rec.get("film") != film_sha(video):
        return "stale"
    return "ok"


def objects(out_dir):
    try:
        return json.load(open(os.path.join(out_dir, RECORD), encoding="utf-8")).get("objects") or []
    except (OSError, ValueError):
        return []


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Every object in the film at its largest, cropped at 100%.")
    ap.add_argument("out_dir")
    ap.add_argument("--every", type=int, default=3)
    a = ap.parse_args(argv)
    r, why = run(a.out_dir, max(1, a.every))
    if r is None:
        print("[object_closeups] NOT MEASURED: %s" % why)
        return 2
    for it in r["items"]:
        print("[object_closeups] %s" % it["label"])
    if not r["items"]:
        print("[object_closeups] no object is drawn large enough to look at anywhere in this film")
    else:
        print("[object_closeups] %s  %d object(s) · %dx%d — give EVERY one a verdict (shot-critic S16)"
              % (os.path.join(a.out_dir, SHEET), len(r["items"]), r["size"][0], r["size"][1]))
    import device_fidelity_qa as dq
    for w in dq.dead_screens(a.out_dir):
        print("[object_closeups] WARN  " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
