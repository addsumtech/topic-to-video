"""A plate is not rebuilt for a change to its screen's CODE that does not change its screen's PICTURES.

The screen code is the whole Remotion library, so any runtime edit staled every device plate — WorkBuddy's plan-3d is
83 min of Blender, staled by a line that cannot touch its screen (2026-11-12). blender_plate re-renders the screen (a
minute) and re-keys the plate when the pictures match within the screen render's own noise; otherwise it rebuilds."""
import json
import os
import sys

import pytest

np = pytest.importorskip("numpy")
Image = pytest.importorskip("PIL.Image")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import blender_plate as bp            # noqa: E402

SPEC = {"id": "p", "screen": {"shot": "S", "props": {}, "px": [64, 40]}}


def _pics(d, n=3, dots=0, seed=0):
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    base = (np.indices((40, 64)).sum(0) % 255).astype(np.uint8)
    for k in range(n):
        a = np.stack([base, base, base, np.full_like(base, 255)], -1)
        if dots:
            ys, xs = rng.integers(0, 40, dots), rng.integers(0, 64, dots)
            a[ys, xs, 0] ^= 0x40
        Image.fromarray(a, "RGBA").save(os.path.join(d, "element-%03d.png" % k))
    return d


def test_screen_difference_counts_pixels_not_bytes(tmp_path):
    a = _pics(str(tmp_path / "a"))
    assert bp.screen_difference(a, _pics(str(tmp_path / "b"))) == (0, 0)
    n, worst = bp.screen_difference(a, _pics(str(tmp_path / "c"), dots=10))
    assert n == 3 and 1 <= worst <= 10
    assert bp.screen_difference(a, _pics(str(tmp_path / "d"), n=2)) is None, "frames that do not pair up are not a match"


@pytest.fixture
def plate(tmp_path, monkeypatch):
    """A built plate whose key was taken under screen code 'old'; the code is 'new' now."""
    out = str(tmp_path)
    pd = os.path.join(out, "media", "blender", "p")
    _pics(os.path.join(pd, "screen"))
    fake_key = lambda spec, out_dir, frames, fps, w, h, cue_t, bv, folder_wide=False, screen_sig=None: \
        "K-" + (screen_sig if screen_sig is not None else "new")
    monkeypatch.setattr(bp, "plate_key", fake_key)
    monkeypatch.setattr(bp, "screen_code", lambda out_dir, screen: "new")
    monkeypatch.setattr(bp, "plate_dir", lambda out_dir, pid: pd)
    with open(os.path.join(pd, "plate.json"), "w") as fh:
        json.dump({"key": "K-old", "screen_code": "old", "frames": 3}, fh)
    return out, pd


ARGS = (SPEC, 3, 30, 1920, 1080, {}, "5.2.4")


def _rekey(out, monkeypatch, dots):
    monkeypatch.setattr(bp, "render_screen", lambda out_dir, spec, frames, dest: _pics(dest, dots=dots, seed=1))
    return bp.screen_rekey(out, *ARGS)


def test_pictures_within_the_render_noise_re_key_the_plate(plate, monkeypatch):
    out, pd = plate
    ok, note = _rekey(out, monkeypatch, dots=5)
    assert ok and "render noise" in note
    built = json.load(open(os.path.join(pd, "plate.json")))
    assert built["key"] == "K-new" and built["screen_code"] == "new" and built["rekeyed"] == 1
    assert not os.path.exists(os.path.join(pd, "screen_check"))


def test_pictures_that_changed_rebuild(plate, monkeypatch):
    out, pd = plate
    monkeypatch.setattr(bp, "SCREEN_NOISE_PX", 3)
    ok, note = _rekey(out, monkeypatch, dots=200)
    assert not ok and "changed" in note
    assert json.load(open(os.path.join(pd, "plate.json")))["key"] == "K-old", "a refused re-key must leave the plate stale"


def test_any_other_input_changing_is_never_re_keyed(plate, monkeypatch):
    out, pd = plate
    with open(os.path.join(pd, "plate.json"), "w") as fh:
        json.dump({"key": "K-something-else", "screen_code": "old", "frames": 3}, fh)
    called = []
    monkeypatch.setattr(bp, "render_screen", lambda *a: called.append(a))
    assert bp.screen_rekey(out, *ARGS) == (False, "")
    assert not called, "no screen render is spent on a plate that must be rebuilt anyway"


def test_a_plate_built_before_the_screen_code_was_recorded_is_rebuilt(plate, monkeypatch):
    out, pd = plate
    with open(os.path.join(pd, "plate.json"), "w") as fh:
        json.dump({"key": "K-old", "frames": 3}, fh)
    assert bp.screen_rekey(out, *ARGS) == (False, "")


def test_still_zero_is_refused_rather_than_building_the_whole_plate():
    """`--still 0` read as "no still" (every check was `if still`) and built the whole plate — 41 min of Cycles."""
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(bp.__file__), "blender_plate.py"), "/nonexistent",
                        "--still", "0"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "counts frames from 1" in r.stderr
    src = open(bp.__file__, encoding="utf-8").read()
    body = src.split("def build(")[1].split("\ndef ")[0]
    assert " if still else" not in body and "if still:" not in body and "if not still" not in body


def test_verify_re_keys_only_a_plate_whose_pictures_are_unchanged(tmp_path, monkeypatch):
    """`--verify` (ANC, 2026-11-12): three plates staled by a kit edit their scenes never import. Three stills under
    today's code against the delivered frames: within encode noise it re-keys; a changed picture is left stale."""
    out = str(tmp_path)
    pd = tmp_path / "plate"
    pd.mkdir()
    (pd / "plate.json").write_text(json.dumps({"key": "OLD", "frames": 100, "cues": {}}))
    board = {"slides": [{"blender": {"id": "p"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board))
    spec = {"id": "p", "screen": None}
    monkeypatch.setattr(bp, "_plates_on", lambda b, o: [(0, b["slides"][0], spec)])
    monkeypatch.setattr(bp, "plate_state", lambda o, b, i: "stale")
    monkeypatch.setattr(bp, "plate_dir", lambda o, pid: str(pd))
    monkeypatch.setattr(bp, "_key_args", lambda o, b, i: dict(spec=spec, out_dir=o, frames=100, fps=30, w=8, h=8,
                                                              cue_t={}, blender_version="5"))
    monkeypatch.setattr(bp, "plate_key", lambda **k: "NEW")

    def pic(path, v):
        Image.fromarray(np.full((8, 8, 4), v, np.uint8), "RGBA").save(path)
        return True

    monkeypatch.setattr(bp, "_plate_frame", lambda pd_, n, dest: pic(dest, 200))
    for still_v, want in ((200, True), (120, False)):
        monkeypatch.setattr(bp, "build", lambda o, only, still, v=still_v: [{"path": pic(str(tmp_path / ("s%d.png" % still)), v)
                                                                             and str(tmp_path / ("s%d.png" % still))}])
        (pd / "plate.json").write_text(json.dumps({"key": "OLD", "frames": 100, "cues": {}}))
        ok, diffs, note = bp.verify_rekey(out, "p")
        assert ok is want, note
        assert json.loads((pd / "plate.json").read_text())["key"] == ("NEW" if want else "OLD")
    (pd / "plate.json").write_text(json.dumps({"key": "OLD", "frames": 90, "cues": {}}))
    assert bp.verify_rekey(out, "p")[0] is False, "a changed frame count is different motion: never verified"
