#!/usr/bin/env python3
"""GENERALISATION engine for the cinematic tier: one deck ACCENT + a TEMPLATE key -> the per-beat colour
worlds (a deterministic transform of the accent, per references/cinematic-templates.md) + the aurora
backplane pages. So ANY topic re-skins ANY template with zero hand-authored colour — the fix for "偏纯色"
and for generalisation. Pure functions of (accent, template, beat_role); no I/O except aurora_page().

A "palette" is {bg, blobs:[hex...], accent, accent2, ink, kicker, light:'dark'|'light'}. The design-director
maps each beat to a semantic ROLE (spine/go/info/alert, stakes/thesis/climax/close, growth/attention, …);
the template turns (accent, role, i, n) into that beat's palette. Fixed grammar + one re-derived accent."""
import colorsys

# ── colour maths (HLS) ────────────────────────────────────────────────────────────────────────────────
def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _to_hex(r, g, b):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(c * 255))) for c in (r, g, b))


def _hls(h):
    r, g, b = _hex(h)
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return hh, ll, ss


def _from_hls(hh, ll, ss):
    return _to_hex(*colorsys.hls_to_rgb(hh % 1.0, max(0, min(1, ll)), max(0, min(1, ss))))


def rot(h, deg):
    hh, ll, ss = _hls(h); return _from_hls(hh + deg / 360.0, ll, ss)


def setl(h, ll):
    hh, _, ss = _hls(h); return _from_hls(hh, ll, ss)


def sets(h, ss):
    hh, ll, _ = _hls(h); return _from_hls(hh, ll, ss)


def scale(h, sfac=1.0, lfac=1.0, ladd=0.0):
    hh, ll, ss = _hls(h); return _from_hls(hh, ll * lfac + ladd, ss * sfac)


def complement(h):
    return rot(h, 180)


# ── per-template palette derivation (deterministic transform of the accent) ─────────────────────────────
def _command_surface(a, n):
    """Graphite substrate + one phosphor accent by command-lifecycle role."""
    go, info, alert = "#34D399", "#22D3EE", rot(a, 180) if _hls(a)[1] > 0.2 else "#F0407A"
    spine = setl(sets(a, 0.85), 0.62)
    roles = [spine, go, spine, info, spine, alert, spine]
    out = []
    for i in range(n):
        acc = roles[i % len(roles)]
        out.append({"bg": "#07090B", "blobs": [scale(acc, 0.9, ladd=-0.18), "#0F1317", setl(acc, 0.22)],
                    "accent": acc, "accent2": info, "ink": "#E7EDF3", "kicker": "#6B7680", "light": "dark"})
    return out


def _ignition_monument(a, n):
    """Void constant (A desat ~7% L, temperature kept); aurora ramps COOL->HOT across the arc."""
    void = setl(sets(a, 0.5), 0.055)
    out = []
    for i in range(n):
        t = i / max(1, n - 1)                                  # 0..1 arc position
        ll = 0.18 + t * 0.62                                   # smoulder -> white-hot
        hue = rot(a, (1 - t) * 22)                             # cool neighbour -> full chroma
        acc = setl(sets(hue, 0.6 + t * 0.35), ll)
        out.append({"bg": void, "blobs": [acc, scale(acc, 0.8, ladd=-0.1), setl(a, 0.30)],
                    "accent": acc, "accent2": setl(a, 0.7), "ink": "#F5F0E8", "kicker": setl(a, 0.7),
                    "light": "dark"})
    return out


def _aurora_bloom(a, n):
    """LIGHT film — pale mist ground + an analogous pastel triad from A; semantic by hue-shift."""
    h0 = _hls(a)[0] * 360
    tri = [rot(a, 0), rot(a, 35), rot(a, -35)]
    tri = [setl(sets(c, 0.72), 0.82) for c in tri]             # high-L pastels
    out = []
    for i in range(n):
        shift = 35 if i % 3 == 1 else (-35 if i % 3 == 2 else 0)
        acc = setl(sets(rot(a, shift), 0.7), 0.7)
        out.append({"bg": "#F7F8FB", "blobs": tri, "accent": acc, "accent2": tri[1],
                    "ink": "#14161C", "kicker": "#6B7280", "light": "light"})
    return out


def _liquid_model(a, n):
    """Duotone from A — colour IS the material. COOL pole (order) <-> WARM pole (formless)."""
    cool = setl(sets(rot(a, -20), 0.85), 0.55)                 # toward cyan/blue
    warm = setl(sets(rot(a, 150), 0.8), 0.6)                   # near-complement magenta/amber
    void = scale(a, 0.5, ladd=-0.02)
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        acc = warm if t < 0.5 else cool                        # raw -> resolved
        out.append({"bg": setl(void, 0.06), "blobs": [warm, cool, setl(a, 0.28)],
                    "accent": acc, "accent2": (cool if acc == warm else warm), "ink": "#F2F0FF",
                    "kicker": setl(cool, 0.75), "light": "dark"})
    return out


def _molten_ledger(a, n):
    """Obsidian + one molten metal ramp from A; loss beats chill to steel."""
    core = setl(sets(a, 0.8), 0.5)
    catch = setl(sets(a, 0.55), 0.85)
    steel = "#5C7A8C"
    out = []
    for i in range(n):
        loss = i % 4 == 3
        acc = steel if loss else core
        out.append({"bg": "#0A0B0F", "blobs": [setl(acc, 0.30), setl(acc, 0.12), catch if not loss else setl(steel, 0.6)],
                    "accent": acc, "accent2": catch, "ink": "#EDE7DC", "kicker": setl(acc, 0.6), "light": "dark"})
    return out


def _defrag(a, n):
    """Two-hue cool-structure / warm-alert FUI from A's hue."""
    struct = setl(sets(a, 0.9), 0.6)
    warn = setl(sets(rot(a, 165), 0.95), 0.58)
    bg = setl(sets(a, 0.45), 0.05)
    out = []
    for i in range(n):
        out.append({"bg": bg, "blobs": [scale(struct, 0.8, ladd=-0.25), bg, setl(struct, 0.18)],
                    "accent": struct, "accent2": warn, "ink": "#DCEBF5", "kicker": setl(struct, 0.55),
                    "light": "dark"})
    return out


def _doorway_gallery(a, n):
    """Warm museum WALLS (ground moves), accent muted one step; each 'room' a different wall tone."""
    acc = scale(a, 0.72)
    rooms = ["#ede6da", "#e9dfcc", "#dce0d6", "#241f1a"]      # neutral / ochre / grey-green / dark alcove
    out = []
    for i in range(n):
        wall = rooms[i % len(rooms)]
        light = "light" if sum(_hex(wall)) / 3 > 0.5 else "dark"
        ink = "#211c17" if light == "light" else "#ede6da"
        out.append({"bg": wall, "blobs": [setl(acc, 0.5), scale(wall, 1.0, ladd=-0.05), setl(acc, 0.42)],
                    "accent": acc, "accent2": setl(a, 0.6), "ink": ink, "kicker": scale(ink, 0.55), "light": light})
    return out


def _rakelight(a, n):
    """Obsidian — colour only where light strikes. Material-accent = A ~50% chroma at lit value; cool backlight."""
    mat = setl(sets(a, 0.5), 0.62)
    back = scale(rot(a, 160), 0.6, ladd=-0.1)
    out = []
    for i in range(n):
        out.append({"bg": "#0a0b0d", "blobs": [setl(mat, 0.22), "#141618", setl(back, 0.2)],
                    "accent": mat, "accent2": back, "ink": "#e8eaed", "kicker": setl(mat, 0.55), "light": "dark"})
    return out


def _exploded_schematic(a, n):
    """Blueprint navy; LINE = A rotated 70% toward cyan (~200°) low-chroma; HOT active = A full chroma."""
    ah = _hls(a)[0]
    line = _from_hls(ah + (200 / 360.0 - ah) * 0.7, 0.5, 0.52)
    hot = setl(sets(a, 0.9), 0.55)
    out = []
    for i in range(n):
        out.append({"bg": "#0b1a2b", "blobs": [setl(line, 0.25), "#0b1a2b", setl(line, 0.16)],
                    "accent": hot, "accent2": line, "ink": "#dce9f5", "kicker": setl(line, 0.6), "light": "dark"})
    return out


def _default(a, n):
    """A generic vivid aurora from A + two neighbours (the b1-style world) when a template has no bespoke map."""
    b1, b2 = rot(a, 28), rot(a, -32)
    out = []
    for i in range(n):
        acc = setl(sets([a, b1, b2][i % 3], 0.75), 0.62)
        out.append({"bg": scale(a, 0.55, ladd=-0.03), "blobs": [setl(a, 0.5), setl(b1, 0.5), setl(b2, 0.42)],
                    "accent": acc, "accent2": setl(b1, 0.6), "ink": "#F2F2F8", "kicker": setl(a, 0.7),
                    "light": "dark"})
    return out


_TEMPLATES = {
    "command-surface": _command_surface, "ignition-monument": _ignition_monument,
    "aurora-bloom": _aurora_bloom, "liquid-model": _liquid_model, "molten-ledger": _molten_ledger,
    "defrag": _defrag, "doorway-gallery": _doorway_gallery, "rakelight": _rakelight,
    "exploded-schematic": _exploded_schematic,
}
TEMPLATE_KEYS = set(_TEMPLATES)                                # all 9 now have a bespoke palette (no _default fallback)


def derive(accent, template, n_beats):
    """Return a list of n_beats per-beat palettes for `template`, all a deterministic transform of `accent`.
    Unknown/not-yet-mapped templates fall back to a vivid default aurora (still generalised from the accent)."""
    if not (isinstance(accent, str) and accent.lstrip("#")):
        raise ValueError("cine_palette.derive: accent must be a #hex, got %r" % (accent,))
    fn = _TEMPLATES.get(str(template), _default)
    return fn(accent, max(1, int(n_beats)))


# ── aurora backplane page generator (a designed colour-world page, per palette) ─────────────────────────
def aurora_css(pal):
    """The 4×radial + conic aurora backplane CSS for one palette (matches the hand-authored recipe, now
    GENERATED)."""
    blobs = (pal.get("blobs") or [pal["accent"]])[:4]
    spots = [(20, 30, 48, 58), (80, 68, 46, 60), (62, 20, 38, 56), (30, 84, 40, 60)]
    rad = ",\n".join("radial-gradient(%d%% %d%% at %d%% %d%%, %s 0%%, transparent %d%%)"
                     % (w, w, x, y, blobs[i % len(blobs)], f) for i, (x, y, w, f) in enumerate(spots))
    conic = ",".join(blobs + [blobs[0]])
    op = ".62" if pal.get("light") == "light" else ".95"
    return (".aurora{position:absolute;inset:0;overflow:hidden;background:%s}"
            ".aurora::before{content:'';position:absolute;inset:-24%%;background:%s;filter:blur(62px) saturate(1.4);opacity:%s}"
            ".aurora::after{content:'';position:absolute;inset:-34%%;background:conic-gradient(from 130deg at 60%% 40%%,%s);filter:blur(94px) saturate(1.45);opacity:.3;mix-blend-mode:screen}"
            % (pal["bg"], rad, op, conic))


def aurora_page(pal, skill_dir, out_dir, title="", kicker="", grad_words="", sub=""):
    """Return a full HTML aurora colour-world page string (a monolith by default). Content is optional — the
    director fills title/kicker/sub + gradient words per the beat. base.css/theme.css linked absolute."""
    ink, acc, acc2, kc = pal["ink"], pal["accent"], pal.get("accent2", pal["accent"]), pal.get("kicker", pal["ink"])
    grad = "linear-gradient(96deg,%s,%s)" % (acc2, acc)
    body = ("<div class='aurora'></div>"
            "<div class='vig'></div>"
            "<div class='wrap'>"
            + ("<div class='k'>%s</div>" % kicker if kicker else "")
            + "<div class='rule'></div>"
            + ("<h1 class='big'>%s<span class='g'>%s</span></h1>" % (title, grad_words) if (title or grad_words) else "")
            + ("<div class='sub'>%s</div>" % sub if sub else "")
            + "</div>")
    css = (aurora_css(pal)
           + ".vig{position:absolute;inset:0;background:radial-gradient(120%% 120%% at 50%% 45%%,transparent 44%%,rgba(3,4,10,.5) 100%%)}"
           + ".wrap{position:absolute;inset:0;z-index:3;display:flex;flex-direction:column;justify-content:center;padding:150px 200px 200px}"
           + ".k{font-size:29px;letter-spacing:.30em;text-transform:uppercase;font-weight:600;color:%s}" % kc
           + ".rule{width:112px;height:5px;border-radius:3px;background:%s;margin:26px 0 40px;box-shadow:0 0 26px %s99}" % (grad, acc)
           + ".big{font-size:150px;line-height:1.02;font-weight:800;letter-spacing:-.02em;margin:0;color:%s}" % ink
           + ".sub{font-size:38px;margin-top:34px;line-height:1.4;color:%s}" % kc
           + ".g{background-image:%s;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}" % grad)
    html = ("<!doctype html><html lang=\"zh\"><head><meta charset=\"utf-8\">\n"
            "<link rel=\"stylesheet\" href=\"file://%s/assets/html/base.css\">\n"
            "<link rel=\"stylesheet\" href=\"file://%s/theme.css\">\n"
            "<style>html,body{margin:0;height:100%%;overflow:hidden}%s</style></head><body>\n%s\n"
            "<script src=\"file://%s/assets/html/seek.js\"></script></body></html>\n"
            % (skill_dir, out_dir, css, body, skill_dir))
    return html


# ── the STRUCTURAL half: each template's beat ARC + signature + seam, as DATA (not prose) ────────────────
# So a template contributes STRUCTURE (which archetype per beat, the through-line, the transition), turning
# "template-driven" from colour-only into real. Arcs mirror references/cinematic-templates.md.
_ARCS = {
    "command-surface":   {"arc": ["hero-on-void", "metaphor-mechanic", "manifesto-monolith", "process-flow", "data-materializes", "hero-on-void"], "transition": "collapse-aperture", "signature": "the blinking caret / prompt line"},
    "ignition-monument": {"arc": ["manifesto-monolith", "metaphor-mechanic", "manifesto-monolith", "data-materializes", "quote-testament", "hero-on-void"], "transition": "match-cut", "signature": "the hot line"},
    "molten-ledger":     {"arc": ["device-focus", "hero-on-void", "data-materializes", "metaphor-mechanic", "metric-wall", "hero-on-void"], "transition": "collapse-to-line", "signature": "the molten ledger line"},
    "aurora-bloom":      {"arc": ["hero-on-void", "data-materializes", "metaphor-mechanic", "metric-wall", "system-map", "hero-on-void"], "transition": "aperture-bloom", "signature": "light as medium"},
    "liquid-model":      {"arc": ["hero-on-void", "manifesto-monolith", "system-map", "comparison-split", "data-materializes", "hero-on-void"], "transition": "liquid-dissolve", "signature": "the one iridescent material"},
    "defrag":            {"arc": ["hero-on-void", "system-map", "metric-wall", "data-materializes", "comparison-split", "manifesto-monolith"], "transition": "boot", "signature": "the reticle + horizon-grid"},
    "doorway-gallery":   {"arc": ["hero-on-void", "device-focus", "manifesto-monolith", "metric-wall", "metaphor-mechanic", "quote-testament"], "transition": "wipe", "signature": "the frame + the moving light"},
    "rakelight":         {"arc": ["hero-on-void", "turntable-material", "device-focus", "exploded-assemble", "metaphor-mechanic", "manifesto-monolith"], "transition": "blackout-rake", "signature": "the travelling blade of light"},
    "exploded-schematic": {"arc": ["device-focus", "exploded-assemble", "device-focus", "metric-wall", "comparison-split", "exploded-assemble"], "transition": "explode-assemble", "signature": "the measurement HUD"},
}


def storyboard_skeleton(template, accent, n_beats):
    """The INSTANTIATOR: return per-beat STRUCTURAL specs from the template's arc + generated palettes, so a
    template contributes archetype/signature/transition, not just colour. The arc is sampled proportionally so
    a shorter/longer film keeps the opening→climax→close shape. The design-director fills each beat's content
    (title/kicker/…) and reads `archetype`/`palette`/`transition`/`is_signature` off each returned dict."""
    tpl = str(template)
    spec = _ARCS.get(tpl, {"arc": ["hero-on-void"], "transition": "dip", "signature": "hero"})
    arc = spec["arc"]
    pals = derive(accent, tpl, n_beats)
    out = []
    for i in range(max(1, int(n_beats))):
        j = round(i * (len(arc) - 1) / max(1, n_beats - 1)) if n_beats > 1 else 0
        out.append({"beat": i, "archetype": arc[min(j, len(arc) - 1)], "palette": pals[i],
                    "transition": spec["transition"] if i > 0 else "none",
                    "is_signature": (i == 0 or i == n_beats - 1),
                    "signature_element": spec["signature"]})
    return out


if __name__ == "__main__":                                    # tiny CLI: preview a template's palette ramp
    import sys, json
    acc = sys.argv[1] if len(sys.argv) > 1 else "#7c5cff"
    tpl = sys.argv[2] if len(sys.argv) > 2 else "ignition-monument"
    print(json.dumps(derive(acc, tpl, 7), indent=2, ensure_ascii=False))
