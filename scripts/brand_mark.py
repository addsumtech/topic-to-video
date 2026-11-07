#!/usr/bin/env python3
"""Is a brand mark the product's own? Read its letters.

    python3 scripts/brand_mark.py <out_dir>          # read every mark the film uses; record what each says

WHY. The WorkBuddy film (2026-11-07) took refs/logo.DFsvaNxA.svg, fetched from the product's own docs site, as
WorkBuddy's mark and derived the whole palette from it. It was CodeBuddy's — a sibling product's, served by the same
site — and nothing noticed until a contact sheet showed "CODE-BUDDY". A file's name and the page it came from do not
say whose mark it is. The mark's own letters do.

WHAT A MARK IS. Every file under assets/brand/, meta.brand.logo / logo_dark, and any image under assets/, refs/,
media/ or workshop/assets/ named as one (logo, logomark, wordmark, lockup, app icon) or whose sidecar says it
is one (`"use": "brand mark / …"` — the WorkBuddy mark's file had no mark word in its name). A mark that is neither
named nor labelled is not found: label what you fetch.

WHICH ONES COUNT. The marks the film USES: the declared brand logo; a file named inside a string of the board or of
the workshop's code (a comment that names a file to warn against it is not a use); an svg whose path data was
pasted into the workshop's code (how the WorkBuddy mark reached the film: inlined into wbKit.ts).

WHOSE NAME. A mark is read against the name it is used AS: a third-party mark the film shows on purpose (Gmail as a
connected app) says so in its sidecar, `"brand": "Gmail"`; every other mark must spell the product's name.

WHAT IS RECORDED. The mark is drawn on a light and on a dark ground (an svg by headless Chrome, a raster by PIL),
read by screen_text.recognize (macOS Vision, else tesseract), and its sidecar <file>.json gets
`identity: {sha256, name, reads, verdict}` — `match`, `mismatch`, or `no-text` (a symbol with no letters: someone who
knows whose it is writes `identity.confirmed` in their own words). validate refuses a used mark that was never read,
was changed since, was read against another name, names another product, or is an unconfirmed symbol.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

TAG = "[brand_mark]"
MARK_NAME = re.compile(r"(?:^|[-_.\s])(?:logo|logomark|wordmark|lockup|app[-_\s]?icon)(?:[-_.\s]|$)", re.I)
MARK_USE = re.compile(r"\b(?:brand[ -]?mark|logo|logomark|wordmark|lockup|app[ -]?icon)\b", re.I)
IMAGE_EXT = (".svg", ".png", ".jpg", ".jpeg", ".webp")
MARK_DIRS = ("assets", "refs", "media", os.path.join("workshop", "assets"))
CODE_EXT = (".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".json")
FUZZY = 0.85          # one OCR slip in a 9-letter name (W0RKBUDDY) passes; CODEBUDDY against WORKBUDDY (0.78) does not


# ── the name ─────────────────────────────────────────────────────────────────────────────────────────────────────
def product_name(meta):
    """The product a mark must name: meta.brand.name, else meta.product. None when the board names neither."""
    brand = (meta or {}).get("brand")
    if isinstance(brand, dict) and isinstance(brand.get("name"), str) and brand["name"].strip():
        return brand["name"].strip()
    p = (meta or {}).get("product")
    return p.strip() if isinstance(p, str) and p.strip() else None


def _norm(s):
    """Case, width, spaces and punctuation gone; letters, digits and CJK kept."""
    s = unicodedata.normalize("NFKC", s or "").casefold()
    return "".join(ch for ch in s if ch.isalnum())


def matches(name, reads):
    """Do the mark's read lines spell `name`? Lines are joined (a stacked wordmark reads as two lines); a window of
    the read text as long as the name must be at least FUZZY like it."""
    n, text = _norm(name), _norm("".join(reads or []))
    if not n or not text:
        return False
    if n in text:
        return True
    L = len(n)
    best = 0.0
    for i in range(0, max(1, len(text) - L + 1)):
        best = max(best, difflib.SequenceMatcher(None, n, text[i:i + L]).ratio())
    return best >= FUZZY


def verdict(name, reads):
    """match | mismatch | no-text. A mark whose read text carries no letter (a date in a calendar icon, a prompt
    glyph) is a symbol: only letters can name a product."""
    if not any(ch.isalpha() for ch in "".join(reads or [])):
        return "no-text"
    return "match" if matches(name, reads) else "mismatch"


# ── which files are marks, and which the film uses ──────────────────────────────────────────────────────────────
def _board(out_dir):
    try:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _declared(meta):
    brand = (meta or {}).get("brand")
    if not isinstance(brand, dict):
        return []
    return [os.path.normpath(p) for p in (brand.get("logo"), brand.get("logo_dark")) if isinstance(p, str) and p]


def _labelled(path):
    """Does the file's sidecar call it a mark?"""
    try:
        with open(path + ".json", encoding="utf-8") as fh:
            side = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(side, dict):
        return False
    return any(isinstance(side.get(k), str) and MARK_USE.search(side[k]) for k in ("use", "kind", "role", "what"))


def candidates(out_dir):
    """Every brand mark in the film's folders, as paths relative to out_dir."""
    out = set(p for p in _declared((_board(out_dir).get("meta") or {})) if os.path.isfile(os.path.join(out_dir, p)))
    for sub in MARK_DIRS:
        root = os.path.join(out_dir, sub)
        for dp, dn, fn in os.walk(root):
            dn[:] = sorted(d for d in dn if not d.startswith("."))
            rel_dir = os.path.relpath(dp, out_dir)
            in_brand = rel_dir.replace(os.sep, "/").startswith("assets/brand")
            for f in fn:
                if not f.lower().endswith(IMAGE_EXT):
                    continue
                if in_brand or MARK_NAME.search(os.path.splitext(f)[0]) or _labelled(os.path.join(dp, f)):
                    out.add(os.path.normpath(os.path.join(rel_dir, f)))
    return sorted(p.replace(os.sep, "/") for p in out)


def _code_texts(out_dir):
    ws = os.path.join(out_dir, "workshop")
    for dp, dn, fn in os.walk(ws):
        dn[:] = sorted(d for d in dn if not d.startswith(".") and d not in ("node_modules", "_stills", "assets"))
        for f in fn:
            if f.endswith(CODE_EXT):
                try:
                    with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                        yield fh.read()
                except OSError:
                    continue


_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/|\{/\*.*?\*/\}", re.S)
_STRING = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`", re.S)


def _strings_of_code(text):
    """The string literals of a source file, its comments taken out first."""
    return [m.group(0)[1:-1] for m in _STRING.finditer(_COMMENT.sub(" ", text))]


def _strings_of(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings_of(v)


def _svg_paths(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            svg = fh.read()
    except OSError:
        return []
    return [d[:48] for d in re.findall(r'\bd="([^"]{24,})"', svg)]


def used(out_dir, rel):
    """Does the film use the mark at `rel`?"""
    data = _board(out_dir)
    if os.path.normpath(rel) in _declared(data.get("meta") or {}):
        return True
    names = {rel, os.path.basename(rel)}
    strings = list(_strings_of(data))
    codes = list(_code_texts(out_dir))
    for text in codes:
        strings += _strings_of_code(text)
    if any(n in s for s in strings for n in names):
        return True
    if rel.lower().endswith(".svg"):
        snippets = _svg_paths(os.path.join(out_dir, rel))
        return any(sn in text for sn in snippets for text in codes)
    return False


# ── reading a mark ──────────────────────────────────────────────────────────────────────────────────────────────
def can_read():
    import screen_text
    import _common
    return screen_text.available() is not None and _common.find_chrome() is not None


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _draw_svg(path, work):
    """The svg drawn at ~1400 px wide on a white and on a near-black ground, inlined (an <img> can screenshot blank
    in headless Chrome before it decodes)."""
    import _common
    chrome = _common.find_chrome()
    if not chrome:
        raise RuntimeError("no Chrome to draw %s with" % path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        svg = fh.read()
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    out = []
    for name, ground in (("light", "#ffffff"), ("dark", "#16181c")):
        page = os.path.join(work, "%s.html" % name)
        with open(page, "w", encoding="utf-8") as fh:
            fh.write('<!doctype html><html><body style="margin:0;background:%s;display:flex;align-items:center;'
                     'justify-content:center;width:1600px;height:900px">'
                     '<div style="width:1400px;height:700px;display:flex;align-items:center;justify-content:center">'
                     '<style>svg{max-width:1400px;max-height:700px;width:1400px;height:auto}</style>%s</div>'
                     '</body></html>' % (ground, svg))
        png = os.path.join(work, "%s.png" % name)
        subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                        "--window-size=1600,900", "--screenshot=" + png, "file://" + page],
                       capture_output=True, timeout=60)
        if not (os.path.exists(png) and os.path.getsize(png) > 0):
            raise RuntimeError("Chrome drew nothing for %s" % path)
        out.append(png)
    return out


def _draw_raster(path, work):
    from PIL import Image
    out = []
    with Image.open(path) as im:
        im = im.convert("RGBA")
        k = max(1.0, 1200.0 / max(1, im.width))
        if k > 1:
            im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        for name, ground in (("light", (255, 255, 255, 255)), ("dark", (22, 24, 28, 255))):
            canvas = Image.new("RGBA", (im.width + 200, im.height + 200), ground)
            canvas.alpha_composite(im, (100, 100))
            png = os.path.join(work, "%s.png" % name)
            canvas.convert("RGB").save(png)
            out.append(png)
    return out


def read(path):
    """The lines of text the mark carries, read on both grounds."""
    import screen_text
    work = tempfile.mkdtemp(prefix="brand_mark_")
    try:
        pngs = _draw_svg(path, work) if path.lower().endswith(".svg") else _draw_raster(path, work)
        lines = []
        for png in pngs:
            for ln in screen_text.recognize(png, cache_dir=work):
                t = (ln.get("text") or "").strip()
                if t and t not in lines:
                    lines.append(t)
        return lines
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def _sidecar(out_dir, rel):
    return os.path.join(out_dir, rel) + ".json"


def _side(out_dir, rel):
    try:
        with open(_sidecar(out_dir, rel), encoding="utf-8") as fh:
            rec = json.load(fh)
        return rec if isinstance(rec, dict) else {}
    except (OSError, ValueError):
        return {}


def expected_name(out_dir, rel, product):
    """The name the mark at `rel` must spell: its sidecar's own `brand` (a third-party mark), else the product's."""
    b = _side(out_dir, rel).get("brand")
    return b.strip() if isinstance(b, str) and b.strip() else product


def check(out_dir, log=print):
    """Read every mark the film uses and write what it says into its sidecar. [{path, reads, verdict}]."""
    product = product_name(_board(out_dir).get("meta") or {})
    res = []
    for rel in candidates(out_dir):
        if not used(out_dir, rel):
            continue
        name = expected_name(out_dir, rel, product)
        if name is None:
            log("%s NOT READ  %s — the board names no product: set meta.product (or meta.brand.name), or give a "
                "third-party mark its own name in %s.json \"brand\"" % (TAG, rel, rel))
            continue
        p = os.path.join(out_dir, rel)
        reads = read(p)
        v = verdict(name, reads)
        side = _sidecar(out_dir, rel)
        rec = _side(out_dir, rel)
        old = rec.get("identity") if isinstance(rec.get("identity"), dict) else {}
        ident = {"sha256": _sha(p), "name": name, "reads": reads, "verdict": v}
        if v == "no-text" and old.get("confirmed") and old.get("sha256") == ident["sha256"]:
            ident["confirmed"] = old["confirmed"]          # the person's word stands for the same file
        rec["identity"] = ident
        with open(side, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        log("%s %-9s %s — reads %s" % (TAG, v.upper(), rel, " / ".join(reads) or "(nothing)"))
        res.append({"path": rel, "reads": reads, "verdict": v})
    if not res:
        log("%s the film uses no brand mark" % TAG)
    return res


# ── what validate refuses ───────────────────────────────────────────────────────────────────────────────────────
def lint(out_dir):
    """(errors, warnings) for the marks the film uses."""
    errors = []
    meta = _board(out_dir).get("meta") or {}
    marks = [rel for rel in candidates(out_dir) if used(out_dir, rel)]
    if not marks:
        return [], []
    product = product_name(meta)
    run = "run `python3 scripts/brand_mark.py %s`" % out_dir
    unnamed = [rel for rel in marks if expected_name(out_dir, rel, product) is None]
    if unnamed:
        errors.append("brand mark: the film uses %s but names no product — set meta.product (or meta.brand.name) "
                      "to the name the mark must spell (a third-party mark: its own name in its sidecar's "
                      "\"brand\"), then %s" % (", ".join(unnamed), run))
    for rel in marks:
        name = expected_name(out_dir, rel, product)
        if name is None:
            continue
        ident = _side(out_dir, rel).get("identity")
        if not isinstance(ident, dict):
            errors.append("brand mark %s was never read: a file's name and where it came from do not say whose mark "
                          "it is — %s" % (rel, run))
            continue
        if ident.get("sha256") != _sha(os.path.join(out_dir, rel)):
            errors.append("brand mark %s changed after it was read — %s again" % (rel, run))
            continue
        if ident.get("name") != name:
            errors.append("brand mark %s was read against %r, and the product is now %r — %s again"
                          % (rel, ident.get("name"), name, run))
            continue
        v = ident.get("verdict")
        reads = " / ".join(ident.get("reads") or [])
        if v == "mismatch":
            errors.append("brand mark %s reads %r, not %r: it is another product's mark — find %s's own (and "
                          "re-derive anything taken from this one, its palette first)" % (rel, reads, name, name))
        elif v == "no-text" and not (isinstance(ident.get("confirmed"), str) and ident["confirmed"].strip()):
            errors.append("brand mark %s has no letters to read: someone who knows must say it is %s's — ask the "
                          "user, and write their words in %s.json identity.confirmed (a third-party mark shown on "
                          "purpose: its owner's name in the sidecar's \"brand\")" % (rel, name, rel))
        elif v not in ("match", "no-text"):
            errors.append("brand mark %s: identity.verdict %r — %s" % (rel, v, run))
    return errors, []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    a = ap.parse_args(argv)
    try:
        res = check(os.path.abspath(a.out_dir))
    except RuntimeError as e:
        print("%s NOT CHECKED — %s" % (TAG, e))
        return 2
    errors, _w = lint(os.path.abspath(a.out_dir))
    for e in errors:
        print("%s ERROR %s" % (TAG, e))
    return 1 if errors else 0 if res is not None else 2


if __name__ == "__main__":
    sys.exit(main())
