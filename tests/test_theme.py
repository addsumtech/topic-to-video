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
