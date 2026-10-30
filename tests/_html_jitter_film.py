"""A small HTML-tier film built from scratch, for the pixel jitter gate (scripts/jitter_qa.py -> jitter_html.py).

Every scene is a known case: a page whose own @keyframes crawls a line of type under a plain translate (Chrome snaps
the baseline to whole pixels: the staircase), the same crawl carrying base.css's baseline unlock (glides), an image
slide whose type rides a Ken Burns move, and a still page. Built at any canvas (meta.width/height, or aspect 9:16),
voiced with silence, rendered by the real scripts/render.py."""
import json
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_CSS = os.path.join(_ROOT, "assets", "html", "base.css")
SEEK_JS = os.path.join(_ROOT, "assets", "html", "seek.js")
UNLOCK = "matrix(1,.0009765625,0,1,0,0)"
RLOCK = "/Users/donghanglyu/code_project/film_work/tools/rlock.py"

# a 40 px crawl over the scene: ~0.44 px a frame at 3 s — slow enough that a snapped baseline holds, then jumps
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{base}">
<style>
  html,body{{width:{w}px;height:{h}px;margin:0;background:{bg};overflow:hidden}}
  .stage{{width:{w}px;height:{h}px;position:relative}}
  #crawl{{position:absolute;left:{x}px;top:{y}px;font:700 {px}px/1.2 Arial,"PingFang SC",sans-serif;color:{ink};
          white-space:nowrap;animation:crawl 1s linear forwards;animation-play-state:paused}}
  @keyframes crawl{{from{{transform:translateY(0){unlock}}}to{{transform:translateY({travel}px){unlock}}}}}
</style></head>
<body>
<div class="stage"><div id="crawl" data-ambient>{text}</div></div>
<script src="file://{seek}"></script>
</body></html>"""


def page(path, W, H, unlocked, text="Spark 5h  92%  14:32  Session", travel=40, still=False, ink="#f2f3f5",
         bg="#111", px=None):
    px = px or max(24, round(min(W, H) * 0.05))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PAGE.format(base=BASE_CSS, seek=SEEK_JS, w=W, h=H, x=round(W * 0.12), y=round(H * 0.3), px=px,
                             ink=ink, bg=bg, text=text, travel=0 if still else travel,
                             unlock=(" " + UNLOCK) if unlocked else ""))


def silence(path, seconds):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t",
                    "%.3f" % seconds, path], check=True)


def slide_image(path, W, H, text="Ken Burns 42 — the type rides the move"):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), (20, 22, 30))
    d = ImageDraw.Draw(im)
    f = None
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            f = ImageFont.truetype(p, max(24, round(min(W, H) * 0.045)))
            break
    for i in range(4):
        d.text((round(W * 0.1), round(H * (0.2 + 0.15 * i))), "%s %d" % (text, i), fill=(236, 238, 242), font=f)
    im.save(path)


def build(out_dir, scenes, W=1920, H=1080, aspect=None, seconds=3.0, reduced_motion=False, captions=False,
          transition="dip"):
    """`scenes`: list of 'snapped' | 'smooth' | 'still' | 'kenburns' | 'cjk-smooth' | 'cjk-snapped' | 'dark-smooth'
    | 'dark-snapped'. Returns the out_dir."""
    os.makedirs(os.path.join(out_dir, "pages"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "audio"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "media"), exist_ok=True)
    if aspect == "9:16":
        W, H = 1080, 1920
    slides = []
    for i, kind in enumerate(scenes, 1):
        wav = os.path.join(out_dir, "audio", "%02d.wav" % i)
        silence(wav, seconds)
        s = {"index": i, "narration": "Scene %d." % i, "duration": seconds, "audio": "audio/%02d.wav" % i,
             "transition": transition}
        if kind == "title":
            s.update(type="title", props={"title": "Settled type 42", "subtitle": "a programmatic scene, judged still"})
        elif kind == "kenburns":
            slide_image(os.path.join(out_dir, "media", "kb%02d.png" % i), W, H)
            s.update(type="slide", image="media/kb%02d.png" % i,
                     motion={"type": "kenburns", "from": [0.3, 0.4, 1.0], "to": [0.6, 0.5, 1.12]})
        else:
            cjk = kind.startswith("cjk")
            dark = kind.startswith("dark")
            page(os.path.join(out_dir, "pages", "p%02d.html" % i), W, H, unlocked=kind.endswith("smooth"),
                 still=(kind == "still"), text="当前会话 92% · 每周限制 79%" if cjk else "Spark 5h  92%  14:32  Session",
                 ink="#2c2f36" if dark else "#f2f3f5", bg="#15171c" if dark else "#111")
            s.update(type="html", props={"html": "pages/p%02d.html" % i})
        slides.append(s)
    meta = {"renderer": "local", "language": "en", "fps": 30, "captions": captions, "transition": transition,
            "reduced_motion": reduced_motion}
    if aspect == "9:16":
        meta["aspect"] = "9:16"
    else:
        meta.update(width=W, height=H)
    with open(os.path.join(out_dir, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "slides": slides}, fh, ensure_ascii=False, indent=1)
    return out_dir


def render(out_dir):
    """scripts/render.py on the film, under the machine-wide render lock."""
    cmd = [sys.executable, os.path.join(_ROOT, "scripts", "render.py"), out_dir]
    if os.path.exists(RLOCK) and not os.environ.get("RLOCK_HELD"):
        cmd = [sys.executable, RLOCK, "--"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=_ROOT)
    if r.returncode != 0:
        raise RuntimeError("render failed: %s" % ((r.stdout or "") + (r.stderr or ""))[-1500:])
    return os.path.join(out_dir, "out.mp4")
