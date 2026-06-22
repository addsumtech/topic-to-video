"""Derive a topic-fitting color theme and write theme.css. Samples the source slide frames when
present (PIL quantize + luminance -> light/dark + a vivid accent), else uses a passed topic palette.
Curated, contrast-safe derivation (not raw pixels). Deterministic: no randomness, no wall-clock."""
import argparse, colorsys, glob, os

def _hex(rgb): return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)
def _hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _lum(rgb):
    r, g, b = [c / 255 for c in rgb]; return 0.2126 * r + 0.7152 * g + 0.0722 * b
def _sat(rgb):
    r, g, b = [c / 255 for c in rgb]; return colorsys.rgb_to_hls(r, g, b)[2]
def _hue(rgb):
    r, g, b = [c / 255 for c in rgb]; return colorsys.rgb_to_hls(r, g, b)[0]
def _mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def _contrast(a, b):
    la, lb = _lum(a) + 0.05, _lum(b) + 0.05
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

def derive_theme(out_dir, mode=None, accent=None, accent2=None, bg=None):
    sampled = None if (accent and bg) else _sample_frames(out_dir)
    if mode in ("light", "dark"):
        m = mode
    elif sampled:
        avg = sum(_lum(c) for c in sampled) / len(sampled)
        m = "light" if avg >= 0.5 else "dark"
    else:
        m = "dark"
    acc = _hex2rgb(accent) if accent else (max(sampled, key=_sat) if sampled else (76, 155, 232))
    if accent2:
        acc2 = _hex2rgb(accent2)
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
    fg = (22, 20, 18) if m == "light" else (240, 243, 248)
    # enforce >=7:1 by pushing the background away from fg (keep its hue); l->1 (light) or ->0 (dark)
    h, l, s = colorsys.rgb_to_hls(*[c / 255 for c in bgc])
    for _ in range(60):
        if _contrast(fg, bgc) >= 7.0:
            break
        l = min(1.0, l + 0.02) if m == "light" else max(0.0, l - 0.02)
        bgc = tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s))
    if _contrast(fg, bgc) < 7.0:
        fg = (0, 0, 0) if m == "light" else (255, 255, 255)
    on_accent = (255, 255, 255) if _lum(acc) < 0.5 else (17, 17, 17)   # readable text on the accent fill
    return {"mode": m, "bg": _hex(bgc), "surface": _hex(_mix(bgc, fg, 0.06)),
            "fg": _hex(fg), "muted": _hex(_mix(fg, bgc, 0.42)),
            "accent": _hex(acc), "accent2": _hex(acc2), "scrim": _hex(bgc),
            "on_accent": _hex(on_accent)}

def write_theme_css(theme, path):
    css = (":root{\n"
           f"  --bg:{theme['bg']}; --surface:{theme['surface']}; --fg:{theme['fg']};\n"
           f"  --muted:{theme['muted']}; --accent:{theme['accent']}; --accent2:{theme['accent2']};\n"
           f"  --rule:var(--accent2); --scrim:{theme['scrim']}; --on-accent:{theme.get('on_accent', '#fff')};\n}}\n")
    with open(path, "w") as f:
        f.write(css)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--mode"); ap.add_argument("--accent"); ap.add_argument("--accent2"); ap.add_argument("--bg")
    a = ap.parse_args()
    t = derive_theme(a.out_dir, a.mode, a.accent, a.accent2, a.bg)
    write_theme_css(t, os.path.join(a.out_dir, "theme.css"))
    print(f"[theme] mode={t['mode']} bg={t['bg']} fg={t['fg']} accent={t['accent']} accent2={t['accent2']}")

if __name__ == "__main__":
    main()
