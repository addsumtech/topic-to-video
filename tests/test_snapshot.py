import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import keyframe_qa
import snapshot


def test_snapshot_floor_is_keyframe_qas():
    # ONE source of truth: snapshot's floor verdict must BE keyframe_qa's classifier (no drifted copy)
    assert snapshot._geometry_issues is keyframe_qa._geometry_issues


def test_shoot_signature_covers_contest_needs():
    import inspect
    params = inspect.signature(snapshot.shoot).parameters
    for p in ("page", "out_png", "p", "vertical", "captions", "meta"):
        assert p in params, p
    assert params["p"].default == 1.0                 # settled state — what the floor is calibrated for
    assert params["captions"].default is True         # overlay decks are the default; --no-captions opts out


def test_no_captions_disables_caption_zone_check():
    # shoot(captions=False) sets meta.captions False, which _geometry_issues honours — verify the seam
    info = {"worst": 0, "clip": 0, "cbot": 1050, "ctop": 100, "cleft": 100, "cright": 1800}
    assert snapshot._geometry_issues(info, {"captions": False}, 1080) == []
    assert len(snapshot._geometry_issues(info, {}, 1080)) == 1


def test_missing_page_raises_before_chrome():
    # Chrome renders a real ERR_FILE_NOT_FOUND page that PROBES CLEAN — a nonexistent path must fail
    # FAST (exit 1 via main), never reach Chrome and return a false floor-pass
    import pytest
    with pytest.raises(FileNotFoundError):
        snapshot.shoot("/definitely/not/a/real/page.html", "/tmp/x.png")


def test_exit_code_contract():
    # 0 = clean · 2 = floor issues · 3 = rendered but NOT probed (unusable as a contest verdict)
    assert snapshot._exit_code({"issues": [], "probed": True}) == 0
    assert snapshot._exit_code({"issues": ["x"], "probed": True}) == 2
    assert snapshot._exit_code({"issues": [], "probed": False}) == 3


def test_unprobed_fallback_reports_itself(tmp_path, monkeypatch):
    # CDP-failed-but-screenshot-works must return probed:False (-> exit 3), never a silent clean verdict
    page = tmp_path / "p.html"
    page.write_text("<html><body>x</body></html>")
    monkeypatch.setattr(snapshot.keyframe_qa, "_open_cdp", lambda meta, W, H: None)
    import scenes
    shots = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, out, W, H, meta: shots.append(url))
    r = snapshot.shoot(str(page), str(tmp_path / "o.png"), p=0.5)
    assert r["probed"] is False and r["issues"] == [] and "note" in r
    assert r["p"] == 0.5 and r["advisory"] is True      # mid-state verdicts are marked, not silent
    assert shots and "?p=0.5" in shots[0]


def test_url_is_percent_encoded(tmp_path, monkeypatch):
    # a '#' in the filename must not truncate the file:// URL (Chrome would load its error page and
    # the probe would return a clean verdict for a frame that never rendered)
    page = tmp_path / "pa#ge.html"
    page.write_text("<html><body>x</body></html>")
    monkeypatch.setattr(snapshot.keyframe_qa, "_open_cdp", lambda meta, W, H: None)
    import scenes
    shots = []
    monkeypatch.setattr(scenes, "_chrome_shot", lambda url, out, W, H, meta: shots.append(url))
    snapshot.shoot(str(page), str(tmp_path / "o.png"))
    assert shots and "%23" in shots[0] and "#" not in shots[0].split("?p=")[0]
