"""Derive a topic-fitting color theme and write theme.css. Samples the source slide frames when
present (PIL quantize + luminance -> light/dark + a vivid accent), else uses a passed topic palette.
A brand logo (--brand-logo, or storyboard meta.brand.logo) outranks frames as the ACCENT source.
Curated, contrast-safe derivation (not raw pixels). Deterministic: no randomness, no wall-clock."""
import argparse, colorsys, glob, json, os

def _hex(rgb): return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)
def _hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _lum(rgb):
    """Simple (non-linear) luminance — a brightness proxy for the light/dark + pure-bg heuristics."""
    r, g, b = [c / 255 for c in rgb]; return 0.2126 * r + 0.7152 * g + 0.0722 * b
def _rel_lum(rgb):
    """WCAG relative luminance: sRGB channels LINEARIZED (gamma-correct). Use for CONTRAST only —
    the simple _lum under-reports mid-tones ~2.2x (it scored #767676-on-#fff at 2.05 vs the true 4.54)."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
def _sat(rgb):
    r, g, b = [c / 255 for c in rgb]; return colorsys.rgb_to_hls(r, g, b)[2]
def _hue(rgb):
    r, g, b = [c / 255 for c in rgb]; return colorsys.rgb_to_hls(r, g, b)[0]
def _mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def _contrast(a, b):
    la, lb = _rel_lum(a) + 0.05, _rel_lum(b) + 0.05
    return max(la, lb) / min(la, lb)

def _sample_frames(out_dir, k=4, n_colors=5):
    from PIL import Image
    paths = sorted(glob.glob(os.path.join(out_dir, "frames", "*.png")))[:k]
    if not paths:
        return None
    cols = []
    for p in paths:
        im = Image.open(p).convert("RGB"); im.thumbnail((120, 120))
        q = im.quantize(colors=n_colors).convert("RGB")
        cols += [rgb for _, rgb in q.getcolors(maxcolors=100000)]
    return cols or None

def _sample_logo(path):
    """Dominant NON-neutral hue of a brand logo. Logos are mostly mark + ground, so drop transparent,
    near-white/near-black and low-saturation pixels; the heaviest survivor is the brand hue.
    None = all-neutral mark (caller falls back)."""
    from PIL import Image
    im = Image.open(path).convert("RGBA"); im.thumbnail((128, 128))
    best, best_n = None, 0
    for n, (r, g, b, a) in (im.getcolors(maxcolors=128 * 128) or []):
        if a < 128 or not (0.06 <= _lum((r, g, b)) <= 0.92) or _sat((r, g, b)) < 0.25:
            continue
        if n > best_n:
            best, best_n = (r, g, b), n
    return best

def _brand_accent(path):
    """Accent source from a brand logo, honoring the never-crash contract: svg (PIL can't rasterize),
    an unreadable file, or an all-neutral mark -> printed note + None so derivation falls back."""
    if str(path).lower().endswith(".svg"):
        print(f"[theme] brand logo {os.path.basename(path)} is svg — can't sample it, falling back (pass a png)")
        return None
    try:
        c = _sample_logo(path)
    except Exception:
        print(f"[theme] brand logo {path!r} unreadable — falling back"); return None
    if not c:
        print("[theme] brand logo has no usable non-neutral hue — falling back to frames/style")
    return c

def _storyboard_brand_logo(out_dir):
    """meta.brand.logo from <out_dir>/storyboard.json (path rel to out_dir) — the auto brand source
    when neither --accent nor --brand-logo was passed. Best-effort AND honest: silent when there is
    no storyboard or no brand block (the normal unbranded case), but a DECLARED brand whose logo
    file isn't on disk yet gets a printed note — the silent no-op shipped brandless accents."""
    try:
        lg = str(json.load(open(os.path.join(out_dir, "storyboard.json")))["meta"]["brand"]["logo"])
    except Exception:
        return ""
    p = lg if os.path.isabs(lg) else os.path.join(out_dir, lg)
    if not os.path.exists(p):
        print(f"[theme] meta.brand.logo '{lg}' declared but not on disk — accent derived WITHOUT the "
              f"brand hue; copy the asset in and re-run theme.py")
        return ""
    return p

# Visual-style presets (see references/visual-styles.md). A chosen style SEEDS the palette (mode + accent
# family) and emits style-hint CSS vars for the flat/HTML tiers + motifs. Precedence: explicit --mode/
# --accent/--accent2/--bg (a stated brand) > STYLE preset > sampled frames > the neutral default. The WCAG
# contrast loops below run AFTERWARD untouched, so a style can never yield an unreadable palette.
# entry: (mode, accent, accent2, {radius, border, display-font, grid-strength, motif-ink})
STYLE_PRESETS = {
    "swiss":        ("light", "#e2231a", "#111111", {"radius": "2px",  "border": "2px", "font": "sans-serif", "grid": ".10", "ink": "grid", "bink": "#111111"}),
    "editorial":    ("light", "#7a1f1f", "#2b2b2b", {"radius": "3px",  "border": "1px", "font": "serif",      "grid": ".05", "ink": "rule"}),
    "bauhaus":      ("light", "#e5231b", "#1552c4", {"radius": "0",    "border": "3px", "font": "sans-serif", "grid": ".08", "ink": "geometric", "bink": "#111111"}),
    "brutalism":    ("light", "#111111", "#c6ff00", {"radius": "0",    "border": "3px", "font": "monospace",  "grid": ".14", "ink": "grid", "bink": "#111111"}),
    "glassmorphism":("dark",  "#5b9dff", "#c58bff", {"radius": "20px", "border": "1px", "font": "sans-serif", "grid": ".05", "ink": "glow"}),
    "claymorphism": ("light", "#7b6ef6", "#ff8fab", {"radius": "28px", "border": "0",   "font": "sans-serif", "grid": ".04", "ink": "blob"}),
    "manga":        ("light", "#111111", "#e5231b", {"radius": "6px",  "border": "3px", "font": "sans-serif", "grid": ".10", "ink": "speedline", "bink": "#111111"}),
    "risograph":    ("light", "#ff5a3c", "#2f6ae0", {"radius": "4px",  "border": "2px", "font": "sans-serif", "grid": ".06", "ink": "halftone"}),
    "memphis":      ("light", "#ff4d6d", "#00c2b8", {"radius": "12px", "border": "3px", "font": "sans-serif", "grid": ".08", "ink": "geometric", "bink": "#111111"}),
    "noir":         ("dark",  "#c9c2b6", "#8a1c1c", {"radius": "2px",  "border": "1px", "font": "serif",      "grid": ".06", "ink": "beam"}),
    "cyberpunk":    ("dark",  "#00e5ff", "#ff2bd6", {"radius": "4px",  "border": "2px", "font": "monospace",  "grid": ".12", "ink": "grid"}),
    "vaporwave":    ("dark",  "#ff71ce", "#01cdfe", {"radius": "8px",  "border": "2px", "font": "sans-serif", "grid": ".14", "ink": "grid"}),
    "watercolor":   ("light", "#4f7a8a", "#c98b6b", {"radius": "10px", "border": "0",   "font": "serif",      "grid": ".04", "ink": "wash"}),
    "artdeco":      ("dark",  "#c8a24a", "#0f6e63", {"radius": "2px",  "border": "2px", "font": "serif",      "grid": ".07", "ink": "fan"}),
    "cinematic":    ("dark",  "#e08a3c", "#2f8f9d", {"radius": "6px",  "border": "0",   "font": "serif",      "grid": ".05", "ink": "none"}),
    "blueprint":    ("dark",  "#5fbcff", "#bcd3e6", {"radius": "2px",  "border": "2px", "font": "monospace",  "grid": ".16", "ink": "grid"}),
    "terminal":     ("dark",  "#39ff14", "#ffb000", {"radius": "2px",  "border": "1px", "font": "monospace",  "grid": ".12", "ink": "scanline"}),
    "cartographic": ("light", "#3f6f5f", "#b06a3c", {"radius": "4px",  "border": "1px", "font": "serif",      "grid": ".07", "ink": "contour"}),
}

# FILM-GRAIN amount per style, keyed off its `ink` — the consumer the `ink` metadata (halftone/speedline/
# wash/scanline/beam) never had. motifs.css `body::after` reads --grain-amount; 0 = clean styles pay
# nothing. Only the styles whose identity is a printed/filmic SURFACE get grain; grid/geometric/glow/blob
# styles stay crisp. A style dict may override with an explicit "grain" key.
_GRAIN_BY_INK = {"halftone": ".16", "speedline": ".13", "wash": ".10",
                 "scanline": ".10", "beam": ".08", "contour": ".06"}


# ── style TYPE — each style's display + body FACE (bundled in assets/fonts/, SIL OFL) so the deck's
#    typography matches its style: comic reads comic (Bangers), Swiss/geometric reads grotesque
#    (Space Grotesk), editorial/deco/noir reads high-contrast serif (Playfair Display), code/data reads
#    mono (JetBrains Mono). Each stack keeps a CJK + generic fallback so 中文 decks and non-mac machines
#    still render. base.css @font-face declares the families; scenes.py reads --font-kind for the same
#    face on the programmatic (matplotlib/PIL) tier.
_CJK_SANS = '"PingFang SC","Hiragino Sans GB","Microsoft YaHei"'
_CJK_SERIF = '"Songti SC","Source Han Serif SC","SimSun"'
_FONT_FAMILIES = {   # kind -> (display stack, body stack)
    "sans":  (f'"Space Grotesk","Helvetica Neue",Arial,{_CJK_SANS},sans-serif',
              f'"Space Grotesk","Helvetica Neue",Arial,{_CJK_SANS},sans-serif'),
    "serif": (f'"Playfair Display",Georgia,"Times New Roman",{_CJK_SERIF},serif',
              f'Georgia,"Times New Roman",{_CJK_SERIF},serif'),
    "mono":  (f'"JetBrains Mono","SF Mono",Menlo,{_CJK_SANS},monospace',
              f'"JetBrains Mono","SF Mono",Menlo,{_CJK_SANS},monospace'),
    "comic": (f'"Bangers","Space Grotesk",Impact,"Hannotate SC","HanziPen SC",{_CJK_SANS},sans-serif',
              f'"Space Grotesk","Helvetica Neue",Arial,{_CJK_SANS},sans-serif'),
}
# The NUMERIC value-role face (--font-number, applied to .stat/.num/.delta/…). A display SERIF
# (Playfair) or COMIC (Bangers) renders big figures unevenly — ornate, varying weight/baseline — so
# numbers get a clean LINING + TABULAR figure face regardless of the headline style: Space Grotesk for
# serif/sans/comic decks (even, modern digits that still sit under a serif headline), JetBrains Mono
# for mono/technical decks (where monospaced figures fit the register). Words keep --font-display.
_FONT_NUMBER = {
    "sans":  f'"Space Grotesk","Helvetica Neue",Arial,{_CJK_SANS},sans-serif',
    "serif": f'"Space Grotesk","Helvetica Neue",Arial,{_CJK_SANS},sans-serif',
    "mono":  f'"JetBrains Mono","SF Mono",Menlo,{_CJK_SANS},monospace',
    "comic": f'"Space Grotesk","Helvetica Neue",Arial,{_CJK_SANS},sans-serif',
}
_STYLE_FONT_KIND = {
    "swiss": "sans", "bauhaus": "sans", "memphis": "sans", "vaporwave": "sans",
    "risograph": "sans", "glassmorphism": "sans", "claymorphism": "sans",
    "editorial": "serif", "artdeco": "serif", "noir": "serif", "cinematic": "serif",
    "watercolor": "serif", "cartographic": "serif",
    "terminal": "mono", "blueprint": "mono", "cyberpunk": "mono", "brutalism": "mono",
    "manga": "comic",
}

_STYLE_ALIASES = {"mangacomic": "manga", "comic": "manga", "cyberpunkneon": "cyberpunk", "neon": "cyberpunk",
                  "deco": "artdeco", "cinematicphotoreal": "cinematic", "photoreal": "cinematic",
                  "glass": "glassmorphism", "clay": "claymorphism", "riso": "risograph",
                  "international": "swiss", "flat": "swiss"}

def _style_key(style):
    """Normalize a style name to a STYLE_PRESETS key, tolerant of the catalog's long forms + spacing:
    'Art Deco'/'art_deco'/'art-deco'→'artdeco'; 'manga_comic'→'manga'; 'cyberpunk_neon'→'cyberpunk'."""
    k = "".join(c for c in (style or "").lower() if c.isalnum())
    k = _STYLE_ALIASES.get(k, k)
    return k if k in STYLE_PRESETS else ""


def derive_theme(out_dir, mode=None, accent=None, accent2=None, bg=None, style=None, brand_logo=None):
    _pre = STYLE_PRESETS.get(_style_key(style))
    _pmode, _pacc, _pacc2, _pvars = _pre if _pre else (None, None, None, {})
    if not accent and not brand_logo:                   # storyboard meta.brand.logo auto-seeds the accent
        brand_logo = _storyboard_brand_logo(out_dir)
    elif accent:
        # overriding a DECLARED brand with --accent is legitimate (a stated brand colour) — but say
        # so, or the override is indistinguishable from the seed never having fired
        try:
            if json.load(open(os.path.join(out_dir, "storyboard.json")))["meta"].get("brand"):
                print("[theme] explicit --accent overrides the meta.brand hue (drop --accent to seed from the logo)")
        except Exception:
            pass
    brand = _brand_accent(brand_logo) if (brand_logo and not accent) else None
    sampled = None if (accent and bg) else _sample_frames(out_dir)   # frames still drive light/dark
    if mode in ("light", "dark"):
        m = mode
    elif sampled:                                       # a frame-sampled BRAND palette is a hard constraint
        avg = sum(_lum(c) for c in sampled) / len(sampled)
        m = "light" if avg >= 0.5 else "dark"
    elif _pmode:                                        # else the chosen style's mode (noir=dark)
        m = _pmode
    else:
        m = "dark"
    # accent: explicit > brand-logo hue > sampled frames > style preset > neutral default. The brand
    # hue counts as SAMPLED — the >=3:1 lightness nudge below still applies (hue preserved).
    acc = (_hex2rgb(accent) if accent
           else (brand if brand
                 else (max(sampled, key=_sat) if sampled
                       else (_hex2rgb(_pacc) if _pacc else (76, 155, 232)))))
    if accent2:
        acc2 = _hex2rgb(accent2)
    elif _pacc2 and not accent and not brand and not sampled:   # style accent2 (unless explicit/brand recolors)
        acc2 = _hex2rgb(_pacc2)
    else:
        h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in acc])
        acc2 = tuple(c * 255 for c in colorsys.hls_to_rgb((h + 0.5) % 1.0, 0.5, max(0.5, s)))
    hue = _hue(acc)
    if bg:
        bgc = _hex2rgb(bg)
    elif m == "light":
        bgc = tuple(c * 255 for c in colorsys.hls_to_rgb(hue, 0.96, 0.18))
    else:
        bgc = tuple(c * 255 for c in colorsys.hls_to_rgb(hue, 0.09, 0.22))
    # anti-cliché: never a pure-black/white background — nudge to a temperature-tinted neutral. Applies to
    # an explicit --bg too (a screen-white #FFF becomes near-white #f8f7f4) — that honors its character; the
    # BUG this fixes is the contrast loop below repainting an explicit --bg to a WILDLY different colour.
    if _lum(bgc) <= 0.02:
        bgc = (14, 15, 17)        # #0e0f11
    elif _lum(bgc) >= 0.97:
        bgc = (248, 247, 244)     # #f8f7f4
    _dark_fg, _light_fg = (22, 20, 18), (240, 243, 248)
    if bg:
        # an explicit --bg is a CONSTRAINT — pick fg by whichever pole has higher contrast ON it, and NEVER
        # repaint the bg to reach contrast (so --bg #FFF --mode dark keeps a near-white bg + dark fg).
        fg = _dark_fg if _contrast(_dark_fg, bgc) >= _contrast(_light_fg, bgc) else _light_fg
        if _contrast(fg, bgc) < 7.0:
            fg = (0, 0, 0) if fg == _dark_fg else (255, 255, 255)
    else:
        fg = _dark_fg if m == "light" else _light_fg
        # enforce >=7:1 by pushing the DERIVED background away from fg (keep its hue); l->1 (light)/->0 (dark)
        h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in bgc])
        for _ in range(60):
            if _contrast(fg, bgc) >= 7.0:
                break
            l = min(1.0, l + 0.02) if m == "light" else max(0.0, l - 0.02)
            bgc = tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s))
        if _contrast(fg, bgc) < 7.0:
            fg = (0, 0, 0) if m == "light" else (255, 255, 255)
    # accent must clear 3:1 on the bg — it renders LARGE marks (.stat 240px, .tile .num 150px → WCAG
    # "large" text = 3:1). Nudge ONLY a SAMPLED accent's lightness (keep hue+sat), capped so a faithful
    # brand/topic hue is never washed out; an explicit `accent=` override is left exactly as given.
    if not accent:
        ha, la0, sa = colorsys.rgb_to_hls(*[c / 255 for c in acc]); la = la0
        for _ in range(30):
            if _contrast(acc, bgc) >= 3.0:
                break
            la = max(0.0, la - 0.02) if m == "light" else min(1.0, la + 0.02)
            if abs(la - la0) > 0.15:                 # cap — preserve the hue's character over full AA
                break
            acc = tuple(c * 255 for c in colorsys.hls_to_rgb(ha, la, sa))
        # UNCAPPED fallback: a light pastel can still be < 3:1 after the cap. Push toward the pole (shedding
        # a little saturation) until it clears 3:1 — a readable deep hue beats an unreadable 240px hero number.
        while _contrast(acc, bgc) < 3.0 and 0.0 < la < 1.0:
            la = max(0.0, la - 0.02) if m == "light" else min(1.0, la + 0.02)
            sa *= 0.97
            acc = tuple(c * 255 for c in colorsys.hls_to_rgb(ha, la, sa))
    # accent2 (the kicker on nearly every page, the .rule/.arrow, the focal timeline label) must ALSO clear
    # 3:1 — it was NEVER contrast-checked, so a low-contrast sampled accent2 rendered near-invisible chrome.
    # Same policy as accent: only nudge a SAMPLED accent2 (an explicit accent2= override is left as given).
    if not accent2:
        h2, l2_0, s2 = colorsys.rgb_to_hls(*[c / 255 for c in acc2]); l2 = l2_0
        while _contrast(acc2, bgc) < 3.0 and 0.0 < l2 < 1.0:
            l2 = max(0.0, l2 - 0.02) if m == "light" else min(1.0, l2 + 0.02)
            if abs(l2 - l2_0) > 0.18:                 # past a soft cap, shed saturation to reach 3:1
                s2 *= 0.97
            acc2 = tuple(c * 255 for c in colorsys.hls_to_rgb(h2, l2, s2))
    # text ON the accent fill: whichever of near-black / white has the higher TRUE contrast (the old
    # _lum<0.5 crossover mis-picked mid-tones — e.g. gave white on a teal accent at 2.06:1 vs black 4.37:1).
    on_accent = (17, 17, 17) if _contrast((17, 17, 17), acc) >= _contrast((255, 255, 255), acc) else (255, 255, 255)
    # text ON an accent2 (--rule) fill — a SEPARATE token: --on-accent was chosen for --accent and can
    # have the wrong polarity for accent2 (e.g. the .stepper 'done' number went white on a pale rule).
    on_accent2 = (17, 17, 17) if _contrast((17, 17, 17), acc2) >= _contrast((255, 255, 255), acc2) else (255, 255, 255)
    return {"mode": m, "bg": _hex(bgc), "surface": _hex(_mix(bgc, fg, 0.06)),
            "fg": _hex(fg), "muted": _hex(_mix(fg, bgc, 0.42)),
            "accent": _hex(acc), "accent2": _hex(acc2), "scrim": _hex(bgc),
            "on_accent": _hex(on_accent), "on_accent2": _hex(on_accent2),
            "style": _style_key(style) if _pre else "", "style_vars": _pvars}

def _deck_language(out_dir):
    """The deck's language from <out_dir>/storyboard.json (written by ingest/merge), '' if unknown."""
    try:
        return str(json.load(open(os.path.join(out_dir, "storyboard.json")))["meta"].get("language") or "").lower()[:2]
    except Exception:
        return ""


def write_theme_css(theme, path):
    sv = theme.get("style_vars") or {}
    style_css = ""
    if sv:   # style-hint vars. base.css/motifs.css AUTO-consume --radius/--font-display/--font-body/
             # --border-weight/--border-ink/--grid-strength; --motif-ink + --font-kind are AUTHOR/renderer
             # hints (which .bg-motif linework to draw; which bundled face the programmatic tier uses).
        kind = _STYLE_FONT_KIND.get(_style_key(theme.get('style', '')), "sans")
        disp, body = _FONT_FAMILIES[kind]
        num = _FONT_NUMBER[kind]
        grain = sv.get("grain") or _GRAIN_BY_INK.get(sv.get("ink"), "0")
        style_css = (f"  --style:{theme.get('style', '')}; --radius:{sv.get('radius', '14px')}; "
                     f"--border-weight:{sv.get('border', '1px')}; --border-ink:{sv.get('bink', 'rgba(127,127,127,.18)')};\n"
                     f"  --font-display:{disp}; --font-body:{body}; --font-number:{num}; --font-kind:{kind};\n"
                     f"  --grid-strength:{sv.get('grid', '.07')}; --motif-ink:{sv.get('ink', 'grid')}; --grain-amount:{grain};\n")
    # CJK display metrics: negative tracking is a LATIN display convention (it squeezes CJK glyphs)
    # and tight display line-heights (~1.08) set full-square CJK lines nearly touching. base.css
    # consumes these via calc(-.025em * var(--track-scale,1)) / var(--lh-display,1.08) — a Latin deck
    # keeps today's values, a CJK deck gets tracking 0 + air.
    _lang = theme.get("language") or _deck_language(os.path.dirname(os.path.abspath(path)))
    _cjk = _lang in ("zh", "ja", "ko")
    metrics_css = (f"  --track-scale:{0 if _cjk else 1}; --lh-display:{'1.28' if _cjk else '1.08'}; "
                   f"--lh-pull:{'1.34' if _cjk else '1.16'};\n")
    css = (":root{\n"
           + metrics_css
           + style_css
           + f"  --bg:{theme['bg']}; --surface:{theme['surface']}; --fg:{theme['fg']};\n"
           f"  --muted:{theme['muted']}; --accent:{theme['accent']}; --accent2:{theme['accent2']};\n"
           f"  --rule:var(--accent2); --scrim:{theme['scrim']}; --on-accent:{theme.get('on_accent', '#fff')};\n"
           f"  --on-accent2:{theme.get('on_accent2', '#fff')};\n}}\n")
    with open(path, "w") as f:
        f.write(css)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--mode"); ap.add_argument("--accent"); ap.add_argument("--accent2"); ap.add_argument("--bg")
    ap.add_argument("--style", default=None, help="a visual-styles.md key (swiss/editorial/glassmorphism/…)")
    ap.add_argument("--brand-logo", default=None,
                    help="brand logo png — its dominant non-neutral hue seeds the accent (counts as "
                         "sampled: the >=3:1 nudge still applies; an explicit --accent wins outright)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)                 # write theme.css even into a fresh out dir
    t = derive_theme(a.out_dir, a.mode, a.accent, a.accent2, a.bg, a.style, a.brand_logo)
    write_theme_css(t, os.path.join(a.out_dir, "theme.css"))
    print(f"[theme] mode={t['mode']} bg={t['bg']} fg={t['fg']} accent={t['accent']} accent2={t['accent2']}"
          + (f" style={t['style']}" if t.get('style') else ""))

if __name__ == "__main__":
    main()
