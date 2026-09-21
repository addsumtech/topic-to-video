"""A measured row has to know when it stops describing its own picture.

`register_energy` already refused to let a rewritten register keep an old number. It hashed the register's
`.tsx` and nothing else, which was exactly right while every register drew itself — and stopped being right
the moment two of them shared a visual primitive. `uiSurface` decides what `SurfaceCarousel` and `PointerTour`
look like; editing it changes both pictures and neither hash, so both rows would go on reading as measured
while describing frames that no longer exist. That is the same failure the function was written to end, one
level up.
"""
import hashlib
import os
import shutil
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import register_energy as re_          # noqa: E402

_SHOTS = os.path.join(_ROOT, "remotion", "src", "shots")
_RUNTIME = os.path.join(_ROOT, "remotion", "src", "runtime")


def test_a_shots_hash_covers_the_runtime_it_draws_with():
    before = re_.source_hashes()
    victim = os.path.join(_RUNTIME, "uiSurface.tsx")
    backup = victim + ".bak"
    shutil.copy2(victim, backup)
    try:
        with open(victim, "a", encoding="utf-8") as fh:
            fh.write("\n// touched by a test\n")
        after = re_.source_hashes()
    finally:
        shutil.move(backup, victim)
    moved = {n for n in before if before[n] != after.get(n)}
    assert "SurfaceCarousel" in moved and "PointerTour" in moved, (
        "editing a shared primitive must invalidate the rows of every register drawn with it; moved: %s"
        % sorted(moved))
    assert "CinematicTitle" not in moved, (
        "and only those: invalidating the whole manifest on any runtime edit makes a 157-render re-sweep the "
        "price of touching anything, which is how a check stops being run")
    assert re_.source_hashes() == before, "the test must leave the manifest's own hashes where it found them"


def test_every_register_resolves_the_runtime_it_imports():
    """The hash is only as good as the import scan. A register whose imports fail to resolve silently goes
    back to being hashed on its own source alone — the exact hole this closes, reopened per file and
    invisible, because nothing about the number would look wrong."""
    import glob
    thin = []
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        if len(re_._deps(f)) < 2:
            thin.append(os.path.basename(f)[:-4])
    assert not thin, (
        "these registers resolved no project imports at all, so their rows are hashed on their own source "
        "only: %s" % ", ".join(thin))


def test_the_recorded_hash_is_the_one_the_render_read(tmp_path, monkeypatch):
    """A full sweep is two and a half hours of rendering, and this repo edits source during it. So the
    question is not whether the hash is right at the end — it is which source the hash DESCRIBES.

    Recorded from a fresh read at write time (which is what this file did), a register measured in the first
    ten minutes and edited in the second hour gets the FINAL hash against the ORIGINAL pixels: the row looks
    current, `stale()` reports nothing, and `density_advice.py` goes on advising from numbers that describe
    code nobody has now. It cost a re-measure of six registers to notice, and the only reason it was noticed
    is that the edits were mine and I remembered making them.

    Hashing per register immediately before its render makes the record describe the bytes that were read.
    A later edit then shows up as stale — the safe direction, because stale only costs a re-measure.
    """
    man = tmp_path / "m.json"
    # A FRESH render cache, or this test does not run the thing it is about: the sweep keys its mp4s by
    # (source hash, dna, props) under $TMPDIR, so a second run of this test finds the first run's file, skips
    # `render_one` entirely, and the probe never observes a render at all. It failed exactly that way.
    monkeypatch.setenv("TMPDIR", str(tmp_path / "cache"))
    monkeypatch.setattr(re_, "MANIFEST", str(man))
    monkeypatch.setattr(re_, "durations", lambda: {"A": 100, "B": 100})
    monkeypatch.setattr(re_, "universe", lambda: ["A", "B"])
    monkeypatch.setattr(re_, "ensure_fixture", lambda: None)
    monkeypatch.setattr(re_, "evidence_props", lambda: {})
    monkeypatch.setattr(re_, "stills_from", lambda *a, **k: None)
    monkeypatch.setattr(re_, "footprint", lambda *a, **k: 0.4)
    monkeypatch.setattr(re_.fe, "measure", lambda *a, **k: {
        "motion_p75": 0.001, "ink_median": 0.2, "luma_range": 0.1, "seconds": 5.0})

    # A's source is edited AFTER A has been rendered and before B is — exactly the mid-sweep edit.
    live = {"A": "a-before", "B": "b-only"}
    rendered = {}

    def fake_hash(name):
        return live[name]

    def fake_render(name, mp4, dna, props):
        rendered[name] = live[name]
        if name == "A":
            live["A"] = "a-after"          # someone edits A while the sweep moves on
        open(mp4, "w").write("x")
        return True, [""]

    monkeypatch.setattr(re_, "source_hash", fake_hash)
    monkeypatch.setattr(re_, "source_hashes", lambda: dict(live))
    monkeypatch.setattr(re_, "render_one", fake_render)
    re_.main(["--dna=product"])

    import json
    data = json.loads(man.read_text(encoding="utf-8"))
    assert data["_source"]["A"] == rendered["A"] == "a-before", (
        "the row records a hash for source the render never read: %r" % data["_source"])
    # and the consequence that makes it matter: the edit is now VISIBLE
    assert [n for n, _ in re_.stale(data)] == ["A"], (
        "a register edited after it was measured does not report as stale: %r" % re_.stale(data))
