#!/usr/bin/env python3
"""review_sheet — the delivered film, every beat at 30 / 60 / 90 % plus its first and last second, to LOOK at.

    python3 scripts/review_sheet.py <out_dir> [--video=PATH] [--rows=N]
    python3 scripts/review_sheet.py <film_dir> [--video=design/animatic.mp4]     # director path: shot_plan.json shots

WHY (2026-11-12, the showcase refine). A round of re-cuts passed every gate, and a look by eye at exactly this sheet
then found what none of them measure:
  * a punch-in that cropped a numbered set to 02-08;
  * a message pill flying blank across a title;
  * a window's sidebar sliced into word fragments during a glide;
  * a caption letter sitting on a laptop's black bezel;
  * both ends of a film fading through white;
  * a cinema screen black for ten frames before its cut.
contact_sheet.py shows ONE settled keyframe per beat (composition, palette); a defect in motion is between the
settled frames, and the ends are not in any beat's keyframe at all. This reads the delivered file, so it shows the
film as the viewer gets it.

WHAT IT WRITES (<out_dir>/_review/):
  beats_NN.jpg   up to --rows beats per sheet, a row each: 30 / 60 / 90 % of the beat's own span (its seam excluded);
                 each row's label is on its own strip above the frames, never inside one (a label drawn on a frame
                 once hid a title and read as a cut word, and another hid a long caption's last words)
  ends.jpg       the first 24 frames (every 2nd) and the last 30 (every 3rd)
  index.json     the sheets, and each row's beat, shot and the seconds sampled
DIRECTOR PATH (a <film_dir> with shot_plan.json; video final.mp4): a row per SHOT, at its opening (0.3 s in), 50 % and
90 %. The opening is where a shot is soft or empty and a settled frame never shows it: the Airbnb film (2026-11-25)
opened a phone out of focus for 1.2 s and the user saw it at once ("some pictures are very blurry at first").
ADVISORY: it always exits 0. Its output is for the eye, the reviewer's checklist is in agents/shot-critic.md.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

POINTS = (0.3, 0.6, 0.9)
OPEN = 0.3          # seconds into a shot: how it opens (director path)
CELL_W = 640
ROWS = 8
LABEL_H = 20


def spans(out_dir, n_frames, fps):
    """[(a, b)] film frames per beat — its own span, the seam IN excluded (scripts/beat_clock: the film's _plan.json,
    else the board on its renderer's clock). A hard-coded 12-frame seam used to be trimmed after every beat, even one
    continuing a stage run, which has none."""
    import beat_clock as _bc
    sp = _bc.spans(out_dir)
    out = []
    for k, (s, e) in enumerate(sp):
        a = max(s, sp[k - 1][1]) if k else s
        out.append((int(round(a * fps)), min(n_frames - 1, max(int(round(a * fps)), int(round(e * fps)) - 1))))
    return out


def shot_rows(out_dir, n_frames, fps):
    """[(label, [frames])] per shot_plan.json shot: its opening, 50 % and 90 % — or None without a shot plan."""
    p = os.path.join(out_dir, "shot_plan.json")
    if not os.path.isfile(p):
        return None
    rows = []
    for sh in json.load(open(p, encoding="utf-8")).get("shots") or []:
        a, b = float(sh["start"]), float(sh["end"])
        ts = (a + min(OPEN, 0.25 * (b - a)), a + 0.5 * (b - a), a + 0.9 * (b - a))
        label = "shot %s  %s" % (sh.get("id", ""), " · ".join(str(sh[k]) for k in ("sequence", "framing") if sh.get(k)))
        rows.append((label + "   ·   opens / 50 / 90 %", [min(n_frames - 1, int(t * fps)) for t in ts]))
    return rows


def default_video(out_dir):
    return os.path.join(out_dir, "final.mp4" if os.path.isfile(os.path.join(out_dir, "shot_plan.json")) else "out.mp4")


def _probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets,r_frame_rate", "-of", "json", video], capture_output=True, text=True)
    st = json.loads(r.stdout)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return int(st["nb_read_packets"]), float(num) / float(den)


def _frame(video, f, fps, w):
    from PIL import Image
    import io
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.4f" % (f / fps), "-i", video, "-frames:v", "1", "-vf",
                        "scale=%d:-2" % w, "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    return Image.open(io.BytesIO(r.stdout)).convert("RGB") if r.stdout else Image.new("RGB", (w, w * 9 // 16))


def _strip(video, frames, fps, w):
    from PIL import Image
    ims = [_frame(video, f, fps, w) for f in frames]
    out = Image.new("RGB", (len(ims) * (w + 4), ims[0].height), "white")
    for i, im in enumerate(ims):
        out.paste(im, (i * (w + 4), 0))
    return out


def build(out_dir, video=None, rows=ROWS):
    from PIL import Image, ImageDraw
    video = video or default_video(out_dir)
    n, fps = _probe(video)
    rows_ = shot_rows(out_dir, n, fps)
    if rows_ is None:
        try:
            slides = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("slides") or []
        except (OSError, ValueError):
            slides = []
        rows_ = []
        for k, (a, b) in enumerate(spans(out_dir, n, fps)):
            shot = (slides[k].get("shot") if k < len(slides) else "") or ""
            rows_.append(("beat %d  %s   ·   30 / 60 / 90 %%" % (k + 1, shot), [int(a + (b - a) * q) for q in POINTS]))
    d = os.path.join(out_dir, "_review")
    os.makedirs(d, exist_ok=True)
    index = {"video": video, "sheets": [], "rows": []}
    cells = []
    for k, (label, fs) in enumerate(rows_):
        cells.append((label, fs, [_frame(video, f, fps, CELL_W) for f in fs]))
        index["rows"].append({"beat": k + 1, "label": label, "seconds": [round(f / fps, 2) for f in fs]})
    for p in range(0, len(cells), rows):
        part = cells[p:p + rows]
        h = part[0][2][0].height
        sheet = Image.new("RGB", (3 * (CELL_W + 4), len(part) * (h + LABEL_H + 4)), "white")
        dr = ImageDraw.Draw(sheet)
        for i, (label, fs, ims) in enumerate(part):
            y = i * (h + LABEL_H + 4)
            # the label sits on its OWN strip above the row: any spot inside a frame hides something (top-left hid a
            # title; bottom-right hid a long caption's last words)
            dr.text((6, y + 4), "%s  (%s s)" % (label, ", ".join("%.1f" % (f / fps) for f in fs)), fill="black")
            for j, im in enumerate(ims):
                sheet.paste(im, (j * (CELL_W + 4), y + LABEL_H))
        path = os.path.join(d, "beats_%02d.jpg" % (p // rows + 1))
        sheet.save(path, quality=84)
        index["sheets"].append(path)
    head = _strip(video, list(range(0, min(n, 24), 2)), fps, 240)
    tail = _strip(video, list(range(max(0, n - 30), n, 3)), fps, 240)
    ends = Image.new("RGB", (max(head.width, tail.width), head.height + tail.height + 8), "white")
    ends.paste(head, (0, 0))
    ends.paste(tail, (0, head.height + 8))
    ends_path = os.path.join(d, "ends.jpg")
    ends.save(ends_path, quality=84)
    index["ends"] = ends_path
    with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    return index


def main(argv):
    from _common import argflag, refuse_unknown
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    refuse_unknown(argv, valued=("video", "rows"))
    out_dir = argv[0]
    video = argflag(argv, "video", None)
    if not os.path.isfile(video or default_video(out_dir)):
        print("[review_sheet] UNMEASURED — no film to sheet")
        return 0
    idx = build(out_dir, video, int(argflag(argv, "rows", ROWS)))
    print("[review_sheet] LOOK at %d beat sheet(s) and the ends before hand-over: %s, %s"
          % (len(idx["sheets"]), ", ".join(idx["sheets"]), idx["ends"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
