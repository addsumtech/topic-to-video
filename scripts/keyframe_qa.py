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
pixel blank-check only (no overflow measurement, and no type-glide census — see below).

Also runs the TYPE-GLIDE CENSUS (post-tts, when CDP is available): a page's OWN custom animation
([data-ambient], a per-page `<style>` @keyframes) crawling text under an axis-aligned matrix, which
Chrome snaps to the whole device pixel — a staircase (3+ whole-pixel steps) is an ERROR, 1-2 is a
WARN. Reuses text_safe_qa.judge_glide/glide_level, the same judgment the Remotion tier's census uses.

Usage:  python scripts/keyframe_qa.py <out_dir> [--p N] [--json]
Exit 0 when clean; non-zero if any page is BLANK or OVERFLOWS (those block). The centered-
paragraph check is advisory-only and never blocks. The contact sheets are the primary artifact —
open `_keyframes/all.png` to eyeball tofu / off-theme / mistimed reveals.
"""
import argparse, base64, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import scenes  # reuse the Chrome bin resolver + per-shot screenshot fallback
import cues as _cues
from _caption_band import caption_band_px   # the ONE definition of the burned-caption band

DEFAULT_PS = [0.0, 0.25, 0.5, 0.75, 1.0]
OVERFLOW_TOL = 6   # px a content box may exceed the canvas before it's flagged

# DOM probe (page frozen at p=1). Returns: `worst` = max px any content box (under .stage/.split,
# NOT full-bleed backdrops) exceeds the canvas; `textlen` = visible text length (blank detection);
# `centered` = count of CENTERED running paragraphs (advisory — body text should be left-aligned to
# scan; excludes display/diagram classes that are centered by design).
_CENTER_EXCL = (".flow,.step,.hubspoke,.hs-spoke,.hs-hub,.timeline,.tl-node,.quadrant,.cell,"
                ".scorecard,.tile,.title,.pullquote,.kicker,.stat,.block")
# `clip` = worst px of TEXT clipped INSIDE a box (a fixed-height / overflow:hidden card slicing its own
# content — invisible to the canvas-overflow check). Fill/bar components legitimately clip (a .meter clips
# its .fill), so those are excluded. `cbot` (content bottom) also drives the caption-zone occlusion check.
# `mystery` = bordered EMPTY leaf boxes ≥~6000px² with no text and no declared role — "mystery furniture"
# a viewer can't decode (an element may assert its idiom with a `data-role` attribute to opt out).
# `nearmiss` = sibling edge pairs off by 5-22px — the "almost aligned" smell (deliberate offsets read
# clearly different; near-misses read as sloppiness). Both feed non-blocking advisories.
_OVERFLOW_JS = (
    "(function(){var W=window.innerWidth,H=window.innerHeight,worst=0,clip=0,ct=1e9,cb=-1e9,cl=1e9,cr=-1e9;"
    "var wx=0,wy=0,wsum=0;"
    "var myst=0,mystEx='';"
    "var n=document.querySelectorAll('.stage *,.split *');"
    "var FILL='.meter,.segbar,.bar,.fill,.gauge,.track,.waffle,.isotype,.bullet,.spark';"
    "for(var i=0;i<n.length;i++){var e=n[i],r=e.getBoundingClientRect();"
    "if(r.width<1||r.height<1)continue;"
    # .bleed-out = an element DELIBERATELY cropped by the frame edge. The crop is the composition,
    # not an accident, so its subtree is exempt from the overflow measure (mirrors how a full-bleed
    # backdrop is exempt). Without this, the off-canvas-bleed primitive would be unusable: the very
    # gesture it exists to express is the one the probe blocks.
    "if(e.closest&&e.closest('.bleed-out'))continue;"
    # …and the same applies to OVERFLOW: a transparent <svg> drawing surface that extends past the
# canvas is not spilled content — its strokes are measured individually below, so a real spill
# is still caught by the child that actually spills. (The container was excluded from the
# content bbox already; leaving it in the overflow measure was half a fix.)
    "if(e.tagName.toLowerCase()!=='svg'){"
    "var o=Math.max(r.right-W,r.bottom-H,-r.left,-r.top);if(o>worst)worst=o;}"
    "var cs=getComputedStyle(e);if(cs.opacity!=='0'&&cs.display!=='none'){"
    # An <svg> CONTAINER's box is the drawing surface it reserves, not ink. A page that overlays one
    # full-canvas transparent SVG and positions its strokes inside (a normal, and for hand-drawn
    # registers the natural, technique) would otherwise report content spanning y=0..H — tripping the
    # caption-zone gate and pinning the content band to 0.00 on every such page. Its drawable children
    # are themselves in this same `.stage *` walk and contribute their REAL stroke boxes, so skipping
    # the container loses nothing and stops the probe measuring a proxy instead of the thing.
    "if(e.tagName.toLowerCase()!=='svg'){"
    "if(r.top<ct)ct=r.top;if(r.bottom>cb)cb=r.bottom;if(r.left<cl)cl=r.left;if(r.right>cr)cr=r.right;}"
    # AREA-WEIGHTED centroid = where the visual MASS actually sits. The bbox midpoint
    # ((cleft+cright)/2) that this replaced is ~0.5 for ANY page whose content spans the frame,
    # however left- or right-heavy it looks — so it reported "everything is centred" for a deck whose
    # ink-weighted balance measured 12-left/8-mid/7-right. Weight each element that carries its own
    # ink (a leaf box, or a box with direct text) by its area; containers are skipped so a wrapper
    # and its children don't double-count the same pixels.
    "var own=false;for(var k=0;k<e.childNodes.length;k++){var cn=e.childNodes[k];"
    "if(cn.nodeType===3&&(cn.nodeValue||'').trim()){own=true;break;}}"
    "if((own||e.children.length===0)&&r.width*r.height>=100){"
    "var ar=r.width*r.height;wx+=ar*(r.left+r.right)/2;wy+=ar*(r.top+r.bottom)/2;wsum+=ar;}"
    "if(e.children.length===0&&!(e.innerText||'').trim()&&r.width*r.height>=6000"
    "&&!e.hasAttribute('data-role')&&!(e.matches&&e.matches(FILL))"
    "&&!/^(svg|img|video|canvas|path|rect|circle|line|i)$/i.test(e.tagName)"
    "&&(parseFloat(cs.borderTopWidth)||0)>0.5&&cs.borderTopStyle!=='none'){"
    "myst++;if(!mystEx)mystEx=String(e.className).slice(0,40);}}"
    "var oy=cs.overflowY;if((oy==='hidden'||oy==='clip')&&e.scrollHeight-e.clientHeight>8"
    "&&(e.innerText||'').trim().length>12&&!(e.matches&&e.matches(FILL))){"
    "var cc=e.scrollHeight-e.clientHeight;if(cc>clip)clip=cc;}}"
    "var nm=0,nmEx='',crowd=0,crowdEx='';var pars=document.querySelectorAll('.stage,.split,.stage *,.split *');"
    "for(var pi=0;pi<pars.length;pi++){var pe=pars[pi],ch=pe.children;"
    "if(ch.length<2||ch.length>12)continue;var bx=[];"
    "for(var ci=0;ci<ch.length;ci++){var el=ch[ci],rr=el.getBoundingClientRect();"
    "if(rr.width*rr.height<2500)continue;var c2=getComputedStyle(el);"
    "if(c2.opacity==='0'||c2.display==='none'||el.hasAttribute('data-role'))continue;"
    "rr.abs=(c2.position==='absolute'||c2.position==='fixed');bx.push(rr);}"
    "for(var a=0;a<bx.length;a++)for(var b=a+1;b<bx.length;b++){var A=bx[a],B=bx[b];"
    "var ds=[Math.abs(A.left-B.left),Math.abs(A.top-B.top),Math.abs(A.right-B.right),Math.abs(A.bottom-B.bottom)];"
    "for(var di=0;di<4;di++){if(ds[di]>=5&&ds[di]<=22){nm++;if(!nmEx)nmEx=String(pe.className).slice(0,30);break;}}"
    "var vgap=Math.max(A.top,B.top)-Math.min(A.bottom,B.bottom);"
    "var hgap=Math.max(A.left,B.left)-Math.min(A.right,B.right);"
    "var hOv=Math.min(A.right,B.right)-Math.max(A.left,B.left);"
    "var vOv=Math.min(A.bottom,B.bottom)-Math.max(A.top,B.top);"
    "var minW=Math.min(A.width,B.width),minH=Math.min(A.height,B.height);"
    "if(A.abs&&B.abs&&((vgap>=-8&&vgap<=12&&hOv>0.3*minW)||(hgap>=-8&&hgap<=12&&vOv>0.3*minH))){"
    "crowd++;if(!crowdEx)crowdEx=String(pe.className).slice(0,30);}}}"
    # VISIBLE text only. innerText counts text inside an `opacity:0` element (it excludes only
    # display:none / visibility:hidden), and every .reveal* starts at opacity:0 — so a page whose
    # reveals never fired reported a full text length and sailed through the BLANK check, which is
    # precisely the failure the check exists to catch. Walk the leaf text nodes and charge each one
    # only when its whole ancestor chain is actually visible.
    # The memo caches each element's OWN chain verdict, computed recursively. An earlier version
    # cached the verdict of whichever text node happened to be walked first onto ALL of its
    # ancestors — so one hidden element poisoned its shared parent and every later sibling under
    # that parent was judged invisible too (a page with a hidden block ahead of a visible one
    # reported textlen 0, i.e. a FALSE BLANK, which blocks a render).
    "var t=0;(function(){var seen=new Map();"
    "function vis(el){if(!el||el===document.body)return true;"
    "if(seen.has(el))return seen.get(el);"
    "var c=getComputedStyle(el);"
    "var v=!(c.display==='none'||c.visibility==='hidden'||parseFloat(c.opacity)<0.05)&&vis(el.parentElement);"
    "seen.set(el,v);return v;}"
    "var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);var nd;"
    "while((nd=w.nextNode())){var s=(nd.nodeValue||'').replace(/\\s+/g,'');"
    "if(s&&vis(nd.parentElement))t+=s.length;}})();"
    "var EXCL='" + _CENTER_EXCL + "',centered=0,para=document.querySelectorAll('.sub,.note,.lead,p');"
    "for(var j=0;j<para.length;j++){var pe=para[j],pcs=getComputedStyle(pe);"
    "if(pcs.textAlign!=='center')continue;if(pe.closest&&pe.closest(EXCL))continue;"
    "var fs=parseFloat(pcs.fontSize)||0,lh=pcs.lineHeight;"
    "lh=(lh==='normal'||!lh)?1.4*fs:parseFloat(lh);if(lh<1)continue;"
    "var lines=Math.round(pe.scrollHeight/lh),w=pe.getBoundingClientRect().width;"
    "if(lines>=3&&w>=600)centered++;}"
    # ENCLOSURE CONTAINMENT: a ring/circle that OVERLAPS text but does not CONTAIN it. An enclosure
    # asserts "these ones, not the others" — text spilling past its edge silently breaks that claim,
    # and no geometry gate can see it (nothing overflows the canvas, nothing is blank, nothing enters
    # the caption zone; the frame is simply wrong about what it encircles).
    "var encl=0,enclEx='';"
    "document.querySelectorAll('.ring,[data-encloses]').forEach(function(rg){"
    "var R=rg.getBoundingClientRect();if(R.width<60||R.height<40)return;"
    "document.querySelectorAll('.stage *,.split *').forEach(function(t){"
    "if(t===rg||rg.contains(t))return;var own=false;"
    "for(var k=0;k<t.childNodes.length;k++){var c=t.childNodes[k];"
    "if(c.nodeType===3&&(c.nodeValue||'').trim()){own=true;break;}}"
    # Measure the TEXT, not its container. A div declared `width:1620px` whose text only fills 1216px
# has a box that spills past the ring while the ink sits comfortably inside — the same
# box-instead-of-ink error this probe fixes elsewhere. Range over the contents gives the real
# glyph extent.
    "if(!own)return;var rr=document.createRange();rr.selectNodeContents(t);"
    "var b=rr.getBoundingClientRect();rr.detach&&rr.detach();"
    "if(b.width<10||b.height<10)return;"
    "var cs2=getComputedStyle(t);if(cs2.opacity==='0'||cs2.display==='none')return;"
    "var ov=!(b.right<R.left||b.left>R.right||b.bottom<R.top||b.top>R.bottom);if(!ov)return;"
    "var ins=b.left>=R.left-3&&b.right<=R.right+3&&b.top>=R.top-3&&b.bottom<=R.bottom+3;"
    "if(!ins){encl++;if(!enclEx)enclEx=(t.innerText||'').trim().slice(0,16);}});});"
    "var bleed=!!document.querySelector('.bg-photo,.bg-soft,.bg-motif,.bg-grid');"
    "return JSON.stringify({worst:Math.round(worst),clip:Math.round(clip),textlen:t,centered:centered,"
    "ctop:Math.round(ct),cbot:Math.round(cb),cleft:Math.round(cl),cright:Math.round(cr),"
    "wcx:wsum?Math.round(wx/wsum):-1,wcy:wsum?Math.round(wy/wsum):-1,encl:encl,enclEx:enclEx,"
    "mystery:myst,mystery_ex:mystEx,nearmiss:nm,nearmiss_ex:nmEx,crowd:crowd,crowd_ex:crowdEx,"
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


def _blank_issue(info):
    """The BLANK gate as a pure check — shared with snapshot.py so a contest frame whose reveal never
    fired can't pass as 'floor clean'. BLANK only when there is genuinely nothing rendered: empty text
    AND no visible content box AND no full-bleed backdrop (a single-glyph hero or icon-only diagram has
    a real bbox; a photo page sets bleed). Returns the issue string, or None."""
    has_box = (info.get("cright", 0) > info.get("cleft", 1e9)
               and info.get("cbot", -1e9) > info.get("ctop", 1e9))
    if info.get("textlen", 0) < 1 and not has_box and not info.get("bleed"):
        return "BLANK at p=1 (reveal never fired / broken page)"
    return None


_VERTICAL_CSS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "html", "vertical.css")


def _fill_zone(W, H):
    """(top, bottom) px of the 9:16 content zone: vertical.css's `.stage` top padding down to where the
    renderer's caption band begins (caption_band_px) — the same two sources the page and the burn use,
    not a literal that drifts from them (the class of bug 0c00fa7 fixed for the caption check)."""
    css = open(_VERTICAL_CSS, encoding="utf-8").read()
    m = re.search(r"\.stage\s*\{[^}]*?padding:\s*(\d+)px", css)
    if not m:
        raise RuntimeError("`.stage` padding not found in %s — the 9:16 fill zone is read from it" % _VERTICAL_CSS)
    return int(m.group(1)), H - caption_band_px(W, H)


def _fill_fraction(info, W, H):
    top, bot = _fill_zone(W, H)
    return (info["cbot"] - info["ctop"]) / float(bot - top)


def _geometry_issues(info, meta, W, H):
    """Pure classifier for the box-geometry gate — the three ways content can be *placed* wrong even
    when the reveal fired: (1) it overflows the safe canvas, (2) a fixed-height / overflow:hidden box
    CLIPS its own text (invisible to the canvas check — the box fits, its content doesn't), (3) it
    reaches into the bottom caption zone where an overlay subtitle burns. Returns blocking-issue
    strings. Chrome-free + unit-tested so the thresholds can't silently drift."""
    meta = meta or {}                       # defensive: a direct API call may pass None (run() always passes a dict)
    out = []
    if info.get("worst", 0) > OVERFLOW_TOL:
        out.append(f"content overflows the safe canvas by {info['worst']}px — "
                   "shorten the text or split the beat")
    if info.get("clip", 0) > 8:
        out.append(f"text CLIPPED inside a card/box by {info['clip']}px — a fixed height / "
                   "overflow:hidden is cutting its own content; give the box auto height, "
                   "shorten the text, or split the beat")
    # caption-zone occlusion: an overlay caption burns into the bottom `caption_band_px(W,H)` of the
    # frame — the SAME band the renderer actually reserves (runtime/layout.ts, via _caption_band.py),
    # not a flat 14%/0.86*H guess. That guess under-counted the real band (200px/18.5% at 16:9 vs the
    # old 151px/14%) so a page could sit BELOW the real band's top edge and still read as clean — the
    # exact miss a 9-line card grid hit (resting content at y935 of 1080, inside the true 880px band
    # top, under the old 928px line). band mode moves captions below the content, so it's exempt; a
    # page with no visible content box (a full-bleed hero) has nothing to occlude.
    _has_box = (info.get("cright", 0) > info.get("cleft", 1e9)
                and info.get("cbot", -1e9) > info.get("ctop", 1e9))
    cap_top = H - caption_band_px(W, H)
    if (meta.get("captions", True) and meta.get("caption_mode", "overlay") != "band"
            and _has_box and info.get("cbot", -1) > cap_top):
        out.append(f"content reaches the bottom caption zone (lowest content y={info['cbot']} "
                   f"> {cap_top}px) — it will overlap the burned subtitle; push content "
                   f"up (reduce sizes/gaps, or reserve the bottom {round(100*(H-cap_top)/H)}%)")
    return out


def _reveal_count(chrome):
    """{tot, vis} reveal elements at the page's CURRENT frozen state (call right after a ?p= shot)."""
    try:
        r = chrome._cmd("Runtime.evaluate",
                        {"expression": _REVEAL_COUNT_JS, "returnByValue": True}, chrome.sid)
        return json.loads(r["result"]["result"]["value"])
    except Exception:
        return {"tot": 0, "vis": 0}


# ── THE TYPE-GLIDE CENSUS, ported to the HTML tier ──────────────────────────────────────────────
#
# The shared base.css reveals (.reveal-up etc.) already carry the baseline unlock (base.css, the
# `matrix(1,.0009765625,0,1,0,0)` skewY trick) — proven clean in remotion/src/runtime/textSafe.tsx's
# own census. What's UNCHECKED is a page's OWN custom animation: a `[data-ambient]` text drift, or a
# per-page `<style>` @keyframes an author writes without knowing the unlock exists. Those can move
# TEXT under an axis-aligned matrix, which Skia/Chrome's text rasterizer snaps to the whole device
# pixel — a slow crawl holds for several frames then jumps, a staircase, while everything drawn
# beside it glides continuously.
#
# WHY A SEPARATE PLAIN-JS COPY, NOT THE TSX. textSafe.tsx's `auditGlide` is a React/Remotion-side
# module (TS, compiled by Remotion's own bundler); this tier drives Chrome directly over CDP with no
# build step, so sharing that file verbatim isn't cheap. What IS shared is the JUDGE: `judge_glide`/
# `glide_level` (text_safe_qa.py) are reused UNCHANGED — same {frame: {"lines":[...]}} shape in,
# same 3-steps-is-a-staircase rule out. Only the MEASUREMENT (walk the DOM, decide whether a line's
# composed matrix is axis-aligned) is a small plain-JS copy here, reduced to the core rule this tier
# needs: it drops textSafe.tsx's 3D-compositor / spatial-filter nuances (will-change layers, blur/
# drop-shadow re-snapping, preserve-3d) — edge cases this tier's hand-authored CSS doesn't produce —
# and keeps Skia's own test verbatim: a composed matrix's skewY entry rounds to zero at 1/1024
# (`snapsBaseline` in textSafe.tsx; `tests/test_keyframe_qa.py` pins the same `*1024` literal in
# both files so the two can't silently drift apart).
#
# HOW. `?p=` seeking is seek.js's OWN URL-driven mechanism; the census instead re-implements seek.js's
# freeze-at-progress formula directly (it is four lines) so it can call it in a plain JS loop, once per
# REAL VIDEO FRAME (`round(duration*fps)`, the same count render.py's `_render_scene` renders), inside
# ONE Runtime.evaluate — no per-frame navigation. Measured on jev-html: ~0.2-0.4s of in-page time for a
# ~20s/600-frame scene, so the cost stays a rounding error next to the existing per-p screenshot sweep.
GLIDE_FRAME_CAP = 3000   # ~100s at 30fps — a safety ceiling, not a tuned budget (every real scene here
                         # is far under it; this just keeps a pathological duration from hanging the page)

_GLIDE_JS_TMPL = r"""(function(nFrames, plist){
  function sec(v){v=parseFloat(v);return isNaN(v)?0:v;}
  var els = Array.prototype.slice.call(document.querySelectorAll('*')).filter(function(el){
    var n = getComputedStyle(el).animationName; return n && n !== 'none';
  });
  // mirrors seek.js's own freeze-at-progress formula exactly (ambient = driven by p across the WHOLE
  // scene; everything else = a reveal, anchored to its own authored delay) — re-implemented here so it
  // can be called once per frame in-process instead of once per page navigation.
  var spans = els.map(function(el){
    var cs = getComputedStyle(el);
    var ambient = el.matches('.bg-live, .bg-drift, [data-ambient]');
    return {el: el, d: sec(cs.animationDelay), dur: sec(cs.animationDuration), ambient: ambient};
  });
  // the page is loaded at p=0 (see _glide_issue), so every delay read above is the reveal's own start —
  // authored, or its cue time in cue mode — and the reveal clock runs to `total` exactly as in seek.js:
  // the scene's duration in cue mode, else the reveals' own envelope max(delay + duration).
  var q = new URLSearchParams(location.search), qdur = parseFloat(q.get('dur'));
  var total = (q.get('cues') && qdur > 0) ? qdur : spans.reduce(function(m, s){
    return s.ambient ? m : Math.max(m, s.d + s.dur);
  }, 0.001);
  function freeze(p){
    spans.forEach(function(s){
      s.el.style.animationDelay = (s.ambient ? -(p * s.dur) : (s.d - p * total)) + 's';
      s.el.style.animationPlayState = 'paused';
    });
  }
  function hasOwnText(el){
    var s = '';
    el.childNodes.forEach(function(n){ if (n.nodeType === 3) s += n.nodeValue || ''; });
    return s.trim();
  }
  // THIS element's own 2x2 linear transform, or null for a matrix3d it can't safely decompose
  // (mirrors textSafe.tsx `selfMatrix` minus the standalone `rotate` longhand, unused on this tier).
  function selfMatrix(cs){
    var tr = cs.transform;
    if (!tr || tr === 'none') return [1, 0, 0, 1];
    if (tr.indexOf('(') < 0) return null;
    var n = tr.slice(tr.indexOf('(') + 1, tr.lastIndexOf(')')).split(',')
             .map(function(x){ return parseFloat(x) || 0; });
    return n.length === 6 ? n : null;                 // matrix3d (16 terms): unmeasured, not guessed
  }
  function mul2(a, b){
    return [a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1], a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3]];
  }
  function domPath(el){                                // a stable per-page key: tag + sibling index, to body
    var path = [], e = el;
    while (e && e.nodeType === 1){
      var idx = 0, sib = e;
      while ((sib = sib.previousElementSibling)) idx++;
      path.unshift(e.tagName.toLowerCase() + idx);
      e = e.parentElement;
    }
    return path.join('/');
  }
  var out = {};
  // `plist`, when given, is the exact progress values to read (the sync audit passes the render's own capture
  // plan, so the census is the frames that SHIP); otherwise nFrames evenly spaced, as the glide census reads.
  var nRead = plist ? plist.length : nFrames;
  var VW = window.innerWidth, VH = window.innerHeight;
  for (var f = 0; f < nRead; f++){
    var p = plist ? plist[f] : ((nFrames <= 1) ? 0 : f / (nFrames - 1));
    freeze(p);
    var nodes = document.querySelectorAll('.stage *,.split *'), lines = [];
    for (var i = 0; i < nodes.length; i++){
      var el = nodes[i];
      var text = hasOwnText(el);
      if (!text) continue;
      var M = [1, 0, 0, 1], op = 1, hidden = false, steps = false, selfCs = null;
      var chain = [], e2 = el;
      while (e2 && e2.nodeType === 1){ chain.push(e2); e2 = e2.parentElement; }
      var r = el.getBoundingClientRect();
      // the VISIBLE box for the sync audit: inside the frame and every clipping ancestor (a word rising
      // through a mask is not readable while its first row of pixels peeks out)
      var cl = Math.max(0, r.left), ct = Math.max(0, r.top), cr = Math.min(VW, r.right), cb = Math.min(VH, r.bottom);
      for (var j = chain.length - 1; j >= 0; j--){
        var node = chain[j], cs = getComputedStyle(node);
        if (node === el) selfCs = cs;
        if (cs.display === 'none' || cs.visibility === 'hidden'){ hidden = true; break; }
        if (node.hasAttribute('data-type-steps')) steps = true;
        var own = selfMatrix(cs);
        if (own === null) M = null; else if (M !== null) M = mul2(M, own);
        op *= (parseFloat(cs.opacity) || 0);
        if (node !== el && (cs.overflowX !== 'visible' || cs.overflowY !== 'visible')){
          var c = node.getBoundingClientRect();
          cl = Math.max(cl, c.left); ct = Math.max(ct, c.top); cr = Math.min(cr, c.right); cb = Math.min(cb, c.bottom);
        }
      }
      if (hidden) continue;
      if (r.width < 1 || r.height < 1) continue;
      var ly = 0, oe = el;
      while (oe){ ly += oe.offsetTop || 0; oe = oe.offsetParent; }
      var rec = {k: domPath(el), y: Math.round(r.top * 1e4) / 1e4, o: Math.round(op * 100) / 100,
                 t: text.length > 96 ? text.slice(0, 96) + '…' : text,
                 ly: Math.round(ly), px: Math.round((parseFloat(selfCs.fontSize) || 0) * 100) / 100};
      var vis = Math.max(0, cr - cl) * Math.max(0, cb - ct) / (r.width * r.height);
      if (vis < 0.995) rec.v = Math.round(vis * 100) / 100;
      var fl = steps ? 's' : '';
      // Skia's own test (textSafe.tsx `snapsBaseline`): the composed skewY entry rounds to zero at
      // 1/1024 -> the baseline snaps to the device pixel. `M === null` (a matrix3d ancestor) is
      // unmeasured, not judged -- listed with 'c' like textSafe.tsx's composited-layer path.
      if (M === null) fl += 'c';
      else if (Math.round(Math.abs(M[1]) * 1024) !== 0) rec.u = 1;
      if (fl) rec.fl = fl;
      lines.push(rec);
    }
    out[f] = {lines: lines};
  }
  return JSON.stringify(out);
})(%d, %s)"""


def _glide_census(chrome, n_frames):
    """{frame_index: {"lines":[...]}} over `n_frames` real video frames of the page CURRENTLY loaded in
    `chrome` — one Runtime.evaluate, no per-frame navigation (see _GLIDE_JS_TMPL)."""
    n_frames = max(1, min(int(n_frames), GLIDE_FRAME_CAP))
    r = chrome._cmd("Runtime.evaluate",
                    {"expression": _GLIDE_JS_TMPL % (n_frames, "null"), "returnByValue": True}, chrome.sid)
    raw = json.loads(r["result"]["result"]["value"])
    return {int(f): rec for f, rec in raw.items()}


def _glide_issue(chrome, duration, fps, url=None):
    """(issue_or_None, advisory_or_None) for the page currently loaded in `chrome`: a crawl under its
    own custom animation that steps 3+ whole pixels is an ERROR (matches the Remotion tier's rule via
    the SAME judge_glide/glide_level); 1-2 steps is a WARN. Reused, not re-derived: the judgment is
    text_safe_qa's; this only supplies the per-frame census."""
    import tempfile
    import text_safe_qa as _tsq
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    n_frames = max(1, round(float(duration) * float(fps or 30)))
    # RE-SEAT THE PAGE AT p=0 FIRST. Whatever loaded it last (the resting p=1.0 shot) let seek.js rebase every
    # reveal's animation-delay to `delay - total`, so read from there every reveal had already finished and the
    # census measured ambient animation only — a component's (or a page's own) moving text was never seen.
    # `url`, when given, is the page on the timeline that SHIPS (cue mode for a cued page — run() passes it);
    # otherwise the page currently loaded, on whichever timeline its own query names.
    href = url or chrome._cmd("Runtime.evaluate", {"expression": "location.href", "returnByValue": True},
                              chrome.sid)["result"]["result"]["value"]
    u = urlsplit(href)
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if k != "p"] + [("p", "0")]
    with tempfile.TemporaryDirectory() as tmp:
        chrome.shot(urlunsplit((u.scheme, u.netloc, u.path, urlencode(q, safe=",:"), u.fragment)),
                    os.path.join(tmp, "p0.jpg"))
    frames = _glide_census(chrome, n_frames)
    runs = _tsq.judge_glide(frames)
    level, worst = _tsq.glide_level(runs)
    if level == "clean" or not worst:
        return None, None
    worst_run = max(worst, key=lambda r: r["steps"])
    msg = (f"{len(worst)} text run(s) crawl under the page's OWN animation while an axis-aligned "
          f"matrix snaps the baseline — worst: {_tsq._describe_run(worst_run)} (give it the baseline "
          f"unlock — base.css's matrix(1,.0009765625,0,1,0,0) trick — or mark it data-type-steps=\"…\" "
          f"if the stepping is intentional)")
    return (msg, None) if level == "error" else (None, msg)


# ── THE SYNC AUDIT, on the frames that ship ─────────────────────────────────────────────────────────
#
# Does each piece of on-screen text become readable when the narration says it? (scripts/sync_qa.py holds the
# matching and the thresholds; the remotion tier asks the same question in text_safe_qa --sync.) The census
# above is read at exactly the progress values render_html CAPTURES (scenes.html_capture_plan), and a frame the
# render fills by copying an earlier capture gets that capture's census — so a reveal that happens between
# captures is seen when the film shows it, not when the page would have.
def _sync_records(chrome, out_dir, s, meta, url):
    """[record] for one page (sync_qa.measure_beat), or None when there is no timeline yet (pre-tts)."""
    import sync_qa as _sq
    dur = s.get("duration")
    if not isinstance(dur, (int, float)) or dur <= 0:
        return None
    fps = meta.get("fps", 30)
    frames = max(1, round(float(dur) * fps))
    pmeta = dict(meta, _out=out_dir, _narration=_sq.narration_of(s), _slide=s)
    plan = scenes.html_capture_plan(s.get("props") or {}, pmeta, frames, s.get("index"))
    base = url + (f"?p=0&cues={plan['cue_param']}&dur={frames / float(fps):.3f}" if plan["cue_param"] is not None
                  else "?p=0")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        chrome.shot(base, os.path.join(tmp, "p0.jpg"))
    plist = [p for _i, p in plan["shots"]]
    r = chrome._cmd("Runtime.evaluate", {"expression": _GLIDE_JS_TMPL % (len(plist), json.dumps(plist)),
                                         "returnByValue": True}, chrome.sid)
    raw = json.loads(r["result"]["result"]["value"])
    at = {i: raw[str(n)]["lines"] for n, (i, _p) in enumerate(plan["shots"])}
    src = dict(plan["copies"])
    samples = []
    for i in range(frames):
        j = i
        while j in src:
            j = src[j]
        samples.append((i / float(fps), at.get(j, [])))
    spoken, _src = _sq.spoken_units(_sq.narration_of(s), _sq.words_for(out_dir, s), dur)
    return _sq.measure_beat(samples, spoken) if spoken else []


def _sync_verdict(records):
    """(issues, advisories) from a page's sync records — a LATE past sync_qa.LAG_ERROR blocks."""
    import sync_qa as _sq
    issues, adv = [], []
    for rec in records or []:
        lv = _sq.level(rec)
        if lv == "error":
            issues.append("LATE text: " + _sq.describe(rec) + " — anchor its reveal to the words that name it "
                          "(data-cue=\"…\" + data-cue-index on that element) — or run "
                          "`python3 scripts/cue_pages.py <out_dir> --write --retarget` to propose them")
        elif lv == "warn":
            adv.append("late text: " + _sq.describe(rec))
        elif lv == "early":
            adv.append("EARLY text (gives the line away): " + _sq.describe(rec))
    return issues, adv


BAND_TOL = 0.035          # normalized frame-height slack for "the same line"
BAND_SHARE = 0.6          # share of pages on one line before it reads as a shared envelope

def _band_uniformity_note(bands):
    """Deck-level CONTENT-BAND uniformity. `bands` = [(scene, ctop, cbot)] normalized to frame height.

    A centroid can look varied while every page still occupies the SAME rectangle — content starting
    and ending on the same two lines, page after page. That shared envelope, not "everything is
    centered", is what actually reads as templated: a deck measured 12-left/8-mid/7-right horizontally
    still felt like one page because 21/29 of its pages ended at cbot ~0.82. Report the shared EDGE so
    the fix is concrete (give N beats a different band) rather than a vague "vary the composition"."""
    if len(bands) < 6:
        return None
    for edge, name in ((2, "bottom"), (1, "top")):
        vals = [b[edge] for b in bands]
        best, at = 0, None
        for v in vals:
            k = sum(1 for w in vals if abs(v - w) <= BAND_TOL)
            if k > best:
                best, at = k, v
        if best / len(bands) > BAND_SHARE:
            return (f"content-band uniformity: {best}/{len(bands)} pages end their content on the same {name} "
                    f"line (~{at:.2f} of frame height) — the pages differ but the ENVELOPE does not, which is "
                    f"what reads as templated. Give ~1/3 of beats a genuinely different band (a sparse beat "
                    f"that stops high with void below; a beat that sits low on the baseline), driven by what "
                    f"the beat says — not a uniform nudge")
    return None


def _shipped_url(out_dir, s, url, p=1.0):
    """URL for the frame that ACTUALLY SHIPS — seek.js in CUE mode (?cues=&dur=) at p=1.0, which is
    the render's real last frame.

    Why this exists: with no ?cues= seek.js runs in blind-ENVELOPE mode, where total = max(delay +
    animation-duration) over the reveals, so p=1.0 means "every animation has finished" BY
    CONSTRUCTION. The blind sheet therefore CANNOT show an animation the scene cut off mid-flight
    (a connector frozen in mid-air) — in its coordinate system that state does not exist. Mirrors
    the cue-param construction in scenes.render_html; returns None when the scene isn't cued (blind
    mode is then already the truth) or the durations aren't in yet (pre-tts)."""
    dur = s.get("duration")
    if not isinstance(dur, (int, float)) or dur <= 0:
        return None
    # THE RENDER'S OWN CUES (scenes.html_capture_plan), not a mirror of them: this used to re-derive the
    # cue list with only the dur-0.5 clamp, so the day render_html learned to LEAD a late cue past its
    # out-transition the sweep would have shown a frame the film no longer has.
    try:
        meta = (json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {})
    except (OSError, ValueError):
        meta = {}                                     # the meta defaults (30 fps, a 0.2 s dip) — what render uses
    try:
        fps = meta.get("fps", 30)
        frames = max(1, round(float(dur) * fps))
        plan = scenes.html_capture_plan(s.get("props") or {},
                                        dict(meta, _out=out_dir, _narration=s.get("narration") or "", _slide=s),
                                        frames, s.get("index"))
    except Exception:
        return None
    if plan["cue_param"] is None:
        return None
    return url + f"?p={p}&cues={plan['cue_param']}&dur={frames / float(fps):.3f}"


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
    blind_scenes = []                     # swept in BLIND mode: no cue timeline available (pre-tts)
    uncued_scenes = []                    # timed, but the page carries no data-cue anchors
    centroids = []                        # (scene, cx, cy) normalized content centroids, for silhouette repetition
    bands = []                            # (scene, ctop, cbot) normalized content BAND, for band uniformity
    sync_by_scene, sync_seconds = {}, 0.0 # the sync audit: {scene label: [records]} (scripts/sync_qa.py)
    glide_seconds, glide_checked = 0.0, 0 # cost accounting — reported in the summary line (glide-skipped
                                           # scenes are the SAME set as blind_scenes below — no duration yet)
    try:
        for s in html:
            idx = s.get("index")
            page = (s.get("props") or {}).get("html")
            if not page:
                continue
            from urllib.parse import quote
            # percent-encode: an unquoted '#'/'%' truncates the file:// URL — Chrome loads its error
            # page and the probe returns a clean verdict for a page that never rendered (see snapshot.py)
            url = "file://" + quote(os.path.abspath(os.path.join(out_dir, page)))
            # THE SWEEP IS THE REAL FILM. Without ?cues= seek.js runs in blind-ENVELOPE mode, where
            # total = max(delay + animation-duration) — a timeline that NEVER SHIPS. Every p in that
            # mode is a fiction: p=0 is not the scene's opening, and p=1.0 means "all animations
            # finished" by construction. Sweeping the CUE timeline instead makes the contact sheet an
            # actual filmstrip: p=0 is the frame the viewer sees while the narration's first words
            # play, and p=1.0 is the frame that ships. Same shot count as before — strictly more
            # information (the old separate shipped shot is now just the last frame of the sweep).
            cued = _shipped_url(out_dir, s, url, p=1.0) is not None
            if not cued:
                # two different reasons, two different fixes: no duration yet (pre-tts) means the sweep
                # is a fiction until tts.py runs; a timed page with no data-cue anchors is swept exactly
                # as it renders (its reveals run on their own clock), so there is nothing to wait for
                dur = s.get("duration")
                if isinstance(dur, (int, float)) and dur > 0:
                    uncued_scenes.append(idx)
                else:
                    blind_scenes.append(idx)
            # A PAGE OF POINTS WITH NO CUES is an ERROR here as in validate (validate.uncued_reveal_points):
            # its reveals keep the page's own paced clock, whatever the narration is saying
            import validate as _val
            try:
                _src_html = open(os.path.join(out_dir, page), encoding="utf-8", errors="replace").read()
            except OSError:
                _src_html = ""
            _n_uncued = _val.uncued_reveal_points(_src_html)
            uncued_issue = (_val.uncued_points_message("page", _n_uncued)
                            if _n_uncued >= _val.REVEAL_POINT_MIN else None)
            frames, ok, rvis, rtot = [], True, [], 0
            for p in ps:
                fp = os.path.join(kf, f"scene_{idx:02d}_p{int(p*100):03d}.png")
                shot_url = (_shipped_url(out_dir, s, url, p=p) if cued else url + f"?p={p}")
                try:
                    if chrome:
                        chrome.shot(shot_url, fp)                 # CDP: (url, out_path)
                        rc = _reveal_count(chrome)                # count visible reveals at THIS frozen state
                        rvis.append(rc["vis"]); rtot = max(rtot, rc["tot"])
                    else:
                        scenes._chrome_shot(shot_url, fp, W, H, meta)
                    frames.append(Image.open(fp))
                except Exception as e:
                    report.append({"scene": idx, "status": "ERROR", "issues": [f"render failed: {e}"]})
                    errors += 1; ok = False; break
            if not ok or not frames:
                continue
            _sheet(frames, os.path.join(kf, f"scene_{idx:02d}.png"))
            final = frames[-1]; shipped = frames[-1] if cued else None
            issues, advisories = [], []       # issues block the gate; advisories are non-blocking
            if uncued_issue:
                issues.append(uncued_issue)
            probed = True                     # False = nothing was measured; never report that as "ok"
            if chrome:
                try:
                    # GEOMETRY is measured on the AUTHORED RESTING state (blind p=1.0), not on the
                    # shipped frame: overflow/clip must judge the layout the author wrote. On the cue
                    # timeline an entrance can still be mid-flight at the cut, and .reveal-up's
                    # transform would shift a box and report a phantom overflow. One extra blind shot
                    # here replaces the separate shipped shot the sweep now provides — net shot count
                    # per scene is unchanged.
                    if cued:
                        chrome.shot(url + "?p=1.0", os.path.join(kf, f"scene_{idx:02d}_resting.png"))
                    info = _dom_probe(chrome)
                    # BLANK only when there is genuinely nothing rendered — not merely little text. A single-
                    # glyph hero ('7', a lone '%', one CJK char) or an icon-only diagram has a real content
                    # bbox; a full-bleed visual sets bleed. Flag only empty text AND no visible content box.
                    _blank = _blank_issue(info)
                    if _blank:
                        issues.append(_blank)
                    issues.extend(_geometry_issues(info, meta, W, H))   # overflow + intra-box clip + caption occlusion
                    if info.get("encl", 0) > 0:
                        advisories.append(f"{info['encl']} text block(s) SPILL past an enclosure "
                                          f"(e.g. \u300c{info.get('enclEx','')}\u300d) — a ring asserts "
                                          f"\u201cthese ones, not the others\u201d; text crossing its edge "
                                          f"breaks that claim. Enlarge the enclosure or shrink/move the text")
                    if info.get("centered", 0) > 0:
                        advisories.append(f"{info['centered']} centered running paragraph(s) — "
                                          "left-align body text for scanning (studios do)")
                    # DECODABILITY: an empty bordered box with no text and no declared role is "mystery
                    # furniture" — a viewer can't name what it is. Label it, mark its idiom with
                    # data-role="…", or remove it (composition needs = meaning or deliberate whitespace).
                    if info.get("mystery", 0) > 0:
                        advisories.append(f"{info['mystery']} empty bordered box(es) with no text/role "
                                          f"(e.g. '{info.get('mystery_ex', '')}') — mystery furniture: every "
                                          "element must be viewer-decodable in ~1s; label it, add data-role, "
                                          "or remove it (html-pages.md Decodability rule)")
                    # ORDER: sibling edges off by 5-22px read as sloppiness, not intent — snap to a
                    # shared guide or make the offset clearly deliberate. One pair may be a false
                    # positive (baseline type); two or more is a pattern.
                    # CROWDING: two sibling boxes nearly TOUCHING (gap -8..12px with real cross-axis
                    # overlap) read as a collision, not a layout — give elements breathing room.
                    # Deliberate deep overlaps (stacked planes) sit far outside the near-touch band.
                    if info.get("crowd", 0) > 0:
                        advisories.append(f"{info['crowd']} sibling box pair(s) nearly TOUCHING "
                                          f"(gap within -8..12px, e.g. under '{info.get('crowd_ex', '')}') — "
                                          "elements need breathing room; add margin or move one "
                                          "(html-pages.md Alignment & order discipline)")
                    if info.get("nearmiss", 0) >= 2:
                        advisories.append(f"{info['nearmiss']} nearly-aligned sibling edge pair(s) (off by "
                                          f"5-22px, e.g. under '{info.get('nearmiss_ex', '')}') — snap to a "
                                          "shared guide or make the offset clearly deliberate "
                                          "(html-pages.md Alignment & order discipline)")
                    # 9:16 fill (html-pages.md "fill the column"): content should span >=~70% of
                    # the zone between the stage top padding and the caption band (_fill_zone). Below 60% is advisory; below HALF
                    # the page ships with an empty lower half under a top-anchored stack, which the
                    # viewer reads as a broken page (a smoke film shipped 45% on an advisory), so it
                    # blocks. A full-bleed .bg-photo hero provides visual fill outside .stage, so
                    # heroes never warn.
                    if meta.get("aspect") == "9:16" and info.get("cbot", -1) > info.get("ctop", 0):
                        fill = _fill_fraction(info, W, H)
                        rep_fill = round(100 * min(1.0, fill))
                        if fill < 0.60 and not info.get("bleed"):
                            (issues if fill < 0.50 else advisories).append(
                                f"fills only {rep_fill}% of the 9:16 zone — scale type up / distribute "
                                "down / add a lower-zone visual, or opt into `class=\"stage fill\"` "
                                "(vertical.css) for a one-line lever (html-pages '9:16 vertical pages')")
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
                    # content centroid (normalized) for the deck-level silhouette-repetition advisory
                    if info.get("cright", -1) > info.get("cleft", 0) and info.get("cbot", -1) > info.get("ctop", 0):
                        # AREA-WEIGHTED centroid where available: the bbox midpoint is ~0.5 for any
                        # page whose content spans the frame, so it called a deck "all centred" whose
                        # visual weight was genuinely 12-left/8-mid/7-right. Fall back to the midpoint
                        # only when nothing carried measurable ink.
                        cx = (info["wcx"] / W if info.get("wcx", -1) >= 0
                              else ((info["cleft"] + info["cright"]) / 2) / W)
                        cy = (info["wcy"] / H if info.get("wcy", -1) >= 0
                              else ((info["ctop"] + info["cbot"]) / 2) / H)
                        centroids.append((idx, cx, cy))
                        bands.append((idx, info["ctop"] / H, info["cbot"] / H))
                except Exception as e:
                    # A probe that THREW measured nothing. Reporting "ok" here made an unverified
                    # scene indistinguishable from a scene that passed all four geometry checks.
                    probed = False
                    advisories.append(f"UNVERIFIED — DOM probe failed ({type(e).__name__}); "
                                      f"geometry/blank checks did not run for this page")
                    if _is_blank(final):
                        issues.append("BLANK at p=1 (reveal never fired / broken page)")
            else:
                probed = False
                if _is_blank(final):
                    issues.append("BLANK at p=1 (reveal never fired / broken page)")
            # TYPE-GLIDE CENSUS: a page's OWN custom animation ([data-ambient], a per-page <style>
            # @keyframes) crawling text under an axis-aligned matrix — unchecked by the geometry probe
            # above (that measures ONE resting frame; this reads consecutive frames). Needs a real
            # duration (post-tts) for a real frame count, same gate as the sweep itself.
            if chrome:
                dur = s.get("duration")
                if isinstance(dur, (int, float)) and dur > 0:
                    try:
                        _t0 = time.time()
                        g_issue, g_warn = _glide_issue(chrome, dur, meta.get("fps", 30),
                                                       url=(_shipped_url(out_dir, s, url, p=0) if cued
                                                            else url + "?p=0"))
                        glide_seconds += time.time() - _t0
                        glide_checked += 1
                        if g_issue:
                            issues.append(g_issue)
                        if g_warn:
                            advisories.append(g_warn)
                    except Exception as e:
                        advisories.append(f"type-glide census failed ({type(e).__name__}) — crawl under "
                                          f"the page's own animation was NOT checked for this page")
                # else: no duration yet — covered by the blind_scenes deck note below (same gate)
                if isinstance(dur, (int, float)) and dur > 0:
                    try:
                        _t0 = time.time()
                        recs = _sync_records(chrome, out_dir, s, meta, url)
                        sync_seconds += time.time() - _t0
                        if recs is not None:
                            sync_by_scene["scene %02d" % idx] = recs
                            s_issues, s_adv = _sync_verdict(recs)
                            issues.extend(s_issues)
                            advisories.extend(s_adv)
                    except Exception as e:
                        advisories.append(f"sync audit failed ({type(e).__name__}: {e}) — when this page's text "
                                          f"appears against the narration was NOT checked")
            # THE OPENING. frames[0] is now the real t=0 frame — what the viewer actually sees while
            # the narration's first words play, and (with a dip) what the transition lands on. A page
            # whose first reveal is anchored to a phrase spoken partway through opens on nothing; the
            # doctrine has always called this "reads as broken" but no gate could see it, because in
            # blind-envelope mode p=0 was a fiction. Only meaningful on the cue timeline.
            if cued and frames and _is_blank(frames[0]):
                # A page still empty a QUARTER of the way in has left the viewer on black for
                # seconds while the voice talks — the doctrine's "reads as broken". A page blank only
                # at t=0 has merely opened on a beat of black before its line fades in, which is a
                # legitimate choice, so that one is said out loud but never blocks.
                _late = next((i for i, pp in enumerate(ps) if pp >= 0.2), None)
                if _late is not None and _late < len(frames) and _is_blank(frames[_late]):
                    issues.append(f"BLANK through {int(ps[_late]*100)}% of the scene — the viewer is "
                                  f"held on an empty frame for seconds while the narration plays; "
                                  f"anchor the first reveal to an OPENING phrase, or give the page "
                                  f"uncued header chrome that shows immediately")
                else:
                    advisories.append("opens on an empty frame at t=0 (its first reveal is cued, not "
                                      "immediate) — fine as a deliberate beat of black, but check it "
                                      "reads that way rather than as a late page")
            last_frames.append(shipped or final)   # all.png shows shipped frames where we have them
            if issues:
                errors += 1
            if advisories:
                warns += 1
            report.append({"scene": idx, "issues": issues, "advisories": advisories, "probed": probed,
                           "status": "FAIL" if issues else ("WARN" if advisories else
                                                            ("ok" if probed else "UNVERIFIED"))})
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

    # Deck-level CONTENT-BAND uniformity (advisory). A centroid can look varied while every page still
    # occupies the SAME rectangle — content starting and ending on the same two lines, page after page.
    # That shared envelope, not "everything is centered", is what actually reads as templated: a deck
    # measured 12-left/8-mid/7-right horizontally still felt like one page because 22/29 of its pages
    # ended at cbot 0.79-0.85. Report the shared EDGE so the fix is concrete (give N beats a different
    # band) rather than the vague "vary the composition".
    if blind_scenes:
        # Without per-scene `duration` (i.e. before tts.py runs) there is no cue timeline, so the
        # sweep necessarily falls back to the BLIND envelope — where p is a fraction of
        # max(delay+animation-duration), NOT of the scene. Every page looks "flooded by p=0.25" in
        # that mode BY CONSTRUCTION. Say so loudly: a reviewer who reads these strips as motion
        # evidence will conclude the whole deck shares one motion signature, which is an artifact.
        deck_notes.append(f"MOTION NOT JUDGEABLE YET: {len(blind_scenes)} scene(s) were swept in "
                          f"BLIND-envelope mode because they carry no duration (run tts.py first). "
                          f"In blind mode p is a fraction of the animation envelope, not of the scene, "
                          f"so every page appears fully drawn early — do NOT read these strips as "
                          f"motion personality evidence; re-run this after tts.py for the real timeline")
    if uncued_scenes:
        deck_notes.append(f"{len(uncued_scenes)} scene(s) ({', '.join(str(i) for i in uncued_scenes)}) carry no "
                          f"data-cue anchors, so their reveals run on the page's own animation clock, not on "
                          f"the narration — the sweep shows them exactly as they render. Add data-cue "
                          f"anchors if a reveal should land on a spoken word (`python3 scripts/cue_pages.py <out_dir>` "
                          f"proposes them)")
    note = _band_uniformity_note(bands)
    if note:
        deck_notes.append(note)

    # FAIL-CLOSED on UNVERIFIED: a scene whose box-geometry floor could NOT be probed (no CDP, or a per-scene
    # probe failure) is NOT a passing scene — SKILL.md's delivery criterion says so, and the sibling snapshot.py
    # already exits 3 here. Reporting 0 when the geometry gate measured NOTHING is a fail-open the caller can't see.
    unverified = [r for r in report if not r.get("probed")]
    status = "OK" if (errors == 0 and not unverified) else ("UNVERIFIED" if (errors == 0 and unverified) else "ISSUES")
    import sync_qa as _sq
    sync_sum = _sq.summarize(sync_by_scene)
    if as_json:
        print(json.dumps({"errors": errors, "warns": warns, "report": report,
                          "deck_advisories": deck_notes, "cdp": bool(chrome),
                          "sync": {"beats": sync_by_scene, "summary": sync_sum}}, indent=2, ensure_ascii=False))
    else:
        for r in report:
            mark = {"FAIL": "✗", "WARN": "!"}.get(r["status"], "✓")
            notes = (r.get("issues") or []) + (r.get("advisories") or [])
            extra = ("  " + "; ".join(notes)) if notes else ""
            print(f"  {mark} scene {r['scene']:02d} [{r['status']}]{extra}")
        for dn in deck_notes:
            print(f"  ! deck  {dn}")
        mode = "DOM+shots" if chrome else "shots-only (no CDP → overflow/centered/type-glide unchecked)"
        glide_note = (f"; glide census {glide_seconds:.2f}s/{glide_checked} page(s)"
                      if glide_checked else "")
        if sync_by_scene:
            print(f"  [sync] {sync_sum['elements']} text element(s) matched to the voice on "
                  f"{len(sync_by_scene)} page(s): {sync_sum['late_error']} late ERROR(s) (>{_sq.LAG_ERROR}s), "
                  f"{sync_sum['late_warn']} late WARN(s), {sync_sum['early']} early · worst lag "
                  f"{sync_sum['worst_lag']:+.2f}s · {sync_seconds:.1f}s")
        print(f"[keyframe_qa] {status}  {len(report)} html page(s), "
              f"{errors} issue(s), {warns + len(deck_notes)} advisory(ies) [{mode}]{glide_note}; sheets -> {kf}/  "
              f"(open all.png to eyeball tofu/theme/reveals)")
    if errors:
        return 1
    if unverified:
        if not as_json:
            print(f"  [keyframe_qa] FAIL: {len(unverified)} scene(s) UNVERIFIED — the box-geometry floor "
                  f"(overflow/clip/caption-zone) was NOT probed ({'no CDP' if not chrome else 'probe error'}); "
                  f"an unverified scene is not a passing scene. Fix Chrome/CDP (set meta.chrome_path) and re-run.")
        return 3
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--p", type=int, default=5, help="number of evenly-spaced p-values (default 5)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    n = max(2, a.p)
    ps = [round(i / (n - 1), 3) for i in range(n)]
    sys.exit(run(a.out_dir, ps=ps, as_json=a.json))
