#!/usr/bin/env python3
"""dna_from_deck — derive the film's Design DNA from the deck's OWN theme and rendered frames.

    python3 scripts/dna_from_deck.py <out_dir> [--pptx <deck.pptx>] [--mode light|dark] [--dry-run] [--json] [--force]

WHY THIS EXISTS. The remotion tier's whole visual identity is one object, `meta.design_dna`: type, palette,
container, motion, annotation grammar (runtime/dna.tsx). Today it comes from a PRESET the shot-director
picks by direction — terminal, editorial, product, blueprint... — so a film made from a deck with a custom
navy-and-teal theme set in Lora renders in the product preset's electric blue and Space Grotesk, and the
deck's owner does not recognise their own brand. The deck is the brand. A mature peer library builds every
film from the product's own identity; this is where ours reads it.

WHAT IS DERIVED FROM WHAT (and in which order of trust):

  ground    the RENDERED frames decide light vs dark and the actual ground colour — a theme's lt1 is white
            even when every slide sits on a dark picture. `--mode` overrides; in dark mode a theme's dk2 (the
            "dark 2" brand navy most templates carry) is the ground when the frames do not offer one.
  ink       the theme's dk1 / lt1 pole for the mode, then pushed apart from the ground to WCAG 7:1 with the
            same gamma-correct loop `theme.py` uses for the html tier — one contrast policy, not two.
  accent    a CUSTOM theme's accent1, treated as SAMPLED: nudged toward 3:1 on the ground, capped so the
            hue keeps its character (theme.py's brand-logo policy). An Office-DEFAULT theme (pptx_theme.py
            names them) never chose its colours, so the frames' most saturated colour wins instead.
  accent2   the most hue-distant of the theme's accent2..6 (custom theme), else the complement — at 3:1.
  type      the theme's major / minor faces CLASSIFIED (serif / didone / geometric / rounded / mono /
            humanist) and mapped onto the faces `runtime/fonts.ts` actually bundles — the deck's Calibri
            cannot be shipped, but its class can. Every stack ends with the CJK chain and a generic, or
            Chinese text would drop to a system default. The original names travel in `provenance`.
  form      atoms / radius / labels / motion follow the type class: serif → editorial kicker grammar,
            mono → the terminal grammar, else the product grammar. `id` is "deck": no native seam, the
            plain cross-fade (Film.tsx), which is the correct default for most films.

WHAT IT REFUSES TO DO. It never overwrites a Design DNA object someone authored (`--force` says otherwise);
a preset NAME is replaced, because a name is a direction and this is the direction's realisation. It fails
loudly when there is nothing to derive from (no frames, no theme) rather than writing the neutral preset
under a new name. Every family it emits is checked against fonts.ts, and every contrast is measured before
the object is written — the same three gates a hand-authored DNA is held to by validate.py.

Verified on real decks (see tests and the commit): an Office-default WorkBuddy deck (frames decide),
a Leiden research template (custom scheme, Calibri Light), Codex templates (Helvetica Neue; Lora + Roboto).
"""
import argparse
import colorsys
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import theme as th                                            # noqa: E402 — the html tier's colour math
import pptx_theme                                             # noqa: E402

FONTS_TS = os.path.join(_HERE, "..", "remotion", "src", "runtime", "fonts.ts")
CJK = '"PingFang SC", "Hiragino Sans", "Microsoft YaHei", "Noto Sans CJK SC"'

# typeface NAME → class. Substring matches on the lower-cased name; first hit wins, so the specific
# (didone, mono, rounded) come before the broad (serif, sans).
_CLASS_RULES = [
    ("mono", ("mono", "consolas", "courier", "menlo", "monaco", "fira code", "source code", "cascadia",
              "inconsolata", "sf mono", "jetbrains")),
    ("didone", ("bodoni", "didot", "playfair", "abril", "prata", "cormorant")),
    ("rounded", ("comic", "chalkboard", "baloo", "quicksand", "varela round", "fredoka", "nunito",
                 "marker felt", "chalkduster", "hand")),
    ("serif", ("times", "georgia", "cambria", "garamond", "book antiqua", "palatino", "lora", "merriweather",
               "baskerville", "minion", "noto serif", "pt serif", "crimson", "libre", "constantia", "song",
               "宋", "ming", "明", "serif", "charter", "spectral", "eb garamond", "literata", "tinos")),
    ("geometric", ("futura", "avenir", "montserrat", "poppins", "gotham", "proxima", "gill", "century gothic",
                   "space grotesk", "dm sans", "raleway", "josefin", "jost", "outfit", "manrope", "urbanist",
                   "impact", "bebas", "anton", "oswald", "league gothic", "din", "bahnschrift")),
    ("plex", ("ibm plex", "plex")),
]
# class → the bundled faces (must be names fonts.ts loads — checked at run time, never assumed)
_CLASS_FACES = {
    "mono":      {"display": "JetBrains Mono", "body": "JetBrains Mono", "generic": "ui-monospace, monospace"},
    "didone":    {"display": "Bodoni Moda", "body": "Source Serif 4", "generic": "Georgia, serif"},
    "serif":     {"display": "Playfair Display", "body": "Source Serif 4", "generic": "Georgia, serif"},
    "rounded":   {"display": "Baloo 2", "body": "Inter", "generic": "system-ui, sans-serif"},
    "geometric": {"display": "Space Grotesk", "body": "Inter", "generic": "system-ui, sans-serif"},
    "plex":      {"display": "IBM Plex Sans", "body": "IBM Plex Sans", "generic": "system-ui, sans-serif"},
    "humanist":  {"display": "Inter", "body": "Inter", "generic": "system-ui, sans-serif"},
}
_CLASS_FORM = {
    # the FORM each type class speaks — mirrors the presets in runtime/dna.tsx for the same worlds
    "mono":  {"atoms": {"bar": "block", "figure": "mono", "list": "tree", "label": "prompt", "divider": "scanline",
                        "marker": "caret"}, "radius": 4, "motion": "type", "decoration": ["prompt", "cursor"],
              "uppercaseLabels": False, "labelSpacing": "0.02em", "uniformType": True},
    "serif": {"atoms": {"bar": "ruled", "figure": "serif", "list": "ruled", "label": "kicker", "divider": "hairline",
                        "marker": "triangle"}, "radius": 2, "motion": "smooth", "decoration": ["grid"],
              "uppercaseLabels": True, "labelSpacing": "0.18em"},
    "sans":  {"atoms": {"bar": "solid", "figure": "display", "list": "bullet", "label": "chip", "divider": "hairline",
                        "marker": "triangle"}, "radius": 14, "motion": "smooth", "decoration": ["grid"],
              "uppercaseLabels": False, "labelSpacing": "0.04em"},
}


def classify_font(name):
    """'Calibri' → 'humanist', 'Lora' → 'serif', 'Consolas' → 'mono' ... An empty / unknown name is humanist."""
    n = (name or "").strip().lower()
    if not n:
        return "humanist"
    for cls, keys in _CLASS_RULES:
        if any(k in n for k in keys):
            return cls
    return "humanist"


def loaded_families():
    """The families fonts.ts actually bundles — read from the file, never restated here."""
    ts = open(FONTS_TS, encoding="utf-8").read()
    return set(re.findall(r"family: '([^']+)'", ts))


def _stack(face, generic):
    return '"%s", %s, %s' % (face, CJK, generic)


def _q(rgb):
    """Quantised to the 8-bit values that will actually be written — a contrast measured on floats can sit
    at 3.001 and ship as 2.998 once rounded to hex, which is how the first run of this failed its own gate."""
    return tuple(max(0, min(255, int(round(c)))) for c in rgb)


def _nudge_to(rgb, bg, mode, target, cap=0.15):
    """theme.py's policy for a SAMPLED hue: move lightness toward contrast, hue kept, capped; then, past
    the cap, shed a little saturation until it clears — a readable deep hue beats an unreadable hero."""
    bg = _q(bg)
    h, l0, s = colorsys.rgb_to_hls(*[c / 255 for c in rgb]); l = l0
    rgb = _q(rgb)
    for _ in range(30):
        if th._contrast(rgb, bg) >= target:
            return rgb
        l = max(0.0, l - 0.02) if mode == "light" else min(1.0, l + 0.02)
        if abs(l - l0) > cap:
            break
        rgb = _q(tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s)))
    while th._contrast(rgb, bg) < target and 0.0 < l < 1.0:
        l = max(0.0, l - 0.02) if mode == "light" else min(1.0, l + 0.02)
        s *= 0.97
        rgb = _q(tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s)))
    if th._contrast(rgb, bg) < target:                                  # l hit the pole and it still fails
        rgb = (0, 0, 0) if mode == "light" else (255, 255, 255)
    return rgb


def _hue_distance(a, b):
    return min(abs(th._hue(a) - th._hue(b)), 1 - abs(th._hue(a) - th._hue(b)))


def sample_frames(out_dir, k=6, n_colors=6):
    """[(weight, rgb)] over up to k frames spread EVENLY through the deck, weight = share of all sampled pixels.

    Not theme.py's sampler, for two measured reasons. That one returns the palette ENTRIES unweighted, so a
    white slide quantised to one white and four dark accent swatches averages as "dark" — the Leiden deck
    (white ground, blue title bands) was read as a dark film that way. And it takes the FIRST four frames,
    where a title slide's full-bleed picture stands in for the whole deck. Pixel weights and an even spread
    make the ground the colour most of the deck actually shows."""
    import glob
    from PIL import Image
    paths = sorted(glob.glob(os.path.join(out_dir, "frames", "*.png")))
    if not paths:
        return None
    if len(paths) > k:
        paths = [paths[int(round(i * (len(paths) - 1) / (k - 1)))] for i in range(k)]
    weights = {}
    total = 0
    for p in paths:
        im = Image.open(p).convert("RGB"); im.thumbnail((160, 160))
        q = im.quantize(colors=n_colors).convert("RGB")
        for n, c in q.getcolors(maxcolors=100000):
            weights[c] = weights.get(c, 0) + n
            total += n
    return sorted(((n / float(total), c) for c, n in weights.items()), reverse=True) or None


def accents_from_frames(out_dir, ground, k=6, bins=24):
    """[(share, rgb)] — the deck's SATURATED hues, heaviest first, each as the mean colour of its hue bin.

    A palette quantised to six colours a frame merges a heading's violet, a bar's cyan and an underline's
    orange into one muddy average and then reports THAT as the accent (measured: a violet-branded deck came
    out teal). So the accent is read from the saturated pixels alone — a hue histogram over every sampled
    frame, pixels near the ground excluded — and the brand colour is simply the hue the deck uses most."""
    import glob
    from PIL import Image
    paths = sorted(glob.glob(os.path.join(out_dir, "frames", "*.png")))
    if not paths:
        return []
    if len(paths) > k:
        paths = [paths[int(round(i * (len(paths) - 1) / (k - 1)))] for i in range(k)]
    hist = [[0, 0.0, 0.0, 0.0] for _ in range(bins)]                 # count, sum r, g, b
    total = 0
    g = _q(ground) if ground is not None else None
    for p in paths:
        im = Image.open(p).convert("RGB"); im.thumbnail((200, 200))
        for n, c in im.getcolors(maxcolors=200 * 200) or []:
            total += n
            if th._sat(c) < 0.35 or not (0.10 <= th._lum(c) <= 0.90):
                continue
            if g is not None and sum((a - b) ** 2 for a, b in zip(c, g)) < 60 ** 2:
                continue                                              # the ground itself is not an accent
            b = int(th._hue(c) * bins) % bins
            hist[b][0] += n; hist[b][1] += n * c[0]; hist[b][2] += n * c[1]; hist[b][3] += n * c[2]
    out = []
    for cnt, r, gg, bb in hist:
        if cnt:
            out.append((cnt / float(max(1, total)), _q((r / cnt, gg / cnt, bb / cnt))))
    return sorted(out, reverse=True)


def _ground_from_frames(sampled, mode):
    """The heaviest sampled colour on the mode's side of mid-grey, if the frames offer one."""
    side = [(w, c) for w, c in sampled if (th._lum(c) >= 0.5) == (mode == "light")]
    return max(side)[1] if side else None


def derive(out_dir, pptx=None, mode=None):
    """The Design DNA dict for this deck, plus the provenance that says where each token came from."""
    theme = pptx_theme.read(pptx) if pptx else None
    sampled = sample_frames(out_dir)
    if theme is None and not sampled:
        raise SystemExit("[dna_from_deck] nothing to derive from: no readable theme and no frames/ in %s" % out_dir)
    cols = (theme or {}).get("colors") or {}
    rgb = lambda k: th._hex2rgb(cols[k]) if cols.get(k) else None            # noqa: E731

    # ── mode + ground: the frames say what the deck LOOKS like ─────────────────────────────────────
    if mode in ("light", "dark"):
        m = mode
    elif sampled:
        m = "light" if sum(w * th._lum(c) for w, c in sampled) >= 0.5 else "dark"
    else:
        g = th._hex2rgb(theme["master_ground"]) if theme.get("master_ground") else rgb("lt1")
        m = "light" if (g is None or th._lum(g) >= 0.5) else "dark"
    ground_src = None
    bgc = _ground_from_frames(sampled, m) if sampled else None
    if bgc is not None:
        ground_src = "frames"
    elif m == "dark" and rgb("dk2") is not None and th._lum(rgb("dk2")) < 0.25:
        bgc, ground_src = rgb("dk2"), "theme dk2"
    elif m == "light" and theme and theme.get("master_ground"):
        bgc, ground_src = th._hex2rgb(theme["master_ground"]), "master ground"
    elif rgb("lt1" if m == "light" else "dk1") is not None:
        bgc, ground_src = rgb("lt1" if m == "light" else "dk1"), "theme %s" % ("lt1" if m == "light" else "dk1")
    else:
        bgc, ground_src = ((248, 247, 244) if m == "light" else (14, 15, 17)), "default"
    # anti-cliché: never a pure white / pure black ground (theme.py's rule, same numbers)
    if th._lum(bgc) <= 0.02:
        bgc = (14, 15, 17)
    elif th._lum(bgc) >= 0.97:
        bgc = (248, 247, 244)

    # ── ink: the theme's pole for the mode, pushed to 7:1 by moving the GROUND (hue kept) ─────────
    pole = rgb("dk1" if m == "light" else "lt1")
    fg = pole if pole is not None else ((22, 20, 18) if m == "light" else (240, 243, 248))
    if th._lum(fg) <= 0.02:
        fg = (22, 20, 18)
    elif th._lum(fg) >= 0.97:
        fg = (240, 243, 248)
    h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in bgc])
    bgc, fg = _q(bgc), _q(fg)
    for _ in range(60):
        if th._contrast(fg, bgc) >= 7.0:
            break
        l = min(1.0, l + 0.02) if m == "light" else max(0.0, l - 0.02)
        bgc = _q(tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s)))
    if th._contrast(fg, bgc) < 7.0:
        fg = (0, 0, 0) if m == "light" else (255, 255, 255)

    # ── accents: a custom theme's own; a default theme's are Office's, so the frames decide ───────
    custom = bool(theme) and not theme.get("default_theme") and rgb("accent1") is not None
    if custom:
        acc, acc_src = rgb("accent1"), "theme accent1"
        others = [rgb("accent%d" % i) for i in range(2, 7) if rgb("accent%d" % i) is not None]
        others = [c for c in others if th._sat(c) >= 0.12]                # a grey accent2 is not a second hue
        if others:
            acc2, acc2_src = max(others, key=lambda c: _hue_distance(c, acc)), "theme accent (most distant hue)"
        else:
            acc2, acc2_src = None, None
    elif sampled and [h for h in accents_from_frames(out_dir, bgc) if h[0] >= 0.002]:
        # the hue the deck uses most among its saturated pixels, provided it covers at least 0.2% of the
        # sampled area — a speck of logo red on one slide is not the deck's accent
        hues = [h for h in accents_from_frames(out_dir, bgc) if h[0] >= 0.002]
        acc, acc_src = hues[0][1], "frames (dominant saturated hue)"
        # a second hue counts when the deck uses it for at least a tenth of what it uses the first for
        second = [c for w, c in hues[1:] if _hue_distance(c, acc) >= 0.15 and w >= max(0.002, 0.1 * hues[0][0])]
        acc2, acc2_src = (second[0], "frames (second hue)") if second else (None, None)
    elif rgb("accent1") is not None:
        acc, acc_src = rgb("accent1"), "theme accent1 (default theme, no saturated frame colour)"
        acc2, acc2_src = None, None
    else:
        acc, acc_src = ((76, 155, 232)), "default"
        acc2, acc2_src = None, None
    if acc2 is None:
        # the complement, TINTED: theme.py's rule at full saturation gave a teal deck a pure #ff0000 kicker,
        # which no deck ever chose. Saturation is capped and the lightness sits with the mode, so it reads as
        # a warm/cool counterpoint rather than a warning light.
        hh, ll, ss = colorsys.rgb_to_hls(*[c / 255 for c in acc])
        acc2 = tuple(c * 255 for c in colorsys.hls_to_rgb((hh + 0.5) % 1.0, 0.44 if m == "light" else 0.62,
                                                         min(0.72, max(0.45, ss))))
        acc2_src = "complement (tinted)"
    acc = _nudge_to(acc, bgc, m, 3.0)
    acc2 = _nudge_to(acc2, bgc, m, 3.0, cap=0.18)
    on_acc = (17, 17, 17) if th._contrast((17, 17, 17), acc) >= th._contrast((255, 255, 255), acc) else (255, 255, 255)

    # ── type: the deck's faces, classified, mapped onto what the renderer bundles ──────────────────
    fonts = (theme or {}).get("fonts") or {}
    major = (fonts.get("major") or {}).get("latin", "")
    minor = (fonts.get("minor") or {}).get("latin", "")
    dcls, bcls = classify_font(major), classify_font(minor)
    faces = loaded_families()
    disp = _CLASS_FACES[dcls]["display"]
    body = _CLASS_FACES[bcls]["body"]
    if bcls == "mono" and dcls != "mono":                              # a mono BODY under a non-mono display is
        body = _CLASS_FACES[dcls]["body"]                              # a spec, not a system: keep one world
    for fam in (disp, body, "JetBrains Mono"):
        if fam not in faces:
            raise SystemExit("[dna_from_deck] %r is not a family runtime/fonts.ts loads (%s) — the font map has "
                             "drifted from the bundle" % (fam, ", ".join(sorted(faces))))
    world = "mono" if dcls == "mono" else ("serif" if dcls in ("serif", "didone") else "sans")
    form = _CLASS_FORM[world]

    slug = re.sub(r"[^a-z0-9]+", "-", (theme or {}).get("theme", "") .lower()).strip("-") if theme else ""
    dna = {
        "id": "deck",
        "name": ("deck: %s" % ((theme or {}).get("theme") or slug or os.path.basename(out_dir))),
        "fontDisplay": _stack(disp, _CLASS_FACES[dcls]["generic"]),
        "fontMono": _stack("JetBrains Mono", "ui-monospace, monospace"),
        "fontBody": _stack(body, _CLASS_FACES[bcls]["generic"]),
        "bg": th._hex(bgc),
        # a quiet lamp from above, like the presets: the ground lifted 4% toward the ink at the top, settling
        # into itself — never a second colour, so the caption ink and the seam guard keep reading `bg`
        "bgGrad": "radial-gradient(120%% 120%% at 50%% -6%%, %s, %s 74%%)"
                  % (th._hex(th._mix(bgc, fg, 0.04)), th._hex(bgc)),
        "fg": th._hex(fg),
        "dim": th._hex(th._mix(fg, bgc, 0.45)),
        "accent": th._hex(acc),
        "accent2": th._hex(acc2),
        "onAccent": th._hex(on_acc),
        "surface": th._hex(th._mix(bgc, fg, 0.06)),
        "surfaceBorder": th._hex(th._mix(bgc, fg, 0.20)),
        "line": th._hex(th._mix(bgc, fg, 0.13)),
        "radius": form["radius"],
        "borderWidth": 1,
        "motion": form["motion"],
        "decoration": list(form["decoration"]),
        "uppercaseLabels": form["uppercaseLabels"],
        "labelSpacing": form["labelSpacing"],
        "atoms": dict(form["atoms"]),
        "provenance": {
            "source": theme["path"] if theme else "frames only",
            "theme": (theme or {}).get("theme"), "scheme": (theme or {}).get("scheme"),
            "default_theme": bool((theme or {}).get("default_theme")),
            "mode": m, "ground": ground_src, "accent": acc_src, "accent2": acc2_src,
            "fonts": {"major": major or None, "minor": minor or None, "major_class": dcls, "minor_class": bcls,
                      "mapped": {"display": disp, "body": body}},
        },
    }
    if form.get("uniformType"):
        dna["uniformType"] = True
    # the gates a hand-authored DNA is held to, applied before anything is written
    assert th._contrast(th._hex2rgb(dna["fg"]), th._hex2rgb(dna["bg"])) >= 7.0
    assert th._contrast(th._hex2rgb(dna["accent"]), th._hex2rgb(dna["bg"])) >= 3.0
    assert th._contrast(th._hex2rgb(dna["accent2"]), th._hex2rgb(dna["bg"])) >= 3.0
    return dna


def _find_pptx(out_dir, explicit):
    if explicit:
        if not os.path.exists(explicit):
            raise SystemExit("[dna_from_deck] --pptx %s does not exist" % explicit)
        return explicit
    try:
        src = (json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {}).get("source")
    except Exception:                                                  # noqa: BLE001
        src = None
    return src if (src and str(src).lower().endswith(".pptx") and os.path.exists(src)) else None


def describe(dna):
    p = dna["provenance"]
    lines = ["[dna_from_deck] %s  (%s theme%s)" % (dna["name"], p["scheme"] or "no",
                                                    ", Office DEFAULT — frames decide" if p["default_theme"] else ""),
             "  mode %-5s ground %s from %s | ink %s | accent %s from %s | accent2 %s from %s"
             % (p["mode"], dna["bg"], p["ground"], dna["fg"], dna["accent"], p["accent"], dna["accent2"], p["accent2"]),
             "  type  %s (%s) -> %s | %s (%s) -> %s | mono JetBrains Mono"
             % (p["fonts"]["major"] or "—", p["fonts"]["major_class"], p["fonts"]["mapped"]["display"],
                p["fonts"]["minor"] or "—", p["fonts"]["minor_class"], p["fonts"]["mapped"]["body"]),
             "  form  atoms %s | radius %d | motion %s" % (dna["atoms"], dna["radius"], dna["motion"])]
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description="Derive meta.design_dna from the deck's own theme + frames.")
    ap.add_argument("out_dir")
    ap.add_argument("--pptx", default=None, help="the source deck (default: storyboard meta.source when it is a pptx)")
    ap.add_argument("--mode", choices=("light", "dark"), default=None)
    ap.add_argument("--dry-run", action="store_true", help="print the DNA, write nothing")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--force", action="store_true", help="replace an AUTHORED design_dna object")
    a = ap.parse_args(argv)
    board = os.path.join(a.out_dir, "storyboard.json")
    data = json.load(open(board, encoding="utf-8")) if os.path.exists(board) else None
    pptx = _find_pptx(a.out_dir, a.pptx)
    dna = derive(a.out_dir, pptx=pptx, mode=a.mode)
    if a.json:
        print(json.dumps(dna, ensure_ascii=False, indent=2))
    else:
        print(describe(dna))
    if a.dry_run:
        return 0
    if data is None:
        print("[dna_from_deck] no storyboard.json in %s — nothing written (use --dry-run to only print)" % a.out_dir)
        return 1
    meta = data.setdefault("meta", {})
    cur = meta.get("design_dna")
    if isinstance(cur, dict) and not a.force and cur.get("id") != "deck":
        print("[dna_from_deck] meta.design_dna is an AUTHORED object (id %r) — not overwritten; pass --force to replace it"
              % cur.get("id"))
        return 1
    meta["design_dna"] = dna
    meta["design_dna_source"] = "deck"
    if pptx and not meta.get("source"):
        meta["source"] = os.path.abspath(pptx)
    json.dump(data, open(board, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[dna_from_deck] wrote meta.design_dna -> %s" % board)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
