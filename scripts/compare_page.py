#!/usr/bin/env python3
"""compare_page — old and new beside each other, beat by beat, for the USER to pick (references/craft-standard.md §loop).

    python3 scripts/compare_page.py OUT.html --old=<out_dir> --new=<out_dir> [--new-clip=PATTERN] [--beats=2,5,9]
    python3 scripts/compare_page.py OUT.html --old=<dir> --new=<dir> --old-clip={n}.mp4 --new-clip={n}.mp4 --names=A,B
                                    # a library redesign: one clip per REGISTER on each side, picked by name

WHY (2026-11-12). The redesign that lifted video-shotcraft's library was judged shot by shot by its user on a page
like this — original / first pass / redesign / drop — not by a metric and not by a critic: of 216 shots, 92 took the
redesign, 50 the first pass, 8 the original, 66 were dropped. A film's redesign is judged the same way here.

INPUTS. `--old` / `--new` are film folders (their delivered out.mp4 and .render_record.json give each beat's span), or
for the new side, `--new-clip=_s{n}.r2.mp4` names one clip per beat inside the new folder (a sample render IS the beat).
Each beat is shown at 30 / 60 / 90 % of its own span (the seam excluded), as review_sheet samples it.
OUTPUT. OUT.html plus a folder of frames beside it. Each beat has a pick (old / new / neither); the page writes the picks
as one line to copy back ("2:new 5:new 9:old"). It is a local file: no network, nothing sent anywhere.
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

POINTS = (0.3, 0.6, 0.9)
SEAM = 12
W = 520


def spans(film_dir):
    rec = json.load(open(os.path.join(film_dir, ".render_record.json"), encoding="utf-8"))
    segs = [(int(a), int(b)) for a, b, *_ in rec["segments"]]
    return [(a + (SEAM if k else 0), b) for k, (a, b) in enumerate(segs)]


def _frames(video, a, b, fps, out_prefix):
    import review_sheet as rs
    paths = []
    for q in POINTS:
        f = int(a + (b - a) * q)
        p = "%s_%02d.jpg" % (out_prefix, int(q * 100))
        rs._frame(video, f, fps, W).save(p, quality=86)
        paths.append(p)
    return paths


def _probe(video):
    import review_sheet as rs
    return rs._probe(video)


def side(film_dir, beat, clip_pattern=None):
    """(video, a, b, fps) for one beat of a film folder, or for a per-beat clip."""
    if clip_pattern:
        v = os.path.join(film_dir, clip_pattern.format(n=beat))
        if not os.path.isfile(v):
            return None
        n, fps = _probe(v)
        return v, SEAM, max(SEAM + 1, n - 1), fps
    v = os.path.join(film_dir, "out.mp4")
    sp = spans(film_dir)
    if not (1 <= beat <= len(sp)) or not os.path.isfile(v):
        return None
    n, fps = _probe(v)
    a, b = sp[beat - 1]
    return v, a, min(b, n - 1), fps


def build(out_html, old_dir, new_dir, beats=None, new_clip=None, old_clip=None):
    img_dir = os.path.splitext(out_html)[0] + "_frames"
    os.makedirs(img_dir, exist_ok=True)
    if beats is None:
        beats = list(range(1, len(spans(old_dir)) + 1))
    try:
        slides = json.load(open(os.path.join(new_dir, "storyboard.json"), encoding="utf-8")).get("slides") or []
    except (OSError, ValueError):
        slides = []
    rows = []
    for n in beats:
        cells = {}
        for tag, d, clip in (("old", old_dir, old_clip), ("new", new_dir, new_clip)):
            s = side(d, n, clip)
            cells[tag] = _frames(s[0], s[1], s[2], s[3], os.path.join(img_dir, "b%s_%s" % (n if not isinstance(n, int) else "%02d" % n, tag))) if s else []
        if not cells["old"] and not cells["new"]:
            continue
        sl = slides[n - 1] if isinstance(n, int) and 0 < n <= len(slides) else {"shot": "" if isinstance(n, int) else str(n)}
        rows.append({"beat": n, "line": sl.get("narration") or sl.get("caption") or "", "shot": sl.get("shot") or "",
                     "old": [os.path.relpath(p, os.path.dirname(out_html)) for p in cells["old"]],
                     "new": [os.path.relpath(p, os.path.dirname(out_html)) for p in cells["new"]]})
    with open(out_html, "w", encoding="utf-8") as fh:
        fh.write(_page(rows))
    return rows


def _page(rows):
    def strip(paths, label):
        if not paths:
            return '<div class="none">%s: not rendered</div>' % label
        return '<div class="strip"><b>%s</b>%s</div>' % (label, "".join('<img src="%s" alt="%s">' % (html.escape(p), label) for p in paths))
    body = []
    for r in rows:
        n = r["beat"]
        key = html.escape(str(n))
        picks = "".join('<label><input type="radio" name="b%s" value="%s"> %s</label>' % (key, v, v) for v in ("old", "new", "neither"))
        head = ("Beat %d" % n) if isinstance(n, int) else key
        body.append('<section><h2>%s <span>%s</span></h2><p class="line">%s</p>%s%s<div class="pick">%s</div></section>'
                    % (head, html.escape(r["shot"] if isinstance(n, int) else ""), html.escape(r["line"]), strip(r["old"], "old"),
                       strip(r["new"], "new"), picks))
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Beat Compare</title><style>
:root{--bg:#f5f4f0;--ink:#1a1a18;--ink2:#66645e;--line:#dddad2;--acc:#0a8f74}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--ink:#ecebe6;--ink2:#a19f98;--line:#33322e;--acc:#3fd3ae}}
body{background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,"PingFang SC",sans-serif;margin:0}
main{max-width:1640px;margin:0 auto;padding:28px 16px 120px}section{border-top:1px solid var(--line);padding:18px 0}
h2{margin:0;font-size:19px}h2 span{color:var(--ink2);font-weight:500;font-size:14px;margin-left:8px}.line{color:var(--ink2);margin:4px 0 10px}
.strip{display:flex;gap:6px;align-items:flex-start;margin:6px 0;overflow-x:auto}.strip b{width:44px;flex:none;padding-top:6px}
.strip img{width:min(31%%,520px);border-radius:4px;border:1px solid var(--line)}.pick{display:flex;gap:18px;margin-top:8px}
.none{color:var(--ink2);margin:6px 0}#out{position:fixed;left:0;right:0;bottom:0;background:var(--bg);border-top:1px solid var(--line);
padding:10px 16px;display:flex;gap:10px;align-items:center}#out code{flex:1;overflow-x:auto;white-space:nowrap}
button{background:var(--acc);color:#fff;border:0;border-radius:6px;padding:7px 14px;font:inherit;cursor:pointer}
</style></head><body><main><h1>Beat compare</h1><p>Pick per beat; the line at the bottom is what to send back.</p>%s</main>
<div id="out"><code id="picks">(no picks yet)</code><button id="copy">Copy</button></div>
<script>
const out=document.getElementById('picks');
function sync(){const v=[...document.querySelectorAll('input:checked')].map(i=>i.name.slice(1)+':'+i.value);out.textContent=v.length?v.join(' '):'(no picks yet)';}
document.addEventListener('change',sync);
document.getElementById('copy').onclick=()=>{try{navigator.clipboard.writeText(out.textContent)}catch(e){}};
</script></body></html>""" % "".join(body)


def main(argv):
    from _common import argflag, refuse_unknown
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 0
    refuse_unknown(argv, valued=("old", "new", "new-clip", "old-clip", "beats", "names"))
    out = os.path.abspath(argv[0])
    old, new = argflag(argv, "old", None), argflag(argv, "new", None)
    if not old or not new:
        print("[compare_page] needs --old=<out_dir> and --new=<out_dir>")
        return 2
    b, names = argflag(argv, "beats", None), argflag(argv, "names", None)
    beats = [x for x in names.split(",") if x] if names else ([int(x) for x in b.split(",")] if b else None)
    rows = build(out, os.path.abspath(old), os.path.abspath(new), beats, argflag(argv, "new-clip", None), argflag(argv, "old-clip", None))
    print("[compare_page] %d beat(s) side by side: %s" % (len(rows), out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
