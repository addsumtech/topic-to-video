import os, re

SK = os.path.join(os.path.dirname(__file__), "..", "assets", "html")


def _read(name):
    with open(os.path.join(SK, name)) as f:
        return f.read()


def test_component_motion_classes_present_and_paused():
    css = _read("base.css")
    for cls in (".grow-w", ".grow-h", ".rail-fill", ".draw-down", ".settle",
                ".cross-dim", ".count-up", ".gauge.sweep"):
        assert cls in css, f"{cls} missing from base.css"
    # each meaning-bearing motion must be paused so seek.js can freeze it deterministically
    assert css.count("animation-play-state:paused") >= 8
    # the @property registrations the count-up / gauge sweep rely on
    assert "@property --count-n" in css and "@property --pdeg" in css


def test_component_motion_reduced_motion_overrides():
    rm = _read("reduced-motion.css")
    for cls in (".grow-w", ".grow-h", ".rail-fill", ".draw-down", ".settle",
                ".cross-dim", ".count-up", ".gauge.sweep"):
        assert cls in rm, f"{cls} missing a reduced-motion override (would keep moving / hide content)"


def test_vertical_css_shipped_and_forces_down_arrow():
    css = _read("vertical.css")
    assert "html, body" in css and "1080px" in css and "1920px" in css
    # the flow connector is forced DOWN regardless of the authored glyph (the ↓->← rotation bug)
    assert ".flow .arrow::after" in css and "2193" in css        # U+2193 down arrow
    assert "transform: none" in css                               # no rotate on the arrow
    assert "flex-direction: column" in css                        # archetypes restack to one column


def test_backdrops_are_aspect_general():
    m = _read("motifs.css")
    for block in re.finditer(r"\.bg-(?:photo|soft)\{[^}]*\}", m):
        assert "1920px" not in block.group(0), "backdrop still hardcodes a landscape 1920px size"
