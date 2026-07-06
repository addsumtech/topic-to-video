#!/usr/bin/env python3
"""C9 — cheap pre-render KEYFRAME QA for the HTML tier.

Screenshots every `type:"html"` page at several `?p=` values (seek.js freezes the reveals at
each), montages a per-scene contact sheet + a master grid under `<out_dir>/_keyframes/`, and
flags the failures that silently corrupt content clarity — a BLANK page (a reveal that never
fired / a broken page) and CONTENT OVERFLOWING the video canvas (1920×1080, or 1080×1920 when
`meta.aspect` is 9:16) — while they are still one-edit fixes, BEFORE the multi-minute full render.

Overflow is measured from the DOM (max amount any `.stage`/`.split` descendant's box exceeds the
canvas), so a legitimate full-bleed background (`.bg-photo`/`.bg-soft`, which lives OUTSIDE `.stage`)
never false-positives. Needs Chrome DevTools Protocol; without it, falls back to screenshots + a
pixel blank-check only (no overflow measurement).

Usage:  python scripts/keyframe_qa.py <out_dir> [--p N] [--json]
Exit 0 when clean; non-zero if any page is BLANK or OVERFLOWS (those block). The centered-
paragraph check is advisory-only and never blocks. The contact sheets are the primary artifact —
open `_keyframes/all.png` to eyeball tofu / off-theme / mistimed reveals.
"""
import argparse, base64, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import scenes  # reuse the Chrome bin resolver + per-shot screenshot fallback

DEFAULT_PS = [0.0, 0.25, 0.5, 0.75, 1.0]
OVERFLOW_TOL = 6   # px a content box may exceed the canvas before it's flagged

# DOM probe (page frozen at p=1). Returns: `worst` = max px any content box (under .stage/.split,
# NOT full-bleed backdrops) exceeds the canvas; `textlen` = visible text length (blank detection);
# `centered` = count of CENTERED running paragraphs (advisory — body text should be left-aligned to
# scan; excludes display/diagram classes that are centered by design).
_CENTER_EXCL = (".flow,.step,.hubspoke,.hs-spoke,.hs-hub,.timeline,.tl-node,.quadrant,.cell,"
                ".scorecard,.tile,.title,.pullquote,.kicker,.stat,.block")
_OVERFLOW_JS = (
    "(function(){var W=window.innerWidth,H=window.innerHeight,worst=0,ct=1e9,cb=-1e9;"
    "var n=document.querySelectorAll('.stage *,.split *');"
    "for(var i=0;i<n.length;i++){var r=n[i].getBoundingClientRect();"
    "if(r.width<1||r.height<1)continue;"
    "var o=Math.max(r.right-W,r.bottom-H,-r.left,-r.top);if(o>worst)worst=o;"
    "var cs=getComputedStyle(n[i]);if(cs.opacity!=='0'&&cs.display!=='none'){"
    "if(r.top<ct)ct=r.top;if(r.bottom>cb)cb=r.bottom;}}"
    "var t=(document.body.innerText||'').replace(/\\s+/g,'').length;"
    "var EXCL='" + _CENTER_EXCL + "',centered=0,para=document.querySelectorAll('.sub,.note,.lead,p');"
    "for(var j=0;j<para.length;j++){var e=para[j],cs=getComputedStyle(e);"
    "if(cs.textAlign!=='center')continue;if(e.closest&&e.closest(EXCL))continue;"
    "var fs=parseFloat(cs.fontSize)||0,lh=cs.lineHeight;"
    "lh=(lh==='normal'||!lh)?1.4*fs:parseFloat(lh);if(lh<1)continue;"
    "var lines=Math.round(e.scrollHeight/lh),w=e.getBoundingClientRect().width;"
    "if(lines>=3&&w>=600)centered++;}"
    "var bleed=!!document.querySelector('.bg-photo,.bg-soft');"
    "return JSON.stringify({worst:Math.round(worst),textlen:t,centered:centered,"
    "ctop:Math.round(ct),cbot:Math.round(cb),bleed:bleed});})()")


def _is_blank(img):
    lo, hi = img.convert("L").getextrema()
    return (hi - lo) < 12


def _sheet(imgs, path, cols=None, tw=560, th=None):
    cols = cols or len(imgs)
    if th is None:                       # aspect-correct thumbs (9:16 shots stay tall)
        w0, h0 = imgs[0].size
        th = max(1, int(tw * h0 / w0))
    rows = (len(imgs) + cols - 1) // cols
    sh = Image.new("RGB", (tw * cols, th * rows), "#cccccc")
    for i, im in enumerate(imgs):
        sh.paste(im.convert("RGB").resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    sh.save(path)


def _open_cdp(meta, W, H):
    """A CDP Chrome, or None if it can't launch (then we fall back to per-shot screenshots)."""
    try:
        import _cdp
        return _cdp.Chrome(scenes._chrome_bin(meta), W, H)
    except Exception:
        return None


def _dom_probe(chrome):
    r = chrome._cmd("Runtime.evaluate",
                    {"expression": _OVERFLOW_JS, "returnByValue": True}, chrome.sid)
    return json.loads(r["result"]["result"]["value"])


def run(out_dir, ps=DEFAULT_PS, as_json=False):
    data = json.load(open(os.path.join(out_dir, "storyboard.json")))
    meta = data["meta"]; meta["_out"] = out_dir
    W, H = (1080, 1920) if meta.get("aspect") == "9:16" else (1920, 1080)
    kf = os.path.join(out_dir, "_keyframes"); os.makedirs(kf, exist_ok=True)
    html = [s for s in data.get("slides", []) if s.get("type") == "html"]
    if not html:
        print("[keyframe_qa] no html scenes — nothing to check"); return 0

    chrome = _open_cdp(meta, W, H)
    report, last_frames, errors, warns = [], [], 0, 0
    try:
        for s in html:
            idx = s.get("index")
            page = (s.get("props") or {}).get("html")
            if not page:
                continue
            url = "file://" + os.path.abspath(os.path.join(out_dir, page))
            frames, ok = [], True
            for p in ps:
                fp = os.path.join(kf, f"scene_{idx:02d}_p{int(p*100):03d}.png")
                try:
                    if chrome:
                        chrome.shot(url + f"?p={p}", fp)          # CDP: (url, out_path)
                    else:
                        scenes._chrome_shot(url + f"?p={p}", fp, W, H, meta)
                    frames.append(Image.open(fp))
                except Exception as e:
                    report.append({"scene": idx, "status": "ERROR", "issues": [f"render failed: {e}"]})
                    errors += 1; ok = False; break
            if not ok or not frames:
                continue
            _sheet(frames, os.path.join(kf, f"scene_{idx:02d}.png"))
            final = frames[-1]; last_frames.append(final)
            issues, advisories = [], []       # issues block the gate; advisories are non-blocking
            if chrome:
                try:
                    info = _dom_probe(chrome)   # page is still at p=1 (last shot) — measure it
                    if info.get("textlen", 0) < 2:
                        issues.append("BLANK at p=1 (reveal never fired / broken page)")
                    if info.get("worst", 0) > OVERFLOW_TOL:
                        issues.append(f"content overflows the safe canvas by {info['worst']}px — "
                                      "shorten the text or split the beat")
                    if info.get("centered", 0) > 0:
                        advisories.append(f"{info['centered']} centered running paragraph(s) — "
                                          "left-align body text for scanning (studios do)")
                    # 9:16 fill (html-pages.md "fill the column"): content should span >=~70% of
                    # the zone above the caption band (y160-1600). Advisory only; a full-bleed
                    # .bg-photo hero provides visual fill outside .stage, so heroes never warn.
                    if meta.get("aspect") == "9:16" and info.get("cbot", -1) > info.get("ctop", 0):
                        fill = (info["cbot"] - info["ctop"]) / (1600 - 160)
                        rep_fill = round(100 * min(1.0, fill))
                        if fill < 0.60 and not info.get("bleed"):
                            advisories.append(f"fills only {rep_fill}% of the 9:16 zone — scale type "
                                              "up / distribute down / add a lower-zone visual "
                                              "(html-pages '9:16 vertical pages')")
                except Exception:
                    if _is_blank(final):
                        issues.append("BLANK at p=1 (reveal never fired / broken page)")
            elif _is_blank(final):
                issues.append("BLANK at p=1 (reveal never fired / broken page)")
            if issues:
                errors += 1
            if advisories:
                warns += 1
            report.append({"scene": idx, "issues": issues, "advisories": advisories,
                           "status": "FAIL" if issues else ("WARN" if advisories else "ok")})
    finally:
        if chrome:
            chrome.close()

    if last_frames:
        _sheet(last_frames, os.path.join(kf, "all.png"), cols=min(4, len(last_frames)))

    if as_json:
        print(json.dumps({"errors": errors, "warns": warns, "report": report, "cdp": bool(chrome)}, indent=2))
    else:
        for r in report:
            mark = {"FAIL": "✗", "WARN": "!"}.get(r["status"], "✓")
            notes = (r.get("issues") or []) + (r.get("advisories") or [])
            extra = ("  " + "; ".join(notes)) if notes else ""
            print(f"  {mark} scene {r['scene']:02d} [{r['status']}]{extra}")
        mode = "DOM+shots" if chrome else "shots-only (no CDP → overflow/centered unchecked)"
        print(f"[keyframe_qa] {'OK' if errors == 0 else 'ISSUES'}  {len(report)} html page(s), "
              f"{errors} issue(s), {warns} advisory(ies) [{mode}]; sheets -> {kf}/  "
              f"(open all.png to eyeball tofu/theme/reveals)")
    return 1 if errors else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--p", type=int, default=5, help="number of evenly-spaced p-values (default 5)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    n = max(2, a.p)
    ps = [round(i / (n - 1), 3) for i in range(n)]
    sys.exit(run(a.out_dir, ps=ps, as_json=a.json))
