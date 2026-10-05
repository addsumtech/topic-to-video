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
    assert snapshot._geometry_issues(info, {"captions": False}, 1920, 1080) == []
    assert len(snapshot._geometry_issues(info, {}, 1920, 1080)) == 1


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


class _StubChrome:
    def __init__(self, probe_raises=False):
        self.shots, self.closed, self.probe_raises = [], False, probe_raises

    def shot(self, url, out):
        self.shots.append(url)
        from PIL import Image
        Image.new("RGB", (8, 8), "#333").save(out, "JPEG")   # CDP path really writes JPEG bytes

    def close(self):
        self.closed = True


def test_probed_happy_path_shape_and_png_transcode(tmp_path, monkeypatch):
    page = tmp_path / "p.html"; page.write_text("<html><body>x</body></html>")
    out = str(tmp_path / "o.png")
    stub = _StubChrome()
    monkeypatch.setattr(snapshot.keyframe_qa, "_open_cdp", lambda meta, W, H: stub)
    info = {"worst": 0, "clip": 0, "textlen": 40, "cbot": 800, "ctop": 100, "cleft": 100, "cright": 900}
    monkeypatch.setattr(snapshot.keyframe_qa, "_dom_probe", lambda c: info)
    r = snapshot.shoot(str(page), out)
    assert r["probed"] is True and r["issues"] == [] and r["info"] is info
    assert stub.closed                                        # chrome released
    assert open(out, "rb").read(4) == b"\x89PNG"              # JPEG bytes transcoded to real PNG

def test_probe_exception_still_closes_chrome(tmp_path, monkeypatch):
    page = tmp_path / "p.html"; page.write_text("<html><body>x</body></html>")
    stub = _StubChrome()
    monkeypatch.setattr(snapshot.keyframe_qa, "_open_cdp", lambda meta, W, H: stub)
    def boom(c): raise RuntimeError("probe died")
    monkeypatch.setattr(snapshot.keyframe_qa, "_dom_probe", boom)
    import pytest
    with pytest.raises(RuntimeError):
        snapshot.shoot(str(page), str(tmp_path / "o.png"))
    assert stub.closed                                        # try/finally held

def test_blank_page_fails_the_contest_floor(tmp_path, monkeypatch):
    # a page whose reveal never fired (empty text, no box, no bleed) must NOT pass as "floor clean"
    page = tmp_path / "p.html"; page.write_text("<html><body></body></html>")
    monkeypatch.setattr(snapshot.keyframe_qa, "_open_cdp", lambda meta, W, H: _StubChrome())
    blank_info = {"worst": 0, "clip": 0, "textlen": 0, "cbot": -1e9, "ctop": 1e9, "cleft": 1e9, "cright": 0}
    monkeypatch.setattr(snapshot.keyframe_qa, "_dom_probe", lambda c: blank_info)
    r = snapshot.shoot(str(page), str(tmp_path / "o.png"))
    assert any("BLANK" in i for i in r["issues"]) and snapshot._exit_code(r) == 2


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


def test_motion_snippet_signature_and_scale_guard():
    # finalists are judged in MOTION: snippet sweeps p=0..1; the encode must force the canonical WxH
    # (headless viewports can come up short → odd heights break yuv420p/x264)
    import inspect
    params = inspect.signature(snapshot.motion_snippet).parameters
    for k in ("page", "out_mp4", "seconds", "fps", "vertical"):
        assert k in params, k
    src = inspect.getsource(snapshot.motion_snippet)
    assert 'f"scale={W}:{H}"' in src


def test_cdp_viewport_is_pinned():
    # --window-size alone lets new-headless subtract ~87px of chrome from the viewport (1920x993
    # captures: bottom crop + 1080/993 vertical stretch at encode). The device-metrics override is
    # the root fix — guard it against regression.
    import os
    src = open(os.path.join(os.path.dirname(snapshot.__file__), "_cdp.py")).read()
    assert "Emulation.setDeviceMetricsOverride" in src
    assert '"width": W, "height": H' in src
