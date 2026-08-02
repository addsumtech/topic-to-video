"""Path A backstops: a cinematic stage element / 3D plane can carry an `html` form page (one of the HTML
tier's bespoke forms) that is screenshotted onto the plane texture at render — so a shot's content is a real
designed form (flow/scorecard/quadrant/…), not the one generic glass panel. The actual Chrome screenshot is
proven by a real render (see the Path A test), not a unit test; here we lock the plumbing + the gate."""
import inspect
import os

import render_remotion as rr
import storyboard as sb
import validate as v


def _card_board():
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion", "captions": False})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "audio/01.mp3"
    s["duration"] = 5.0
    s["stage"] = {"perspective": 1300, "elements": [
        {"id": "grid", "kind": "grid", "position": [0, 0, -1200]},
        {"id": "form", "kind": "card", "html": "pages/flow.html", "position": [0, 0, 0], "size": [1720, 968]}]}
    s["shots"] = [{"type": "HERO", "target": "form"}]
    d["slides"] = [s]
    return d


def test_card_html_jobs_collects_stage_and_planes():
    d = _card_board()
    d["slides"][0]["planes"] = [{"kind": "plane", "html": "pages/chart.html", "position": [0, 0, 0]}]
    htmls = sorted(h for h, _ in rr._html_card_jobs(d))
    assert htmls == ["pages/chart.html", "pages/flow.html"]


def test_card_html_jobs_skips_when_src_already_present():
    d = _card_board()
    d["slides"][0]["stage"]["elements"][1]["src"] = "x.png"
    assert rr._html_card_jobs(d) == []


def test_render_html_cards_noops_without_jobs(tmp_path):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion"})
    s = sb.new_scene(1, "cinematic", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 2.0
    s["stage"] = {"elements": [{"id": "a", "kind": "panel", "position": [0, 0, 0], "title": "X"}]}
    s["shots"] = [{"type": "HERO", "target": "a"}]
    d["slides"] = [s]
    rr._render_html_cards(d, str(tmp_path))                     # no `html` -> no Chrome, no error
    assert not os.path.isdir(os.path.join(str(tmp_path), ".cards"))


def test_html_threads_through_build_props(tmp_path):
    form = [e for e in rr.build_props(_card_board(), str(tmp_path))["scenes"][0]["stage"]["elements"]
            if e["id"] == "form"][0]
    assert form["html"] == "pages/flow.html"                   # survives to render (converted to src there)


def test_plane_html_threads_through_build_props(tmp_path):
    d = sb.new_storyboard({"fps": 30, "renderer": "remotion"})
    s = sb.new_scene(1, "cinematic3d", {}, narration="x")
    s["audio"] = "a"
    s["duration"] = 3.0
    s["planes"] = [{"kind": "plane", "html": "pages/x.html", "position": [0, 0, 0]}]
    d["slides"] = [s]
    assert rr.build_props(d, str(tmp_path))["scenes"][0]["planes"][0]["html"] == "pages/x.html"


def test_cdp_chrome_supports_supersample():
    import _cdp
    assert "device_scale" in inspect.signature(_cdp.Chrome.__init__).parameters, \
        "Path A needs a supersample option so a close-framed form stays razor-sharp"


def test_validate_knows_card_kind_and_flags_missing_page(tmp_path):
    errs, warns = [], []
    v._cinematic_fields(_card_board()["slides"][0], {"fps": 30}, str(tmp_path), "scene 1", errs, warns)
    assert not any("'card'" in w for w in warns), "card is a known element kind (no unknown-kind warning)"
    assert any("html card page" in e for e in errs), "a missing Path-A page must fail the gate"
