#!/usr/bin/env python3
"""film_copy_qa — every word a director-path film SHOWS must come from its sources, or be declared as illustration.

    python3 scripts/film_copy_qa.py <film_dir> [--page film.html] [--every 0.5] [--frames A-B] [--json]

Loads film.html (scripts/_filmpage.py), records every string the page draws on a canvas (fillText / strokeText,
from the first script on), and steps window.seek(t) through the film collecting the VISIBLE text of the page. Each
string is checked against the film's corpus: the docs (`input/sources/`, `sources/`), `script.json` and `brief.json`.
A string is SOURCED when, normalised (case, quotes, dashes, arrows, spacing, end punctuation), it occurs in that
corpus. Anything else is UNSOURCED, unless `<film_dir>/copy_ok.json` lists it with a reason:
    {"Pipeline → drafts": "the film's own label for the handoff (illustration of the docs' example task)"}
— a ledger the user can read, not a silencer: an entry with no reason fails.

WHY. brief_qa checks the SPOKEN claims; nothing checked the words drawn on screen. A Grok Bot film showed "To: 5 account
contacts", "1 of 5" and invented terminal commands on its product UI; every gate was green (2026-11-18).
Strings of fewer than two letters (a "$" prompt, a digit) are not judged; a letter in its own inline element (a query
typed a <span> per letter, the Airbnb film 2026-11-25) is judged as the line it belongs to.
Exit 0 every shown string sourced or declared, 1 unsourced strings, 2 usage error or the page failed to load.
"""
import glob
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

_USAGE = "usage: film_copy_qa.py <film_dir> [--page film.html] [--every 0.5] [--frames A-B] [--json]"

CANVAS_HOOK = r"""
(() => { const seen = window.__canvasText = new Set();
  for (const C of [window.CanvasRenderingContext2D, window.OffscreenCanvasRenderingContext2D]) { if (!C) continue;
    for (const m of ['fillText', 'strokeText']) { const f = C.prototype[m];
      C.prototype[m] = function (txt) { try { seen.add(String(txt)); } catch (e) {} return f.apply(this, arguments); }; } } })();
"""

_DOM_TEXT = r"""
(() => { const out = [], lines = new Set();
  const vis = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false; } return true; };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) { const s = n.textContent.trim(); if (!s) continue;
    const el = n.parentElement; if (!el || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName) || !vis(el)) continue;
    const r = el.getBoundingClientRect(); if (r.width < 1 || r.bottom < 0 || r.right < 0 || r.top > innerHeight || r.left > innerWidth) continue;
    if ((s.match(/\p{L}/gu) || []).length < 2) {        // typed a letter per element: judge the line it belongs to
      let b = el; while (b.parentElement && getComputedStyle(b).display === 'inline') b = b.parentElement;
      if (b !== el && !lines.has(b)) { lines.add(b); const t = b.innerText.replace(/\u00a0/g, ' ').trim(); if (t) out.push(t); }
      continue; }
    out.push(el.innerText && el.childNodes.length === 1 ? el.innerText.trim() : s); }
  return out; })()
"""


def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[‘’ʼ`]", "'", s)
    s = re.sub(r"[“”«»]", '"', s)
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"[←-⇿⟶➔]|->", " ", s)        # arrows read as a separator
    s = re.sub(r"[*_#>|]", " ", s)                                # markdown/table marks in the docs
    s = re.sub(r"\s+", " ", s).strip()
    return s.strip(" .,:;!?…\"'()[]")


def corpus(d):
    parts = []
    for root in ("input/sources", "sources"):
        for p in glob.glob(os.path.join(d, root, "**", "*"), recursive=True):
            if os.path.isfile(p) and p.rsplit(".", 1)[-1].lower() in ("txt", "md", "json", "html", "csv"):
                parts.append(open(p, encoding="utf-8", errors="replace").read())
    for name in ("script.json", "brief.json"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            parts.append(open(p, encoding="utf-8").read())
            try:  # the JSON's own strings, unescaped
                def walk(o):
                    if isinstance(o, str):
                        parts.append(o)
                    elif isinstance(o, dict):
                        for v in o.values():
                            walk(v)
                    elif isinstance(o, list):
                        for v in o:
                            walk(v)
                walk(json.load(open(p, encoding="utf-8")))
            except ValueError:
                pass
    return " \n ".join(norm(x) for x in parts)


def excerpt(n, sentences):
    """True when n's words occur IN ORDER inside one corpus sentence, with at most 12 words left out: a quote shortened
    with an ellipsis ("Owns ... review-ready outreach"), not a paraphrase."""
    words = re.findall(r"[^\W_][\w'-]*", n)
    if len(words) < 2:
        return False
    for sent in sentences:
        if words[0] not in sent:
            continue
        toks = re.findall(r"[^\W_][\w'-]*", sent)
        for start in (i for i, w in enumerate(toks) if w == words[0]):
            j, skipped = start + 1, 0
            for w in words[1:]:
                while j < len(toks) and toks[j] != w:
                    j += 1
                    skipped += 1
                if j >= len(toks) or skipped > 12:
                    break
                j += 1
            else:
                return True
    return False


def judge(strings, corp, ok):
    """strings: {text: (where, first_t)}. Returns (unsourced [(text, where, t)], bad_ok [text])."""
    okn = {norm(k): v for k, v in ok.items()}
    bad_ok = [k for k, v in ok.items() if not (isinstance(v, str) and v.strip())]
    sentences = [x for x in re.split(r"[.!?\n]+", corp) if x.strip()]
    norms = {norm(k) for k in strings}
    out = []
    for s, (where, t) in sorted(strings.items(), key=lambda kv: (kv[1][1] if kv[1][1] is not None else -1, kv[0])):
        n = norm(s)
        if len(re.findall(r"[^\W\d_]", n)) < 2:
            continue
        if any(o != n and o.startswith(n) for o in norms):   # a typing animation's partial text: judged as the whole
            continue
        if n in corp or excerpt(n, sentences):
            continue
        if n in okn and isinstance(okn[n], str) and okn[n].strip():
            continue
        out.append((s, where, t))
    return out, bad_ok


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "every", "frames"), switches=("json",), usage=_USAGE)
    span = _c.frame_span(argv)
    vals = {k: _c.argflag(argv, k, None) for k in ("page", "every", "frames")}
    args = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    page = vals["page"] or "film.html"
    if not os.path.isfile(os.path.join(d, page)):
        print("film_copy_qa: no page at %s" % os.path.join(d, page), file=sys.stderr)
        return 2
    every = float(vals["every"] or 0.5)
    n = _fp.film_frames_count(d, 30)
    if not n:
        print("film_copy_qa: no _plan.json \"frames\" or timeline.json \"duration\"", file=sys.stderr)
        return 2
    okp = os.path.join(d, "copy_ok.json")
    ok = json.load(open(okp, encoding="utf-8")) if os.path.isfile(okp) else {}
    corp = corpus(d)
    port, srv = _fp.serve(d)
    strings = {}
    try:
        p = _fp.FilmPage(port, page, init_script=CANVAS_HOOK)
        try:
            t, t_end = (span[0] / 30.0, min(n, span[1]) / 30.0) if span else (0.0, n / 30.0)
            while t < t_end:
                p.seek(t)
                for s in p.ev(_DOM_TEXT) or []:
                    strings.setdefault(s, ("page", round(t, 2)))
                # app screens laid out as HTML (Stage3D.screen) and shown right now: their words, as the viewer reads them
                for r in p.ev("(window.Stage3D && Stage3D.screenTexts) ? Stage3D.screenTexts() : []", True) or []:
                    for s in r["texts"]:
                        strings.setdefault(s, ("screen " + r["screen"], round(t, 2)))
                t += every
            for s in p.ev("[...(window.__canvasText || [])]") or []:
                if s.strip():
                    strings.setdefault(s.strip(), ("canvas", None))
        finally:
            p.close()
    except _fp.PageError as e:
        print("film_copy_qa: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    bad, bad_ok = judge(strings, corp, ok)
    if "--json" in argv:
        print(json.dumps({"unsourced": [{"text": s, "where": w, "t": t} for s, w, t in bad], "ok_without_reason": bad_ok},
                         ensure_ascii=False))
    else:
        for s, w, t in bad:
            print("UNSOURCED  %-6s %s  %r" % (w, "t=%.1fs" % t if t is not None else "      ", s))
        for k in bad_ok:
            print("NO REASON  copy_ok.json lists %r without a reason" % k)
        print("[film_copy_qa] %s  %d shown string(s), %d unsourced%s" % (
            "OK" if not bad and not bad_ok else "RED", len(strings), len(bad),
            "" if not bad else " (source them, grey them out, or declare them in copy_ok.json with a reason)"))
    return 1 if bad or bad_ok else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
