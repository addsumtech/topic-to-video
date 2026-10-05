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


def test_offcenter_band_primitive_present():
    css = _read("base.css")
    for cls in (".stage.frame-left", ".stage.frame-right", ".stage.thirds"):
        assert cls in css, f"{cls} off-center band missing from base.css"
    # left/right park the content in ONE band (a capped width leaves the deliberate void)
    assert "max-width:58%" in css.replace(" ", "")
    # 9:16 widens the band so it isn't a cramped gutter on the narrow column
    v = _read("vertical.css")
    assert "frame-left" in v and "82%" in v


def test_vertical_fill_is_an_opt_in_lever_for_thin_pages():
    # a thin 9:16 page can opt into `class="stage fill"` to step the type scale up and spread the
    # stack through the zone, instead of a page-by-page hand-rolled font-size override. It must be
    # scoped under `.stage.fill` (opt-in) — never bare `.stage`/`.title`/etc, which would change
    # every existing page's fill behaviour without anyone asking for it.
    v = _read("vertical.css").replace(" ", "")
    assert ".stage.fill{" in v
    for cls in (".stage.fill.title{", ".stage.fill.sub{", ".stage.fill.label{"):
        assert cls in v, f"{cls} missing from vertical.css"
    # it must actually step SIZES UP past the phone-first baseline a few lines above, not just restyle
    base_title = re.search(r"(?<!\.fill)\.title\{font-size:(\d+)px", v)
    fill_title = re.search(r"\.stage\.fill\.title\{font-size:(\d+)px", v)
    assert base_title and fill_title
    assert int(fill_title.group(1)) > int(base_title.group(1))
    # spreads the stack through the zone rather than pooling it under the top anchor
    assert "justify-content:space-between" in re.search(r"\.stage\.fill\{[^}]*\}", v).group(0)


def test_grain_primitive_present_and_gated():
    m = _read("motifs.css")
    # a fixed-seed feTurbulence overlay, auto-applied via body::after, GATED by --grain-amount (0 = off)
    assert "body::after" in m and "feTurbulence" in m
    assert "opacity:var(--grain-amount,0)" in m.replace(" ", "")
    assert "seed=" in m and "fractalNoise" in m          # deterministic seed, film-grain noise type
    assert "pointer-events:none" in m.replace(" ", "")
    assert "body.no-grain::after" in m                   # data-heavy pages can opt out
