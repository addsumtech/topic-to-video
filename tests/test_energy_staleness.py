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
