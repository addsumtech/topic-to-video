import os
from PIL import Image
import theme

def _frame(path, rgb):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (160, 90), rgb).save(path)

def test_light_frames_give_light_mode(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (245, 240, 228))   # warm near-white
    t = theme.derive_theme(str(tmp_path))
    assert t["mode"] == "light"
    assert theme._lum(theme._hex2rgb(t["bg"])) > 0.6                # bg is light

def test_dark_frames_give_dark_mode(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (12, 16, 24))
    t = theme.derive_theme(str(tmp_path))
    assert t["mode"] == "dark"
    assert theme._lum(theme._hex2rgb(t["bg"])) < 0.4

def test_contrast_enforced(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (245, 240, 228))
    t = theme.derive_theme(str(tmp_path))
    assert theme._contrast(theme._hex2rgb(t["fg"]), theme._hex2rgb(t["bg"])) >= 7.0

def test_overrides_and_no_frames(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="dark", accent="#4C9Be8")   # no frames
    assert t["mode"] == "dark" and t["accent"].lower() == "#4c9be8"

def test_writes_theme_css_with_all_vars(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (200, 70, 30))
    t = theme.derive_theme(str(tmp_path))
    p = str(tmp_path / "theme.css"); theme.write_theme_css(t, p)
    css = open(p).read()
    for v in ("--bg", "--surface", "--fg", "--muted", "--accent", "--accent2", "--rule", "--scrim"):
        assert v in css
    assert ":root" in css

def test_deterministic(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (200, 70, 30))
    assert theme.derive_theme(str(tmp_path)) == theme.derive_theme(str(tmp_path))

def test_dark_frame_contrast_enforced(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (40, 44, 12))   # tricky dark yellow-green hue
    t = theme.derive_theme(str(tmp_path))
    assert t["mode"] == "dark"
    assert theme._contrast(theme._hex2rgb(t["fg"]), theme._hex2rgb(t["bg"])) >= 7.0

def test_pure_black_bg_is_tinted(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="dark", accent="#4C9Be8", bg="#000000")
    assert t["bg"].lower() != "#000000" and t["bg"].lower() == "#0e0f11"

def test_pure_white_bg_is_tinted(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="light", accent="#c0461f", bg="#ffffff")
    assert t["bg"].lower() != "#ffffff" and t["bg"].lower() == "#f8f7f4"

def test_clamped_bg_still_contrast_safe(tmp_path):
    t = theme.derive_theme(str(tmp_path), mode="dark", accent="#4C9Be8", bg="#000000")
    assert theme._contrast(theme._hex2rgb(t["fg"]), theme._hex2rgb(t["bg"])) >= 7.0


# ── A: gamma-correct WCAG contrast + on-accent argmax + sampled-accent ≥3:1 nudge ─────
def test_contrast_is_gamma_correct_wcag():
    # canonical AA color #767676 on white is exactly 4.54:1 (the simple formula gave ~2.05)
    c = theme._contrast((0x76, 0x76, 0x76), (255, 255, 255))
    assert 4.45 <= c <= 4.65

def test_on_accent_picks_higher_contrast_choice(tmp_path):
    for a in ("#2f7d6a", "#c1472e", "#e8590c", "#4c9be8", "#ffd166", "#0b6e99"):
        t = theme.derive_theme(str(tmp_path), mode="dark", accent=a)
        acc = theme._hex2rgb(a); on = theme._hex2rgb(t["on_accent"])
        other = (255, 255, 255) if on == (17, 17, 17) else (17, 17, 17)
        assert theme._contrast(on, acc) >= theme._contrast(other, acc)   # argmax, not a 0.5 guess

def test_sampled_bright_accent_nudged_for_legibility(tmp_path):
    raw = (250, 220, 60)                                    # bright yellow -> light mode, low contrast
    _frame(str(tmp_path / "frames" / "01.png"), raw)
    t = theme.derive_theme(str(tmp_path))
    acc = theme._hex2rgb(t["accent"]); bg = theme._hex2rgb(t["bg"])
    assert theme._contrast(acc, bg) >= theme._contrast(raw, bg)          # nudged toward legibility

def test_override_accent_never_nudged(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (250, 220, 60))          # frames present…
    t = theme.derive_theme(str(tmp_path), accent="#ffdd00")              # …but accent is an explicit override
    assert t["accent"].lower() == "#ffdd00"                              # left exactly as given (faithful)


def test_accent_and_accent2_clear_3to1_on_pastel(tmp_path):
    # a pale/pastel deck must not yield a low-contrast accent (240px hero) or accent2 (kicker/.rule)
    _frame(str(tmp_path / "frames" / "01.png"), (238, 224, 236))
    _frame(str(tmp_path / "frames" / "02.png"), (240, 232, 220))
    for mode in ("light", "dark"):
        t = theme.derive_theme(str(tmp_path), mode=mode)
        bg = theme._hex2rgb(t["bg"])
        assert theme._contrast(theme._hex2rgb(t["accent"]), bg) >= 3.0 - 0.05, (mode, "accent")
        assert theme._contrast(theme._hex2rgb(t["accent2"]), bg) >= 3.0 - 0.05, (mode, "accent2")


def test_explicit_bg_not_repainted_to_different_color(tmp_path):
    # an explicit --bg must keep its CHARACTER (near-white/near-black), not get repainted to a wild colour
    t = theme.derive_theme(str(tmp_path), mode="dark", bg="#FFFFFF")
    r, g, b = theme._hex2rgb(t["bg"])
    assert r > 235 and g > 235 and b > 235, t["bg"]                 # still near-white (not dark brown)
    assert theme._contrast(theme._hex2rgb(t["fg"]), (r, g, b)) >= 7.0   # readable dark fg on it


def test_style_preset_seeds_palette_and_keeps_wcag(tmp_path):
    for st in ("swiss", "noir", "terminal", "artdeco"):
        t = theme.derive_theme(str(tmp_path), style=st)
        bg = theme._hex2rgb(t["bg"])
        assert t["style"] == st and t["style_vars"]
        assert theme._contrast(theme._hex2rgb(t["fg"]), bg) >= 7.0 - 0.05
        assert theme._contrast(theme._hex2rgb(t["accent"]), bg) >= 3.0 - 0.05
    # explicit accent still overrides a style preset
    t2 = theme.derive_theme(str(tmp_path), style="swiss", accent="#22aa55")
    assert t2["accent"].lower() == "#22aa55"

def test_no_style_is_backward_compatible(tmp_path):
    import os as _os
    theme.write_theme_css(theme.derive_theme(str(tmp_path)), str(tmp_path / "t.css"))
    css = open(str(tmp_path / "t.css")).read()
    assert "--style:" not in css and "--radius:" not in css   # no style vars emitted without a style

def test_style_css_emits_hint_vars(tmp_path):
    theme.write_theme_css(theme.derive_theme(str(tmp_path), style="brutalism"), str(tmp_path / "b.css"))
    css = open(str(tmp_path / "b.css")).read()
    for v in ("--style:brutalism", "--radius:", "--border-weight:", "--font-display:", "--font-body:",
              "--font-kind:", "--motif-ink:", "--grain-amount:"):
        assert v in css, v


def test_grain_amount_wires_texture_styles_not_clean_ones(tmp_path):
    # the film-grain amount is the consumer the `ink` metadata (halftone/…) never had: textured styles
    # get grain, clean/grid styles stay crisp at 0
    def amt(style):
        p = tmp_path / f"{style}.css"
        theme.write_theme_css(theme.derive_theme(str(tmp_path), style=style), str(p))
        line = [l for l in open(str(p)) if "--grain-amount:" in l][0]
        return line.split("--grain-amount:")[1].split(";")[0].strip()
    assert amt("risograph") == ".16"          # ink:'halftone' now HAS a consumer
    assert amt("manga") == ".13"
    assert float(amt("noir")) > 0
    for clean in ("swiss", "glassmorphism", "cyberpunk"):
        assert amt(clean) == "0", clean


def test_style_type_maps_to_bundled_face(tmp_path):
    # the picked style drives the TYPE: a display face that evokes the style + a readable body face + the
    # --font-kind the programmatic tier reads. Each stack keeps a CJK + generic fallback.
    cases = {"manga": ("comic", "Bangers"), "swiss": ("sans", "Space Grotesk"),
             "editorial": ("serif", "Playfair Display"), "terminal": ("mono", "JetBrains Mono"),
             "cyberpunk": ("mono", "JetBrains Mono"), "artdeco": ("serif", "Playfair Display")}
    for st, (kind, face) in cases.items():
        p = tmp_path / f"{st}.css"
        theme.write_theme_css(theme.derive_theme(str(tmp_path), style=st), str(p))
        css = open(str(p)).read()
        assert f"--font-kind:{kind}" in css, st
        import re
        disp = re.search(r"--font-display:([^;]+);", css).group(1).strip()
        assert face in disp, (st, disp)                       # display face evokes the style
        assert ("PingFang" in disp or "Songti" in disp)       # CJK fallback preserved
        assert disp.endswith(("sans-serif", "serif", "monospace"))   # generic fallback last

def test_font_number_is_clean_figure_face(tmp_path):
    # NUMBERS get a dedicated clean lining/tabular figure face (--font-number), distinct from the
    # display face on serif/comic decks (where Playfair/Bangers digits render unevenly) — always a
    # Space-Grotesk-first (or mono JetBrains) stack, with CJK + generic fallback preserved.
    import re
    for st, expect in {"editorial": "Space Grotesk", "manga": "Space Grotesk",
                       "swiss": "Space Grotesk", "terminal": "JetBrains Mono",
                       "blueprint": "JetBrains Mono"}.items():
        p = tmp_path / f"{st}.css"
        theme.write_theme_css(theme.derive_theme(str(tmp_path), style=st), str(p))
        css = open(str(p)).read()
        num = re.search(r"--font-number:([^;]+);", css)
        assert num, f"{st}: no --font-number emitted"
        num = num.group(1).strip()
        assert num.startswith(f'"{expect}"'), (st, num)          # clean figure face leads the stack
        assert ("PingFang" in num or "Hiragino" in num)          # CJK fallback preserved
        # on a SERIF/COMIC deck the number face DIFFERS from the display face (that IS the fix)
        if st in ("editorial", "manga"):
            disp = re.search(r"--font-display:([^;]+);", css).group(1).strip()
            assert num != disp, f"{st}: --font-number should differ from the ornate display face"

def test_font_kind_covers_every_style():
    # no style may fall through to the "sans" default silently — each of the 18 is explicitly typed
    for st in theme.STYLE_PRESETS:
        assert st in theme._STYLE_FONT_KIND, st


def test_style_long_keys_resolve(tmp_path):
    for k in ("cyberpunk_neon", "art_deco", "manga_comic", "cinematic_photoreal", "Art Deco"):
        t = theme.derive_theme(str(tmp_path), style=k)
        assert t["style"] and t["style_vars"], k          # the 4 catalog long-keys must not silently no-op
    assert theme._style_key("cyberpunk_neon") == "cyberpunk"

def test_brand_frames_outrank_style_preset(tmp_path):
    _frame(str(tmp_path / "frames" / "01.png"), (240, 232, 220))   # light BRAND frames
    t = theme.derive_theme(str(tmp_path), style="noir")            # noir=dark, but brand=light wins
    assert t["mode"] == "light"

def test_border_ink_emitted_for_brutalism(tmp_path):
    theme.write_theme_css(theme.derive_theme(str(tmp_path), style="brutalism"), str(tmp_path / "b.css"))
    assert "--border-ink:#111111" in open(str(tmp_path / "b.css")).read()


def test_theme_emits_cjk_display_metrics(tmp_path):
    import json as _json
    zh = tmp_path / "zh"; en = tmp_path / "en"
    for d, lang in ((zh, "zh"), (en, "en")):
        d.mkdir()
        (d / "storyboard.json").write_text(_json.dumps({"meta": {"language": lang}, "slides": []}))
        theme.write_theme_css(theme.derive_theme(str(d)), str(d / "theme.css"))
    zh_css = (zh / "theme.css").read_text(); en_css = (en / "theme.css").read_text()
    assert "--track-scale:0" in zh_css and "--lh-display:1.28" in zh_css   # CJK: no negative tracking + air
    assert "--track-scale:1" in en_css and "--lh-display:1.08" in en_css   # Latin: unchanged defaults
