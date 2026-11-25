#!/usr/bin/env python3
"""film_deliver — finish and hand over a director-path film: the final encode (with a grain finish), the subtitles,
a cover image, and the copy to the user's Desktop.

    python3 scripts/film_deliver.py <film_dir> [--encode] [--frames work/frames] [--audio audio/mix.wav]
                                    [--grain 3] [--no-copy]

--encode   <frames>/f_%05d.jpg + the mix -> the plan's video (final.mp4): H.264 High, preset medium (2.5x faster
           than slow and no worse: SSIM 0.992 vs 0.991 on the QR film, 2026-11-18), CRF 17, `aq-mode=3` (bits where a
           dark flat ground needs them), AAC 192k, faststart, and a fine temporal luma GRAIN (`--grain`, 0 = off).
           WHY THE GRAIN: an 8-bit dark gradient encodes as visible steps; the Grok Bot night sky measured CAMBI 8.0
           (visible past 5) on 9 of 26 shots; with grain 3 the worst was 4.1 and the median 0.13, UI text unchanged.
Always:    `<video stem>.share.mp4`, the film small enough to send or host (CRF 23, under 95 MB; `share()`), delivered
           beside the master as "<name> - share.mp4"; `<video stem>.credits.txt`, the credit every sourced picture the
           page shows and its map data are owed (imagefetch.credit_lines, geo.credit_lines), delivered beside it.
Always:    `final.srt` beside the video, from timeline.json (each line chunked by the classic renderer's caption rule,
           every chunk starting on its first word); `out.cover.png`, the film's cover — the final film's first hero shot at its
           settled moment, drawn by film.html with its captions hidden (`data-caption`); then
           scripts/deliver.py copies the film, its .srt and the cover to the Desktop (a re-delivery takes the clean
           name and moves the film's own earlier copy into work/superseded; a file the user made is never touched).
Exit 0 done, 1 a step failed (named), 2 usage error / missing inputs.
"""
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = ("usage: film_deliver.py <film_dir> [--encode] [--frames work/frames] [--audio audio/mix.wav] [--grain 3]"
          " [--no-copy]")


def _ts(t):
    h, m, s = int(t // 3600), int((t % 3600) // 60), t % 60
    return ("%02d:%02d:%06.3f" % (h, m, s)).replace(".", ",")


def srt(timeline):
    """SRT text for a director timeline: each line's captions by the classic chunker, timed on the line's words."""
    import render
    out, n = [], 0
    for ln in timeline.get("lines") or []:
        a, b = float(ln["start"]), float(ln["end"])
        words = [{"w": w["w"], "t": float(w["t"]) - a} for w in ln.get("words") or []]
        caps = render._captions_for({"narration": ln["text"], "duration": max(0.1, b - a)}, words or None)
        for c in caps:
            n += 1
            out += [str(n), "%s --> %s" % (_ts(a + c["start"]), _ts(a + c["end"])), c["text"], ""]
    return "\n".join(out)


def encode(d, frames, audio, video, grain, start=0, count=None):
    """`start` / `count`: a stretch of the frames only (film_qc --frames encodes a builder's shots the way the film is)."""
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-start_number", str(start), "-i", os.path.join(frames, "f_%05d.jpg")]
    if count:
        cmd += ["-frames:v", str(count)]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-vf", _c.BT709_VF + (",noise=c0s=%d:c0f=t+u" % grain if grain > 0 else "")]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-x264-params", "aq-mode=3", "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    # written beside the video and moved into place when complete: a check reading the video while it was being
    # re-encoded read a truncated file ("the video could not be read", 2026-11-18)
    tmp = os.path.join(os.path.dirname(video), ".encoding." + os.path.basename(video))
    cmd += ["-movflags", "+faststart", tmp]
    try:
        subprocess.run(cmd, check=True)
        os.replace(tmp, video)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


CAPTION_SELECTORS = "[data-caption], #cap, #caption, #captions, .caption, .captions, #subtitle, .subtitle"


def _hero_time(d, plan):
    fps = float(plan.get("fps", 30))
    segs = plan.get("segments") or []
    sp = os.path.join(d, "shot_plan.json")
    hero = None
    if os.path.isfile(sp):
        shots = json.load(open(sp, encoding="utf-8"))
        shots = shots.get("shots") if isinstance(shots, dict) else shots
        hero = next((s["id"] for s in shots if s.get("hero")), None)
    seg = next((s for s in segs if s.get("id") == hero), segs[0] if segs else None)
    return (seg["start"] + 0.85 * (seg["end"] - seg["start"])) / fps if seg else 1.0


def cover(d, video, plan, out, page="film.html"):
    """The cover: the FINAL film's first hero shot at its settled moment, drawn by the page with its captions hidden
    (a design keyframe can be out of date by delivery: the Grok Bot cover showed a cast the film had replaced).
    The caption element is found by `data-caption` (or a common id/class) and its hiding confirmed; with no page, or
    no caption element found, it is the video's frame and the return says the cover carries a caption."""
    t = _hero_time(d, plan)
    if os.path.isfile(os.path.join(d, page)):
        import _filmpage as _fp
        port, srv = _fp.serve(d)
        try:
            p = _fp.FilmPage(port, page)
            try:
                p.seek(t)
                hid = p.ev("(() => { const els = [...document.querySelectorAll(%s)]; els.forEach(e => e.style.setProperty('visibility', 'hidden', 'important'));"
                           " return els.length; })()" % json.dumps(CAPTION_SELECTORS))
                p.ev("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))", True)
                if hid:
                    p.shot(out, "png")
                    return "the film's hero shot at %.2fs, captions hidden" % t
            finally:
                p.close()
        finally:
            srv.shutdown()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", video, "-frames:v", "1", out], check=True)
    return "the video's frame at %.2fs — WITH its caption (mark the page's caption element data-caption)" % t


SHARE_CRF = 23
SHARE_CAP_MB = 95      # under GitHub's 100 MB file limit and most chat apps' video limits


def share(video, cap_mb=SHARE_CAP_MB):
    """`<video stem>.share.mp4`: the same film small enough to send or host (CRF 23, AAC 128k, faststart), re-encoded
    to a bitrate under `cap_mb` when CRF 23 is still larger. Kept while it is newer than the film. Returns its path.
    WHY: the MRI film's master (CRF 17 + grain) was 145 MB, over GitHub's 100 MB limit, and was re-encoded by hand for
    the showcase site (23 MB at CRF 23); every delivered film needs that copy."""
    out = os.path.splitext(video)[0] + ".share.mp4"
    if os.path.isfile(out) and os.path.getmtime(out) >= os.path.getmtime(video):
        return out
    tmp = os.path.join(os.path.dirname(out), ".encoding." + os.path.basename(out))
    base = ["ffmpeg", "-v", "error", "-y", "-i", video, "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-vf", _c.BT709_VF, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
    try:
        subprocess.run(base[:8] + ["-crf", str(SHARE_CRF)] + base[8:] + [tmp], check=True)
        if os.path.getsize(tmp) > cap_mb * 1e6:
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                       capture_output=True, text=True).stdout.strip())
            kbps = max(300, int(cap_mb * 8e3 * 0.95 / dur) - 128)
            subprocess.run(base[:8] + ["-b:v", "%dk" % kbps, "-maxrate", "%dk" % kbps, "-bufsize", "%dk" % (2 * kbps)] + base[8:] + [tmp],
                           check=True)
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return out


def main(argv):
    _c.refuse_unknown(argv, valued=("frames", "audio", "grain"), switches=("encode", "no-copy"), usage=_USAGE)
    vals = {k: _c.argflag(argv, k, None) for k in ("frames", "audio", "grain")}
    args = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    pp, tp = os.path.join(d, "_plan.json"), os.path.join(d, "timeline.json")
    if not (os.path.isfile(pp) and os.path.isfile(tp)):
        print("film_deliver: needs _plan.json and timeline.json in %s" % d, file=sys.stderr)
        return 2
    plan = json.load(open(pp, encoding="utf-8"))
    video = os.path.join(d, plan.get("video", "final.mp4"))
    try:
        if "--encode" in argv:
            frames = os.path.join(d, vals["frames"] or os.path.join("work", "frames"))
            audio = os.path.join(d, vals["audio"] or os.path.join("audio", "mix.wav"))
            if not glob.glob(os.path.join(frames, "f_*.jpg")):
                print("film_deliver: no frames in %s (render them with scripts/film_frames.py)" % frames, file=sys.stderr)
                return 2
            encode(d, frames, audio if os.path.isfile(audio) else None, video, int(vals["grain"] or 3))
            print("[film_deliver] encoded %s (grain %s)%s" % (os.path.relpath(video, d), vals["grain"] or 3,
                                                               "" if os.path.isfile(audio) else "  — NO AUDIO found"))
        if not os.path.isfile(video):
            print("film_deliver: no video at %s (pass --encode)" % video, file=sys.stderr)
            return 2
        sh = share(video)
        print("[film_deliver] %s  %.1f MB (to send or host; the master is %.1f MB)"
              % (os.path.relpath(sh, d), os.path.getsize(sh) / 1e6, os.path.getsize(video) / 1e6))
        import geo
        import imagefetch
        pics, maps = imagefetch.credit_lines(d), geo.credit_lines(d)
        if pics or maps:
            cp = os.path.splitext(video)[0] + ".credits.txt"
            open(cp, "w", encoding="utf-8").write("".join("%s\n%s\n" % (h, "\n".join(x)) for h, x in (("Pictures", pics), ("Maps", maps)) if x))
            print("[film_deliver] %s  %d picture and %d map-data credit(s)" % (os.path.relpath(cp, d), len(pics), len(maps)))
        s = srt(json.load(open(tp, encoding="utf-8")))
        sp = os.path.splitext(video)[0] + ".srt"
        open(sp, "w", encoding="utf-8").write(s)
        print("[film_deliver] %s  %d caption(s)" % (os.path.relpath(sp, d), s.count(" --> ")))
        how = cover(d, video, plan, os.path.join(d, "out.cover.png"))
        print("[film_deliver] out.cover.png  (%s)" % how)
        if "--no-copy" not in argv:
            import deliver
            for p in deliver.deliver(d):
                print("[film_deliver] delivered %s" % p)
    except (subprocess.CalledProcessError, OSError) as e:
        print("film_deliver: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
