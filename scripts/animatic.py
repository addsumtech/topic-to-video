#!/usr/bin/env python3
"""animatic — the film's boards cut to its real voice, before anything is built: rhythm, cuts and what is on screen
under each line, judged for seconds of work instead of a full render.

    python3 scripts/animatic.py <film_dir> [--out design/animatic.mp4] [--fps 12] [--width 1280] [--page film.html]

Reads `shot_plan.json` (shots: id, start, end, technique, hero), `timeline.json` (the voice clock: lines with start,
end, text, clip, trim) and the boards: `design/boards/<shot id>.png|jpg` for any shot (a rough blocking frame or a
sketch), else the hero keyframes `design/keyframes/*.png` in hero order for the `hero: true` shots, else a GREY CARD
drawn from the shot's paragraph in `design/treatment.md` and marked BOARD MISSING — so a shot nobody has pictured is
visible as such. Each frame carries the shot id and time (top left; it is a working cut) and the spoken line as a
caption. The voice: `audio/voice.wav` when the film has one, else every line's clip placed at its start.
`--page film.html`: the BLOCKING cut — every shot without its own board is captured from the film's page itself at
20 / 50 / 85 % of its span (scripts/_filmpage.py) and shown as three steps, so the animatic is the real composition on
the real clock, rough as it is; boards and keyframes still win where they exist.

WHY. A film with three hero keyframes went straight to the full build; its pacing faults (a 1.5 s pull from close to
wide, a scribble standing in for "router", six shots of one framing) were found only after it was built, each fix a
re-render (Grok Bot 2026-11-18). The industry's order is boards -> animatic -> build; the user approves this.
Exit 0 written (prints how many shots lack a board), 2 usage error or missing plan/timeline.
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = "usage: animatic.py <film_dir> [--out design/animatic.mp4] [--fps 12] [--width 1280] [--page film.html]"
STEPS = (0.2, 0.5, 0.85)


def page_boards(d, page, shots, have, td):
    """{shot id: [3 capture paths]} for shots not in `have`, drawn by the film's own page at 20/50/85 % of each."""
    import _filmpage as _fp
    port, srv = _fp.serve(d)
    out = {}
    try:
        p = _fp.FilmPage(port, page)
        try:
            for s in shots:
                if have.get(s["id"]):
                    continue
                a, b = float(s["start"]), float(s["end"])
                out[s["id"]] = []
                for k, u in enumerate(STEPS):
                    path = os.path.join(td, "pg_%s_%d.jpg" % (s["id"], k))
                    p.seek(a + (b - a) * u)
                    p.shot(path, "jpeg", 85)
                    out[s["id"]].append(path)
        finally:
            p.close()
    finally:
        srv.shutdown()
    return out


def treatment_lines(path):
    """{shot id: its paragraph} from design/treatment.md ("**s03 · ... .** what we see ...")."""
    out = {}
    if not os.path.isfile(path):
        return out
    text = open(path, encoding="utf-8").read()
    for m in re.finditer(r"\*\*(s\d+)\b(.*?)\*\*(.*?)(?=\n\s*\n|\n\*\*s\d+\b|\Z)", text, re.S):
        out[m.group(1)] = re.sub(r"\s+", " ", (m.group(2).strip(" ·.") + ". " + m.group(3)).strip())
    return out


def boards(d, shots):
    """{shot id: image path or None} — own board, else the hero keyframes in order, else None."""
    own = {}
    for p in glob.glob(os.path.join(d, "design", "boards", "*")):
        sid = os.path.splitext(os.path.basename(p))[0]
        if p.lower().endswith((".png", ".jpg", ".jpeg")):
            own[sid] = p
    keys = sorted(glob.glob(os.path.join(d, "design", "keyframes", "*.png")))
    heroes = [s["id"] for s in shots if s.get("hero")]
    out = {}
    for s in shots:
        if s["id"] in own:
            out[s["id"]] = own[s["id"]]
        elif s["id"] in heroes and heroes.index(s["id"]) < len(keys):
            out[s["id"]] = keys[heroes.index(s["id"])]
        else:
            out[s["id"]] = None
    return out


def _font(size, bold=False):
    """A face that has CJK glyphs (an animatic's caption may be Chinese): a full system CJK font first, the skill's
    bundled Noto SC subset next, DejaVu last (Latin only). The first version fell to DejaVu and drew Chinese as boxes."""
    from PIL import ImageFont
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
    for p, idx in (("/System/Library/Fonts/Hiragino Sans GB.ttc", 1 if bold else 0),
                   ("/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc", 0),
                   ("/System/Library/Fonts/PingFang.ttc", 0),
                   ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
                   (os.path.join(here, "NotoSansSC-Subset.ttf"), 0),
                   (os.path.join(here, "DejaVuSans.ttf"), 0)):
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size, index=idx)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap(text, font, width):
    """Lines no wider than `width` px in `font`: words break at spaces, CJK at any character (a character-count wrap
    tuned for Latin let a Chinese line run off the frame)."""
    import re as _re
    toks = _re.findall(r"[\u2e80-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]|[^\s\u2e80-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]+|\s+", text or "")
    lines, cur = [], ""
    for t in toks:
        nxt = cur + t
        closing = t in "，。、；：！？）」』”’》〉,.;:!?)"           # never starts a line (it stays on the one before)
        if cur and font.getlength(nxt.rstrip()) > width and not t.isspace() and not closing:
            lines.append(cur.rstrip())
            cur = t.lstrip()
        else:
            cur = nxt
    if cur.strip():
        lines.append(cur.strip())
    return lines


def _card(W, H, shot, para):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (58, 60, 66))
    g = ImageDraw.Draw(im)
    g.rectangle((int(W * 0.04), int(H * 0.06), int(W * 0.96), int(H * 0.78)), outline=(120, 124, 132), width=3)
    g.text((int(W * 0.07), int(H * 0.10)), "BOARD MISSING", fill=(255, 170, 90), font=_font(int(H * 0.04), True))
    g.text((int(W * 0.07), int(H * 0.17)), shot.get("technique") or shot["id"], fill=(240, 240, 244), font=_font(int(H * 0.05), True))
    body = wrap(para or "(no treatment line)", _font(int(H * 0.032)), int(W * 0.86))[:9]
    for i, ln in enumerate(body):
        g.text((int(W * 0.07), int(H * (0.27 + i * 0.05))), ln, fill=(200, 202, 208), font=_font(int(H * 0.032)))
    return im


def _fit(path, W, H):
    from PIL import Image
    src = Image.open(path).convert("RGB")
    k = min(W / src.width, H / src.height)
    src = src.resize((max(1, int(src.width * k)), max(1, int(src.height * k))), Image.LANCZOS)
    im = Image.new("RGB", (W, H), (0, 0, 0))
    im.paste(src, ((W - src.width) // 2, (H - src.height) // 2))
    return im


def _voice(d, lines, total, out):
    va = os.path.join(d, "audio", "voice.wav")
    if os.path.isfile(va):
        return va
    ins, chain, labs = [], [], []
    for k, ln in enumerate(l for l in lines if l.get("clip") and os.path.isfile(os.path.join(d, l["clip"]))):
        a, b = (ln.get("trim") or [0, None])[:2]
        ins += ["-i", os.path.join(d, ln["clip"])]
        trim = "atrim=%.3f%s," % (a, (":%.3f" % b) if b else "")
        chain.append("[%d:a]%sasetpts=PTS-STARTPTS,adelay=%d:all=1[a%d]" % (k, trim, int(ln["start"] * 1000), k))
        labs.append("[a%d]" % k)
    if not labs:
        return None
    chain.append("%samix=inputs=%d:normalize=0,apad=whole_dur=%.3f[out]" % ("".join(labs), len(labs), total))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(chain), "-map", "[out]",
                    "-ar", "48000", "-ac", "1", out], check=True)
    return out


def main(argv):
    _c.refuse_unknown(argv, valued=("out", "fps", "width", "page"), usage=_USAGE)
    vals = {k: _c.argflag(argv, k, None) for k in ("out", "fps", "width", "page")}
    args = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    sp, tp = os.path.join(d, "shot_plan.json"), os.path.join(d, "timeline.json")
    if not (os.path.isfile(sp) and os.path.isfile(tp)):
        print("animatic: needs shot_plan.json and timeline.json in %s" % d, file=sys.stderr)
        return 2
    plan = json.load(open(sp, encoding="utf-8"))
    shots = plan.get("shots") if isinstance(plan, dict) else plan
    tl = json.load(open(tp, encoding="utf-8"))
    lines = tl.get("lines") or []
    total = float(tl.get("duration") or max(float(s["end"]) for s in shots))
    fps = float(vals["fps"] or 12)
    W = int(vals["width"] or 1280)
    H = W * 9 // 16
    SH = (int(H * 0.17) // 2) * 2          # the strip under the picture (even, for yuv420p)
    out = os.path.join(d, vals["out"] or os.path.join("design", "animatic.mp4"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    para = treatment_lines(os.path.join(d, "design", "treatment.md"))
    bd = boards(d, shots)
    from PIL import ImageDraw
    cache = {}
    with tempfile.TemporaryDirectory(prefix="animatic_") as td:
        steps = {}
        if vals["page"]:
            if not os.path.isfile(os.path.join(d, vals["page"])):
                print("animatic: no page at %s" % os.path.join(d, vals["page"]), file=sys.stderr)
                return 2
            import _filmpage as _fp
            try:
                steps = page_boards(d, vals["page"], shots, bd, td)
            except _fp.PageError as e:
                print("animatic: %s" % e, file=sys.stderr)
                return 2
        n = int(round(total * fps))
        for f in range(n):
            t = f / fps
            shot = next((s for s in shots if float(s["start"]) <= t < float(s["end"])), shots[-1] if t >= float(shots[-1]["start"]) else shots[0])
            key = shot["id"]
            if steps.get(shot["id"]):
                a, b = float(shot["start"]), float(shot["end"])
                u = (t - a) / max(1e-6, b - a)
                k = 0 if u < 0.35 else (1 if u < 0.68 else 2)
                key = "%s#%d" % (shot["id"], k)
                if key not in cache:
                    cache[key] = _fit(steps[shot["id"]][k], W, H)
            elif key not in cache:
                cache[key] = _fit(bd[shot["id"]], W, H) if bd[shot["id"]] else _card(W, H, shot, para.get(shot["id"]))
            # the picture whole, untouched; the working labels and the spoken line in a strip BELOW it (a caption
            # over the picture hid the cards and characters at the bottom of the frame)
            from PIL import Image
            im = Image.new("RGB", (W, H + SH), (0, 0, 0))
            im.paste(cache[key], (0, 0))
            g = ImageDraw.Draw(im)
            tag = "%s  %05.2fs  %s" % (shot["id"], t, "HERO" if shot.get("hero") else "")
            g.text((int(W * 0.012), H + int(SH * 0.08)), tag, fill=(255, 220, 120), font=_font(int(H * 0.03), True))
            ln = next((l for l in lines if float(l["start"]) <= t <= float(l["end"])), None)
            if ln:
                cap = wrap(ln["text"], _font(int(H * 0.036)), int(W * 0.97))[:2]
                for i, c in enumerate(cap):
                    g.text((int(W * 0.012), H + int(SH * 0.36) + i * int(H * 0.045)), c, fill=(255, 255, 255),
                           font=_font(int(H * 0.036)))
            im.save(os.path.join(td, "f_%05d.jpg" % f), quality=88)
        voice = _voice(d, lines, total, os.path.join(td, "voice.wav"))
        cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(td, "f_%05d.jpg")]
        if voice:
            cmd += ["-i", voice, "-shortest"]
        cmd += ["-vf", _c.BT709_VF, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", out]
        subprocess.run(cmd, check=True)
    missing = [s["id"] for s in shots if not bd[s["id"]] and not steps.get(s["id"])]
    print("[animatic] %s  %.1f s, %d shots (%d with a board, %d BOARD MISSING%s)%s" % (
        os.path.relpath(out, d), total, len(shots), len(shots) - len(missing), len(missing),
        (": " + ", ".join(missing)) if missing else "", "" if voice else "  — NO VOICE found (audio/voice.wav or line clips)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
