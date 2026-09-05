#!/usr/bin/env python3
"""pptx_theme — read a deck's OWN theme: its colour scheme, its font scheme, its master ground. No guessing.

    python3 scripts/pptx_theme.py <deck.pptx>          # the theme as JSON

WHY THIS EXISTS. A deck already carries a visual identity — the theme part every pptx ships (`theme1.xml`:
twelve scheme colours, a major/minor font pair) and the slide master's ground. Until now the pipeline threw
all of it away at ingest: `ingest.py` rendered the slides to PNG and kept the speaker notes, and every
downstream palette was re-sampled from pixels while the deck's actual accent hexes and typeface names sat
unread in the file. `dna_from_deck.py` turns this into the remotion tier's Design DNA.

WHAT IS READ, AND HOW IT IS RESOLVED:

  colours   `<a:clrScheme>`: dk1 lt1 dk2 lt2 accent1..6 hlink folHlink. A `sysClr` (Office's "windowText" /
            "window") resolves through its `lastClr`, else to black / white — the only two Office ever uses.
  fonts     `<a:fontScheme>`: majorFont (headings) and minorFont (body), latin + East-Asian faces.
  ground    the master's `<p:bg>`: a solid fill (srgb or a scheme colour resolved through the master's
            `<p:clrMap>` — bg1→lt1 is the mapping, not an identity) or None for a gradient / picture, where
            the rendered frames are the only honest source.
  master    a deck can carry several masters; the one MOST SLIDES USE is read, and the count is reported.

DEFAULT-THEME DETECTION. Most decks never chose their colours: the scheme is Office's own ("Office", accent1
#4F81BD / #4472C4 / #156082 — three generations of the same default) and the fonts are Calibri. Reporting
such a theme as "the brand" would paint every film Office blue. `default_theme` is True for those, and a
caller treats the theme as WEAK (the rendered frames decide) while still keeping any custom font pair.
Verified against real decks: an Office-default WorkBuddy deck, a Leiden template with a custom 'Custom 83'
scheme, and two Codex template decks (custom schemes, Helvetica Neue / Lora + Roboto).
"""
import json
import os
import re
import sys
from collections import Counter

DEFAULT_ACCENT1 = {"4F81BD", "4472C4", "156082"}      # Office 2007 / 2013 / 2023 defaults
DEFAULT_SCHEME_NAMES = {"office", "office theme", "default"}
_SYS = {"windowtext": "000000", "window": "FFFFFF"}
_CLRMAP_DEFAULT = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}


def _srgb(body):
    m = re.search(r'srgbClr val="([0-9A-Fa-f]{6})"', body or "")
    if m:
        return m.group(1).upper()
    m = re.search(r'sysClr val="(\w+)"(?:[^>]*lastClr="([0-9A-Fa-f]{6})")?', body or "")
    if m:
        return (m.group(2) or _SYS.get(m.group(1).lower(), "000000")).upper()
    return None


def _scheme_colors(theme_xml):
    m = re.search(r'<a:clrScheme[^>]*name="([^"]*)"(.*?)</a:clrScheme>', theme_xml, re.S)
    if not m:
        return None, {}
    cols = {}
    for k in re.finditer(r"<a:(dk1|lt1|dk2|lt2|accent[1-6]|hlink|folHlink)>(.*?)</a:\1>", m.group(2), re.S):
        v = _srgb(k.group(2))
        if v:
            cols[k.group(1)] = "#" + v.lower()
    return m.group(1), cols


def _font_scheme(theme_xml):
    m = re.search(r'<a:fontScheme[^>]*name="([^"]*)"(.*?)</a:fontScheme>', theme_xml, re.S)
    if not m:
        return None, {}
    out = {}
    for role in ("major", "minor"):
        b = re.search(r"<a:%sFont>(.*?)</a:%sFont>" % (role, role), m.group(2), re.S)
        body = b.group(1) if b else ""
        lat = re.search(r'<a:latin typeface="([^"]*)"', body)
        ea = re.search(r'<a:ea typeface="([^"]*)"', body)
        out[role] = {"latin": (lat.group(1) if lat else "") or "", "ea": (ea.group(1) if ea else "") or ""}
    return m.group(1), out


def _master_ground(master_xml, cols):
    """The master's solid ground as '#hex', resolved through its clrMap; None when it is not a solid."""
    cmap = dict(_CLRMAP_DEFAULT)
    m = re.search(r"<p:clrMap([^>]*)/?>", master_xml)
    if m:
        for k, v in re.findall(r'(\w+)="(\w+)"', m.group(1)):
            cmap[k] = v
    bg = re.search(r"<p:bg>(.*?)</p:bg>", master_xml, re.S)
    if not bg:
        return cols.get(cmap.get("bg1", "lt1"))               # no <p:bg>: the theme's bg1 shows through
    body = bg.group(1)
    if "<a:gradFill" in body or "<a:blipFill" in body or "<a:pattFill" in body:
        return None
    s = _srgb(body)
    if s:
        return "#" + s.lower()
    sc = re.search(r'schemeClr val="(\w+)"', body)
    if sc:
        key = cmap.get(sc.group(1), sc.group(1))
        return cols.get(key)
    return None


def read(pptx_path):
    """The deck's theme as a dict, or None when the file has no readable theme part."""
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    prs = Presentation(pptx_path)
    masters = list(prs.slide_masters)
    if not masters:
        return None
    # the master most slides actually use — a deck can carry unused masters from a template's past
    usage = Counter()
    for s in prs.slides:
        try:
            usage[id(s.slide_layout.slide_master)] += 1
        except Exception:                                    # noqa: BLE001
            pass
    master = max(masters, key=lambda m: usage.get(id(m), 0)) if usage else masters[0]
    rel = [r for r in master.part.rels.values() if r.reltype == RT.THEME]
    if not rel:
        return None
    theme_xml = rel[0].target_part.blob.decode("utf-8", "replace")
    tname = re.search(r'<a:theme[^>]*name="([^"]*)"', theme_xml)
    scheme, cols = _scheme_colors(theme_xml)
    fscheme, fonts = _font_scheme(theme_xml)
    a1 = (cols.get("accent1") or "").lstrip("#").upper()
    default = (scheme or "").strip().lower() in DEFAULT_SCHEME_NAMES or a1 in DEFAULT_ACCENT1
    return {"path": os.path.abspath(pptx_path), "theme": tname.group(1) if tname else None,
            "scheme": scheme, "font_scheme": fscheme, "colors": cols, "fonts": fonts,
            "default_theme": bool(default),
            "master_ground": _master_ground(master.part.blob.decode("utf-8", "replace"), cols),
            "masters": len(masters), "slides": len(prs.slides)}


def main(argv):
    if not argv:
        print(__doc__.split("\n\n")[0]); return 2
    t = read(argv[0])
    if t is None:
        print("[pptx_theme] %s carries no readable theme part" % argv[0]); return 1
    print(json.dumps(t, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
