"""storyboard.json -> out.mp4 (+ out.srt). ffmpeg-direct, no moviepy."""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw
import _common
import storyboard as sb

def _have_ass_filter():
    """Return True if ffmpeg was compiled with libass (ass/subtitles filter)."""
    try:
        import re
        out = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True).stdout
        # Match only lines where the filter name itself is 'ass' or 'subtitles'
        return bool(re.search(r'^\s+[A-Z.]+\s+(?:ass|subtitles)\s+', out, re.MULTILINE))
    except Exception:
        return False

_ASS_AVAILABLE = _have_ass_filter()

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

def _callout_overlay(callouts, W, H, dst):
    """Draw all callouts for a slide onto one transparent PNG (static for v1)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for co in callouts:
        x0, y0, x1, y1 = co["box"]
        box = [x0 * W, y0 * H, x1 * W, y1 * H]
        if co.get("style") == "highlight":
            d.rectangle(box, fill=(255, 230, 0, 60), outline=(255, 200, 0, 230), width=4)
        else:  # box / arrow target
            d.rectangle(box, outline=(255, 60, 60, 240), width=5)
        if co.get("label"):
            d.text((box[0] + 6, max(0, box[1] - 22)), co["label"], fill=(255, 255, 255, 255))
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

def _ass_for_slide(slide, W, H, path):
    """Minimal ASS so captions burn deterministically with a known font size."""
    fs = int(H * 0.045)
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,BackColour,"
        "Bold,Alignment,MarginV\nStyle: Cap,Arial,%d,&H00FFFFFF,&H80000000,1,2,%d\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Text\n"
    ) % (W, H, fs, int(H * 0.06))
    def ass_t(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
        return f"{h:d}:{m:02d}:{s:05.2f}"
    body = ""
    for c in _captions_for(slide):
        txt = c["text"].replace("\n", " ")
        body += f"Dialogue: 0,{ass_t(c['start'])},{ass_t(c['end'])},Cap,{txt}\n"
    with open(path, "w") as f:
        f.write(header + body)

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

    co_png = None
    if slide.get("callouts"):
        co_png = os.path.join(workdir, f"co_{i:02d}.png")
        _callout_overlay(slide["callouts"], W, H, co_png)

    ass = None
    if burn_captions and _ASS_AVAILABLE:
        ass = os.path.join(workdir, f"cap_{i:02d}.ass")
        _ass_for_slide(slide, W, H, ass)

    out_clip = os.path.join(workdir, f"clip_{i:02d}.mp4")
    # Inputs are fixed order: 0=frame(loop), 1=audio, 2=overlay(optional).
    parts = [f"[0:v]{vf}[base]"]
    vlabel = "base"
    extra_inputs = []
    if co_png:
        extra_inputs += ["-i", co_png]
        parts.append(f"[{vlabel}][2:v]overlay=0:0[ov]"); vlabel = "ov"
    if ass:
        parts.append(f"[{vlabel}]ass={ass}[vc]"); vlabel = "vc"
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
