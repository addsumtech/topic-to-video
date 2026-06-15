"""storyboard.json -> out.mp4 (+ out.srt). ffmpeg-direct, no moviepy.

Captions are burned in with PIL (a bundled font), composited as an overlay
*after* zoompan so they stay fixed while the slide gently zooms. This avoids
any dependency on an ffmpeg built with libass.
"""
import argparse, os, tempfile
from PIL import Image, ImageDraw, ImageFont
import _common
import storyboard as sb

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "assets", "fonts", "DejaVuSans.ttf")

def _load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def _canvas(meta, vertical):
    if vertical:
        return 1080, 1920
    return meta.get("width", 1920), meta.get("height", 1080)

def _fit_frame(src, dst, W, H):
    """Scale-and-pad a slide image onto a WxH canvas (letterbox)."""
    im = Image.open(src).convert("RGB")
    im.thumbnail((W, H), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), (0, 0, 0))
    bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    bg.save(dst)

def _wrap(d, text, font, max_w):
    """Greedy word-wrap to a max pixel width."""
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if not cur or d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

def _draw_caption(d, text, W, H):
    """Burn a centered caption bar near the bottom (fixed, doesn't zoom)."""
    if not text:
        return
    font = _load_font(int(H * 0.045))
    margin = int(H * 0.06)
    pad = int(H * 0.012)
    lines = _wrap(d, text, font, int(W * 0.9))
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    block_h = line_h * len(lines) + pad * 2
    y0 = H - margin - block_h
    d.rectangle([0, y0, W, y0 + block_h], fill=(0, 0, 0, 140))
    y = y0 + pad
    for ln in lines:
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h

def _overlay(callouts, caption_text, W, H, dst):
    """Draw callouts and the caption onto one transparent PNG (static for v1)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    label_font = _load_font(int(H * 0.028))
    for co in callouts or []:
        x0, y0, x1, y1 = co["box"]
        box = [x0 * W, y0 * H, x1 * W, y1 * H]
        if co.get("style") == "highlight":
            d.rectangle(box, fill=(255, 230, 0, 60), outline=(255, 200, 0, 230), width=4)
        else:  # box / arrow target
            d.rectangle(box, outline=(255, 60, 60, 240), width=5)
        if co.get("label"):
            d.text((box[0] + 6, max(0, box[1] - 30)), co["label"],
                   font=label_font, fill=(255, 255, 255, 255))
    _draw_caption(d, caption_text, W, H)
    layer.save(dst)

def _srt_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

def _captions_for(slide):
    """Use explicit captions, else one caption spanning the slide."""
    caps = slide.get("captions") or []
    if caps:
        return caps
    return [{"start": 0.0, "end": slide["duration"], "text": slide["narration"].strip()}]

def _write_srt(data, path):
    idx = 1; t0 = 0.0
    lines = []
    for s in data["slides"]:
        for c in _captions_for(s):
            lines.append(str(idx))
            lines.append(f"{_srt_time(t0 + c['start'])} --> {_srt_time(t0 + c['end'])}")
            lines.append(c["text"]); lines.append(""); idx += 1
        t0 += s["duration"]
    with open(path, "w") as f:
        f.write("\n".join(lines))

def _render_slide(slide, meta, W, H, workdir, burn_captions):
    i = slide["index"]
    frame = os.path.join(workdir, f"fit_{i:02d}.png")
    _fit_frame(os.path.join(meta["_out"], slide["image"]), frame, W, H)
    fps = meta.get("fps", 30)
    dur = slide["duration"]
    frames = max(1, int(round(dur * fps)))
    z0 = slide["motion"]["from"][2]; z1 = slide["motion"]["to"][2]
    zexpr = f"{z0}+({z1}-{z0})*on/{frames}"
    vf = (f"scale={W}:{H},zoompan=z='{zexpr}':d={frames}:s={W}x{H}:fps={fps}")

    # Build a single overlay PNG (callouts + caption), composited after zoompan.
    caption_text = ""
    if burn_captions:
        caption_text = " ".join(c["text"].strip() for c in _captions_for(slide)).strip()
    ov_png = None
    if slide.get("callouts") or caption_text:
        ov_png = os.path.join(workdir, f"ov_{i:02d}.png")
        _overlay(slide.get("callouts"), caption_text, W, H, ov_png)

    out_clip = os.path.join(workdir, f"clip_{i:02d}.mp4")
    # Inputs are fixed order: 0=frame(loop), 1=audio, 2=overlay(optional).
    parts = [f"[0:v]{vf}[base]"]
    vlabel = "base"
    extra_inputs = []
    if ov_png:
        extra_inputs += ["-i", ov_png]
        parts.append(f"[{vlabel}][2:v]overlay=0:0[ov]"); vlabel = "ov"
    fcomplex = ";".join(parts)
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", frame, "-i",
           os.path.join(meta["_out"], slide["audio"])] + extra_inputs + [
        "-filter_complex", fcomplex, "-map", f"[{vlabel}]", "-map", "1:a",
        "-t", f"{dur}", "-r", str(fps), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", out_clip]
    _common.run(cmd)
    return out_clip

def render(out_dir, sample=None, vertical=False, only=None):
    data = sb.load(os.path.join(out_dir, "storyboard.json"))
    sb.validate(data)
    meta = data["meta"]; meta["_out"] = out_dir
    W, H = _canvas(meta, vertical)
    burn = bool(meta.get("captions", True))

    slides = data["slides"]
    if sample is not None:
        slides = [s for s in slides if s["index"] == sample]
    elif only is not None:
        slides = [s for s in slides if s["index"] == only]

    for s in slides:
        if not s.get("audio") or not s.get("duration"):
            raise sb.StoryboardError(f"slide {s['index']} missing audio/duration; run tts.py first")

    with tempfile.TemporaryDirectory() as wd:
        clips = [_render_slide(s, meta, W, H, wd, burn) for s in slides]
        if sample is not None:
            dst = os.path.join(out_dir, "sample.mp4")
            _common.run(["ffmpeg", "-y", "-i", clips[0], "-c", "copy", dst])
            return dst
        listfile = os.path.join(wd, "list.txt")
        with open(listfile, "w") as f:
            for c in clips:
                f.write(f"file '{c}'\n")
        dst = os.path.join(out_dir, "out.mp4")
        _common.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                     "-c", "copy", dst])
        _write_srt(data, os.path.join(out_dir, "out.srt"))
        return dst

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--vertical", action="store_true")
    a = ap.parse_args()
    res = render(a.out_dir, sample=a.sample, vertical=a.vertical, only=a.only)
    print(f"Rendered -> {res}")

if __name__ == "__main__":
    main()
