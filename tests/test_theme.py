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
