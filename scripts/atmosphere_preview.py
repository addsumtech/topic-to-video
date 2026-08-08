"""ATMOSPHERE CONTEST preview — render ONE representative frame of each candidate WORLD so the user picks
from PIXELS, not names (the cinematic analog of the HTML register-contest snapshot).

`route(topic)` gives the best ~3 atmospheres; this renders the SAME canonical scene (a 3D `bars` chart —
which reveals each world's MATERIAL + POST + colour under identical content, so it is a pure world-to-world
comparison) once per candidate, then montages the frames into a labelled contact sheet
`<out_dir>/atmosphere_contest.png`. The director shows that to the user, who picks `meta.atmosphere`.

Rendering reuses the real pipeline per candidate (tts → theme → render_remotion --sample), so the preview is
exactly what the final film's substrate looks like. Deterministic content; the montage is PIL.
"""
import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.dirname(_HERE)
_FONTS = os.path.join(_SKILL, "assets", "fonts")
sys.path.insert(0, _HERE)
import atmospheres as _atmo  # noqa: E402


def _canonical_board(atmosphere):
    """A single cinematic3d `bars` scene under the given world — the universal reveal (material + post +
    colour show for every atmosphere on the same content). Short, one narration line for the sample render."""
    return {
        "meta": {"renderer": "remotion", "aspect": "16:9", "fps": 30, "language": "en",
                 "image_source": "none", "audacity": "conservative", "film_look": True,
                 "atmosphere": atmosphere, "title": "atmosphere preview"},
        "slides": [{
            "index": 1, "type": "cinematic3d", "archetype": "data-materializes",
            # a few seconds so the bars grow in + the camera moves + the post settles before we grab a frame.
            "narration": "This is the world your film would be rendered in, shown on the same data.",
            "planes": [{"kind": "bars", "data": [4, 7, 5, 9, 6], "position": [0, 0, 0]}],
            "camera3d": [{"at": 0.0, "yaw": -0.5, "radius": 9, "height": 3.4},
                         {"at": 1.0, "yaw": 0.4, "radius": 8.2, "height": 2.8}],
        }],
    }


def _run(cmd, **kw):
    return subprocess.run(cmd, cwd=_SKILL, capture_output=True, text=True, **kw)


def _render_one(key, work_dir, accent, bg):
    """tts → theme → render sample → extract a frame; return the frame path or None (best-effort per world)."""
    os.makedirs(work_dir, exist_ok=True)
    json.dump(_canonical_board(key), open(os.path.join(work_dir, "storyboard.json"), "w"), indent=2)
    if _run([sys.executable, "scripts/tts.py", work_dir]).returncode != 0:
        return None
    _run([sys.executable, "scripts/theme.py", work_dir, "--mode", "dark", "--accent", accent, "--bg", bg])
    r = _run([sys.executable, "scripts/render_remotion.py", work_dir, "--sample", "1", "--no-plan"])
    mp4 = os.path.join(work_dir, "sample.mp4")
    if r.returncode != 0 or not os.path.isfile(mp4):
        return None
    # seek to ~68% of the MEASURED clip (tts rewrote the storyboard with the real duration) so the frame lands
    # after the bars have grown + the camera has moved — NOT past the end (a short clip yielded no frame).
    dur = 3.0
    try:
        _b = json.load(open(os.path.join(work_dir, "storyboard.json")))
        dur = float(_b["slides"][0].get("duration") or 3.0)
    except Exception:
        pass
    frame = os.path.join(work_dir, "frame.png")
    ff = _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.2f" % max(0.1, dur * 0.68), "-i", mp4,
               "-frames:v", "1", frame])
    return frame if (ff.returncode == 0 and os.path.isfile(frame)) else None


def _montage(cards, out_png):
    """Compose the candidate frames side by side with a name + pitch caption under each. `cards` is a list of
    (key, name, pitch, frame_path_or_None). A world whose render failed shows a placeholder tile (never a
    blank sheet). Returns out_png."""
    from PIL import Image, ImageDraw, ImageFont
    n = len(cards)
    tw, th = 640, 360                       # per-tile image size
    cap = 96                                # caption band height
    pad, gap = 28, 20
    W = pad * 2 + n * tw + (n - 1) * gap
    H = pad * 2 + th + cap + 40
    sheet = Image.new("RGB", (W, H), (14, 16, 20))
    d = ImageDraw.Draw(sheet)
    try:
        f_title = ImageFont.truetype(os.path.join(_FONTS, "SpaceGrotesk-VF.ttf"), 30)
        f_body = ImageFont.truetype(os.path.join(_FONTS, "SpaceGrotesk-VF.ttf"), 20)
        f_head = ImageFont.truetype(os.path.join(_FONTS, "SpaceGrotesk-VF.ttf"), 26)
    except Exception:
        f_title = f_body = f_head = ImageFont.load_default()
    d.text((pad, 18), "Pick an atmosphere (the film's WORLD):", font=f_head, fill=(240, 243, 248))
    for i, (key, name, pitch, frame) in enumerate(cards):
        x = pad + i * (tw + gap)
        y = pad + 34
        if frame and os.path.isfile(frame):
            im = Image.open(frame).convert("RGB").resize((tw, th))
            sheet.paste(im, (x, y))
        else:
            d.rectangle([x, y, x + tw, y + th], fill=(30, 32, 38))
            d.text((x + 20, y + th // 2 - 12), "(render unavailable)", font=f_body, fill=(150, 155, 162))
        d.rectangle([x, y, x + tw, y + th], outline=(60, 66, 74), width=2)
        cy = y + th + 12
        d.text((x + 4, cy), "%d. %s" % (i + 1, name), font=f_title, fill=(240, 243, 248))
        # wrap the pitch to the tile width
        words, line, ly = str(pitch).split(), "", cy + 40
        for w in words:
            t = (line + " " + w).strip()
            if d.textlength(t, font=f_body) > tw - 8 and line:
                d.text((x + 4, ly), line, font=f_body, fill=(150, 160, 172)); line = w; ly += 24
            else:
                line = t
        if line:
            d.text((x + 4, ly), line, font=f_body, fill=(150, 160, 172))
        d.text((x + 4, y + th - 30), "key: %s" % key, font=f_body, fill=(120, 200, 160))
    sheet.save(out_png)
    return out_png


def preview(out_dir, topic=None, candidates=None, accent="#5b8cff", bg="#0b0e14"):
    """Render a contact sheet of the best ~3 candidate worlds for `topic` (or an explicit `candidates` list).
    Returns {'candidates': [keys], 'preview': <rel png or None>}. Best-effort: a world that fails to render
    still appears as a placeholder tile so the sheet is always produced."""
    cands = [str(c).lower() for c in (candidates or _atmo.route(topic, 3))]
    cards, base = [], os.path.join(out_dir, ".atmo_preview")
    for key in cands:
        a = _atmo.ATMOSPHERES.get(key, {})
        frame = _render_one(key, os.path.join(base, key), accent, bg)
        cards.append((key, a.get("name", key), a.get("pitch", ""), frame))
    out_png = os.path.join(out_dir, "atmosphere_contest.png")
    try:
        _montage(cards, out_png)
        rel = os.path.relpath(out_png, out_dir)
    except Exception as e:
        print("[atmosphere_preview] montage failed: %s" % e)
        rel = None
    return {"candidates": cands, "preview": rel}


def main():
    ap = argparse.ArgumentParser(description="Render an atmosphere-contest contact sheet (pick a world from pixels).")
    ap.add_argument("out_dir")
    ap.add_argument("--topic", default=None, help="free-text topic → the best ~3 worlds are routed + rendered")
    ap.add_argument("--candidates", default=None, help="comma-separated atmosphere keys (overrides --topic)")
    ap.add_argument("--accent", default="#5b8cff")
    ap.add_argument("--bg", default="#0b0e14")
    a = ap.parse_args()
    cands = a.candidates.split(",") if a.candidates else None
    res = preview(a.out_dir, topic=a.topic, candidates=cands, accent=a.accent, bg=a.bg)
    print("[atmosphere_preview] candidates=%s → %s" % (res["candidates"], res["preview"]))


if __name__ == "__main__":
    main()
