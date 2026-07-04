#!/usr/bin/env python3
"""C9 — cheap pre-render KEYFRAME QA for the HTML tier.

Screenshots every `type:"html"` page at several `?p=` values (seek.js freezes the reveals at
each), montages a per-scene contact sheet + a master grid under `<out_dir>/_keyframes/`, and
flags the failures that silently corrupt content clarity — a BLANK page (a reveal that never
fired / a broken page) and CONTENT OVERFLOWING the 1920×1080 safe canvas — while they are still
one-edit fixes, BEFORE the multi-minute full render.

Overflow is measured from the DOM (max amount any `.stage`/`.split` descendant's box exceeds the
canvas), so a legitimate full-bleed background (`.bg-photo`/`.bg-soft`, which lives OUTSIDE `.stage`)
never false-positives. Needs Chrome DevTools Protocol; without it, falls back to screenshots + a
pixel blank-check only (no overflow measurement).

Usage:  python scripts/keyframe_qa.py <out_dir> [--p N] [--json]
Exit 0 when clean (this is advisory); non-zero if any page is blank or overflows. The contact
sheets are the primary artifact — open `_keyframes/all.png` to eyeball tofu / off-theme / reveals.
"""
import argparse, base64, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import scenes  # reuse the Chrome bin resolver + per-shot screenshot fallback

DEFAULT_PS = [0.0, 0.25, 0.5, 0.75, 1.0]
OVERFLOW_TOL = 6   # px a content box may exceed the canvas before it's flagged

# max px any content box (under .stage/.split — NOT full-bleed backdrops) exceeds the canvas,
# plus the visible text length (to catch a blank / never-revealed page).
_OVERFLOW_JS = (
    "(function(){var W=window.innerWidth,H=window.innerHeight,worst=0;"
    "var n=document.querySelectorAll('.stage *,.split *');"
    "for(var i=0;i<n.length;i++){var r=n[i].getBoundingClientRect();"
    "if(r.width<1||r.height<1)continue;"
    "var o=Math.max(r.right-W,r.bottom-H,-r.left,-r.top);if(o>worst)worst=o;}"
    "var t=(document.body.innerText||'').replace(/\\s+/g,'').length;"
    "return JSON.stringify({worst:Math.round(worst),textlen:t});})()")


def _is_blank(img):
    lo, hi = img.convert("L").getextrema()
    return (hi - lo) < 12


def _sheet(imgs, path, cols=None, tw=560, th=315):
    cols = cols or len(imgs)
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
    report, last_frames, errors = [], [], 0
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
            issues = []
            if chrome:
                try:
                    info = _dom_probe(chrome)   # page is still at p=1 (last shot) — measure it
                    if info.get("textlen", 0) < 2:
                        issues.append("BLANK at p=1 (reveal never fired / broken page)")
                    if info.get("worst", 0) > OVERFLOW_TOL:
                        issues.append(f"content overflows the safe canvas by {info['worst']}px — "
                                      "shorten the text or split the beat")
                except Exception:
                    if _is_blank(final):
                        issues.append("BLANK at p=1 (reveal never fired / broken page)")
            elif _is_blank(final):
                issues.append("BLANK at p=1 (reveal never fired / broken page)")
            if issues:
                errors += 1
            report.append({"scene": idx, "status": "FAIL" if issues else "ok", "issues": issues})
    finally:
        if chrome:
            chrome.close()

    if last_frames:
        _sheet(last_frames, os.path.join(kf, "all.png"), cols=min(4, len(last_frames)))

    if as_json:
        print(json.dumps({"errors": errors, "report": report, "cdp": bool(chrome)}, indent=2))
    else:
        for r in report:
            mark = "✗" if r["status"] != "ok" else "✓"
            extra = ("  " + "; ".join(r["issues"])) if r.get("issues") else ""
            print(f"  {mark} scene {r['scene']:02d} [{r['status']}]{extra}")
        mode = "DOM+shots" if chrome else "shots-only (no CDP → overflow unchecked)"
        print(f"[keyframe_qa] {'OK' if errors == 0 else 'ISSUES'}  {len(report)} html page(s), "
              f"{errors} issue(s) [{mode}]; sheets -> {kf}/  (open all.png to eyeball tofu/theme/reveals)")
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
