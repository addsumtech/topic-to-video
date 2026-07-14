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
# `cbotc` = deepest REAL-content bottom, EXCLUDING full-bleed backdrops, faint decorative watermarks,
# and bottom-corner chrome (.credit/.pageno) — used for the caption-band overlap check (content must
# clear the bottom strip the flush caption is drawn over). It differs from `cbot` (which includes any
# box) precisely so a low-opacity texture or an image credit can't mask a real chart/label spilling
# into the band. `.ghost`/`.icon-ghost` are ~.05-.06 opacity `pointer-events:none` watermarks that
# CAN sit under `.stage` (a card watermark, an oversized ghost number) — excluded so a faint watermark
# reaching the band never phantom-blocks the gate; `.bg-glow` is a backdrop that may also land there.
_CBOTC_EXCL = (".bg-photo,.bg-soft,.bg-motif,.bg-grid,.bg-glow,.bg-live,.bg-drift,.scrim,"
               ".ghost,.icon-ghost,.credit,.pageno,[data-ambient]")
_OVERFLOW_JS = (
    "(function(){var W=window.innerWidth,H=window.innerHeight,worst=0,ct=1e9,cb=-1e9,cl=1e9,cr=-1e9,cbc=-1e9;"
    "var n=document.querySelectorAll('.stage *,.split *');"
    "for(var i=0;i<n.length;i++){var r=n[i].getBoundingClientRect();"
    "if(r.width<1||r.height<1)continue;"
    "var o=Math.max(r.right-W,r.bottom-H,-r.left,-r.top);if(o>worst)worst=o;"
    "var cs=getComputedStyle(n[i]);if(cs.opacity!=='0'&&cs.display!=='none'){"
    "if(r.top<ct)ct=r.top;if(r.bottom>cb)cb=r.bottom;if(r.left<cl)cl=r.left;if(r.right>cr)cr=r.right;"
    "if(!n[i].matches('" + _CBOTC_EXCL + "')&&r.bottom>cbc)cbc=r.bottom;}}"
    "var t=(document.body.innerText||'').replace(/\\s+/g,'').length;"
    "var EXCL='" + _CENTER_EXCL + "',centered=0,para=document.querySelectorAll('.sub,.note,.lead,p');"
    "for(var j=0;j<para.length;j++){var e=para[j],cs=getComputedStyle(e);"
    "if(cs.textAlign!=='center')continue;if(e.closest&&e.closest(EXCL))continue;"
    "var fs=parseFloat(cs.fontSize)||0,lh=cs.lineHeight;"
    "lh=(lh==='normal'||!lh)?1.4*fs:parseFloat(lh);if(lh<1)continue;"
    "var lines=Math.round(e.scrollHeight/lh),w=e.getBoundingClientRect().width;"
    "if(lines>=3&&w>=600)centered++;}"
    "var bleed=!!document.querySelector('.bg-photo,.bg-soft,.bg-motif,.bg-grid');"
    "return JSON.stringify({worst:Math.round(worst),textlen:t,centered:centered,"
    "ctop:Math.round(ct),cbot:Math.round(cb),cbotc:Math.round(cbc),cleft:Math.round(cl),cright:Math.round(cr),"
    "bleed:bleed,cued:!!document.querySelector('[data-cue-index]')});})()")

# Reveal-count probe (evaluated at EACH frozen p-state): how many reveal elements are visible now.
# Used for the STAGGER advisory — on a PACED page (no data-cue-index) a proper stagger makes this rise
# across the p-states; if most are already visible at p=0.25 the page dumps everything at once.
_REVEAL_COUNT_JS = (
    "(function(){var n=document.querySelectorAll('.reveal,.reveal-up,.reveal-up-sm,.reveal-pop,"
    ".reveal-wipe,.reveal-glow'),tot=0,vis=0;for(var i=0;i<n.length;i++){"
    "var r=n[i].getBoundingClientRect();if(r.width<1)continue;tot++;"
    "if(parseFloat(getComputedStyle(n[i]).opacity)>0.5)vis++;}"
    "return JSON.stringify({tot:tot,vis:vis});})()")

# Early-pop probe (evaluated at the p=0 frozen state, where seek.js has revealed NOTHING yet): any
# reveal element already painted (opacity > 0.05) has a BASE OPACITY leaking past .reveal's opacity:0
# — a decorative class (a dim/tint) set the `opacity` PROPERTY, which the reveal owns, so the element
# pops in BEFORE its cue and breaks step-by-step (top-to-bottom / left-to-right) order. Ambient
# backdrops (.bg-live/.bg-drift/[data-ambient] — progress-driven, legitimately visible at p=0) and
# unanimated elements are excluded. Returns each offender's class + opacity + top-y.
_EARLY_POP_JS = (
    "(function(){var n=document.querySelectorAll('.reveal,.reveal-up,.reveal-up-sm,.reveal-pop,"
    ".reveal-wipe,.reveal-glow'),out=[];for(var i=0;i<n.length;i++){var e=n[i];"
    "if(e.matches('.bg-live,.bg-drift,[data-ambient]'))continue;"
    "var r=e.getBoundingClientRect();if(r.width<1||r.height<1)continue;"
    "var cs=getComputedStyle(e);if(cs.animationName==='none')continue;"
    "var op=parseFloat(cs.opacity);if(op>0.05)out.push({cls:e.className,op:Math.round(op*100)/100,"
    "top:Math.round(r.top)});}return JSON.stringify(out);})()")

# Connector-alignment probe (evaluated at the final p=1 state): a `.connector`/`.arrow` that joins
# STACKED blocks must share their horizontal alignment. Flags a connector explicitly `text-align:center`
# whose box is WIDE (so centring actually pushes the glyph to the column centre) sitting in a VERTICAL
# stack whose text-bearing siblings are left/start-aligned — the glyph then floats to centre while the
# content (numbers/labels) sits at the left (a visible misalignment). Precise + low-false-positive:
# (a) the canonical `.flow .arrow` centres via `align-self` (text-align stays start) → not flagged;
# (b) a genuinely centred card stack has centre-aligned siblings → not flagged; (c) a thin RAIL sized to
# itself (`.hs-connect` width:5px, centred as a unit in a centred hub layout) has a narrow box, so
# text-align can't displace it → not flagged. Only a bespoke left-aligned stack with a stray centred
# full-width connector trips it.
_CONNECTOR_ALIGN_JS = (
    "(function(){var out=[],c=document.querySelectorAll('.connector,.arrow');"
    "for(var i=0;i<c.length;i++){var el=c[i];if(getComputedStyle(el).textAlign!=='center')continue;"
    # only an arrow/chevron GLYPH (≤3 chars) — a `.connector`-marked CONTENT box (e.g. a hub label that
    # borrows a cue) or an empty rail is not an alignment-sensitive glyph.
    "var t=(el.innerText||'').trim();if(t.length<1||t.length>3)continue;"
    "var p=el.parentElement;if(!p)continue;var pcs=getComputedStyle(p);"
    "var vertical=(pcs.display.indexOf('flex')>=0)?(pcs.flexDirection==='column'):true;if(!vertical)continue;"
    "var er=el.getBoundingClientRect(),pr=p.getBoundingClientRect();"
    "if(pr.width<=0||er.width<pr.width*0.4)continue;"   # narrow box: centring can't displace the glyph
    "var sib=p.children,left=0;for(var j=0;j<sib.length;j++){var s=sib[j];"
    "if(s===el||s.matches('.connector,.arrow'))continue;if(!(s.innerText||'').trim())continue;"
    "var ta=getComputedStyle(s).textAlign;if(ta==='left'||ta==='start')left++;}"
    "if(left>=1)out.push({cls:el.className,top:Math.round(er.top)});}"
    "return JSON.stringify(out);})()")


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


def _reveal_count(chrome):
    """{tot, vis} reveal elements at the page's CURRENT frozen state (call right after a ?p= shot)."""
    try:
        r = chrome._cmd("Runtime.evaluate",
                        {"expression": _REVEAL_COUNT_JS, "returnByValue": True}, chrome.sid)
        return json.loads(r["result"]["result"]["value"])
    except Exception:
        return {"tot": 0, "vis": 0}


def _early_pop(chrome):
    """Reveal elements already visible at the current (p=0) frozen state — a base-opacity leak."""
    try:
        r = chrome._cmd("Runtime.evaluate",
                        {"expression": _EARLY_POP_JS, "returnByValue": True}, chrome.sid)
        return json.loads(r["result"]["result"]["value"])
    except Exception:
        return []


def _connector_misaligned(chrome):
    """Connectors centre-aligned over a left-aligned vertical stack (misaligned) at the current state."""
    try:
        r = chrome._cmd("Runtime.evaluate",
                        {"expression": _CONNECTOR_ALIGN_JS, "returnByValue": True}, chrome.sid)
        return json.loads(r["result"]["result"]["value"])
    except Exception:
        return []


def run(out_dir, ps=DEFAULT_PS, as_json=False):
    data = json.load(open(os.path.join(out_dir, "storyboard.json")))
    meta = data["meta"]; meta["_out"] = out_dir
    W, H = (1080, 1920) if meta.get("aspect") == "9:16" else (1920, 1080)
    try:                                  # the flush caption strip (px) is drawn over the bottom of each
        import render                     # frame — content must clear it; 0 in overlay mode / captions off
        band = render._caption_band_px(meta, W, H)
    except Exception:
        band = 0
    kf = os.path.join(out_dir, "_keyframes"); os.makedirs(kf, exist_ok=True)
    html = [s for s in data.get("slides", []) if s.get("type") == "html"]
    if not html:
        print("[keyframe_qa] no html scenes — nothing to check"); return 0

    chrome = _open_cdp(meta, W, H)
    report, last_frames, errors, warns = [], [], 0, 0
    centroids = []                        # (scene, cx, cy) normalized content centroids, for silhouette repetition
    try:
        for s in html:
            idx = s.get("index")
            page = (s.get("props") or {}).get("html")
            if not page:
                continue
            url = "file://" + os.path.abspath(os.path.join(out_dir, page))
            frames, ok, rvis, rtot, early_pop = [], True, [], 0, []
            for pi, p in enumerate(ps):
                fp = os.path.join(kf, f"scene_{idx:02d}_p{int(p*100):03d}.png")
                try:
                    if chrome:
                        chrome.shot(url + f"?p={p}", fp)          # CDP: (url, out_path)
                        rc = _reveal_count(chrome)                # count visible reveals at THIS frozen state
                        rvis.append(rc["vis"]); rtot = max(rtot, rc["tot"])
                        if pi == 0 and p <= 0.02:                 # p=0: nothing revealed yet — any visible reveal leaks
                            early_pop = _early_pop(chrome)
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
                    mis = _connector_misaligned(chrome)   # centred connector over a left-aligned stack
                    if mis:
                        advisories.append(f"{len(mis)} connector(s) centre-aligned over left-aligned content — "
                                          "align the ↓/arrow to the content it joins (left-align it under the "
                                          "anchor); see html-pages 'A connector shares the ALIGNMENT'")
                    # BLANK only when there is genuinely nothing rendered — not merely little text. A single-
                    # glyph hero ('7', a lone '%', one CJK char) or an icon-only diagram has a real content
                    # bbox; a full-bleed visual sets bleed. Flag only empty text AND no visible content box.
                    _has_box = (info.get("cright", 0) > info.get("cleft", 1e9)
                                and info.get("cbot", -1e9) > info.get("ctop", 1e9))
                    if info.get("textlen", 0) < 1 and not _has_box and not info.get("bleed"):
                        issues.append("BLANK at p=1 (reveal never fired / broken page)")
                    if info.get("worst", 0) > OVERFLOW_TOL:
                        issues.append(f"content overflows the safe canvas by {info['worst']}px — "
                                      "shorten the text or split the beat")
                    # CAPTION-BAND OVERLAP: the flush caption strip is drawn IN-canvas over the bottom
                    # `band` px; REAL content (cbotc excludes full-bleed backdrops + .credit/.pageno
                    # chrome) must clear it, or the caption paints over it. Tolerate a small kiss into the
                    # strip's top padding; flag a meaningful intrusion so the author raises/scales it.
                    if band:
                        band_top = H - band
                        into = info.get("cbotc", -1) - band_top
                        if into > max(16, int(band * 0.18)):
                            issues.append(f"content reaches {into}px into the bottom {band}px caption band "
                                          f"— raise/scale it so the burned caption never overlaps (reserve "
                                          f"the bottom ~{band}px; see captions.md)")
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
                    # STAGGER (paced pages only — a cued page renders BLIND here [no ?cues=], so its
                    # reveals all fire at delay 0 and would false-flag): on a page with NO data-cue-index,
                    # a proper stagger makes the visible-reveal count RISE across the p-states.
                    if not info.get("cued") and rtot >= 3 and len(ps) >= 4:
                        ei = next((i for i, pp in enumerate(ps) if pp >= 0.25), 1)   # first ~quarter state, not literal index 1
                        early = rvis[ei] / rtot if ei < len(rvis) else 1.0
                        rises = sum(1 for a, b in zip(rvis, rvis[1:]) if b > a)
                        if early > 0.7 or rises < 2:
                            advisories.append(f"no stagger — {round(100*early)}% of reveals already visible by "
                                              f"p={ps[ei]} (rises across only {rises} step[s]); give each component "
                                              f"its own data-cue-index so they land one-by-one")
                    # EARLY POP (measured at p=0, where NOTHING should be revealed): a reveal element
                    # already painted → its base opacity leaked past .reveal's opacity:0 (a decorative
                    # class set the `opacity` PROPERTY the reveal owns), so it appears before its cue and
                    # breaks step-by-step top-to-bottom / left-to-right order. Blocks the gate.
                    if early_pop:
                        top = ", ".join(f"{(o['cls'].split(' reveal')[0] or o['cls']).strip()}@op{o['op']}"
                                        for o in sorted(early_pop, key=lambda o: -o["op"])[:4])
                        issues.append(f"{len(early_pop)} reveal element(s) already visible at p=0 (early pop "
                                      f"before cue): {top}. A decorative class set the `opacity` property that "
                                      ".reveal owns — dim via filter:opacity() or a translucent color instead")
                    # content centroid (normalized) for the deck-level silhouette-repetition advisory
                    if info.get("cright", -1) > info.get("cleft", 0) and info.get("cbot", -1) > info.get("ctop", 0):
                        centroids.append((idx, ((info["cleft"] + info["cright"]) / 2) / W,
                                          ((info["ctop"] + info["cbot"]) / 2) / H))
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

    # Deck-level SILHOUETTE REPETITION (advisory): when >~half the pages share one content centroid
    # cluster, the deck reads as one template even if the forms differ. Greedy cluster @ tol 0.08.
    deck_notes = []
    if len(centroids) >= 4:
        best, best_c = 0, None
        for _, ax, ay in centroids:
            k = sum(1 for _, bx, by in centroids if abs(ax - bx) <= 0.08 and abs(ay - by) <= 0.08)
            if k > best:
                best, best_c = k, (ax, ay)
        if best / len(centroids) > 0.5:
            cy = best_c[1]
            zone = "top" if cy < 0.40 else "bottom" if cy > 0.60 else "centered"   # from the cluster's actual centroid
            deck_notes.append(f"silhouette repetition: {best}/{len(centroids)} pages share one content "
                              f"centroid ({zone}) — vary the vertical anchor / horizontal balance so the deck "
                              f"isn't one template (design-critic D11)")

    if as_json:
        print(json.dumps({"errors": errors, "warns": warns, "report": report,
                          "deck_advisories": deck_notes, "cdp": bool(chrome)}, indent=2))
    else:
        for r in report:
            mark = {"FAIL": "✗", "WARN": "!"}.get(r["status"], "✓")
            notes = (r.get("issues") or []) + (r.get("advisories") or [])
            extra = ("  " + "; ".join(notes)) if notes else ""
            print(f"  {mark} scene {r['scene']:02d} [{r['status']}]{extra}")
        for dn in deck_notes:
            print(f"  ! deck  {dn}")
        mode = "DOM+shots" if chrome else "shots-only (no CDP → overflow/centered unchecked)"
        print(f"[keyframe_qa] {'OK' if errors == 0 else 'ISSUES'}  {len(report)} html page(s), "
              f"{errors} issue(s), {warns + len(deck_notes)} advisory(ies) [{mode}]; sheets -> {kf}/  "
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
