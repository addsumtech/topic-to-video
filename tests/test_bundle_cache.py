"""scripts/bundle_cache.py: one Remotion bundle per film state, rebuilt exactly when something it is built from moves."""
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import bundle_cache as bc  # noqa: E402


@pytest.fixture
def project(tmp_path, monkeypatch):
    rem = tmp_path / "skill" / "remotion"
    (rem / "src").mkdir(parents=True)
    (rem / "src" / "index.ts").write_text("export {};\n")
    (rem / "node_modules").mkdir()
    (rem / "node_modules" / ".package-lock.json").write_text("{}")
    (tmp_path / "skill" / "assets" / "fonts").mkdir(parents=True)
    (tmp_path / "skill" / "assets" / "fonts" / "a.ttf").write_bytes(b"font")
    monkeypatch.setattr(bc, "REMOTION", str(rem))
    monkeypatch.setattr(bc, "SKILL_ROOT", str(tmp_path / "skill"))
    monkeypatch.setenv("TTV_BUNDLE_CACHE", str(tmp_path / "cache"))
    calls = []

    def run(cmd, **kw):
        out = next(a for a in cmd if a.startswith("--out-dir=")).split("=", 1)[1]
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, "index.html"), "w").write("<html>%d" % len(calls))
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    return types.SimpleNamespace(rem=rem, tmp=tmp_path, run=run, calls=calls)


def test_same_inputs_bundle_once(project):
    a = bc.bundle(run=project.run)
    b = bc.bundle(run=project.run)
    assert a == b and len(project.calls) == 1 and os.path.isfile(os.path.join(a, "index.html"))


@pytest.mark.parametrize("change", ["src", "workshop", "public", "env", "lock", "asset"])
def test_any_input_rebuilds(project, change, monkeypatch):
    ws = project.tmp / "film" / "workshop"
    ws.mkdir(parents=True)
    (ws / "index.ts").write_text("export const SHOTS = {};\n")
    pub = project.tmp / "pub"
    pub.mkdir()
    (pub / "plate.webm").write_bytes(b"x" * 10)
    env = dict(os.environ, SLIDES_WORKSHOP=str(ws))
    first = bc.bundle(str(pub), env, run=project.run)
    if change == "src":
        (project.rem / "src" / "Film.tsx").write_text("// new\n")
    elif change == "workshop":
        (ws / "plates.ts").write_text("export const PLATES = {};\n")
    elif change == "public":
        (pub / "plate.webm").write_bytes(b"y" * 11)          # a rebuilt plate
    elif change == "env":
        env["REMOTION_CONCURRENCY"] = "1"
    elif change == "lock":
        (project.rem / "node_modules" / ".package-lock.json").write_text('{"v": 2}')
    elif change == "asset":
        (project.tmp / "skill" / "assets" / "fonts" / "a.ttf").write_bytes(b"other font")
    second = bc.bundle(str(pub), env, run=project.run)
    assert second != first and len(project.calls) == 2


def test_a_failed_bundle_raises_and_leaves_nothing(project):
    def bad(cmd, **kw):
        return types.SimpleNamespace(returncode=1, stdout="", stderr="webpack: boom")
    with pytest.raises(RuntimeError, match="boom"):
        bc.bundle(run=bad)
    assert not [d for d in os.listdir(project.tmp / "cache") if not d.startswith(".")]
    assert not [d for d in os.listdir(project.tmp / "cache") if d.startswith(".building-")]


def test_off_builds_afresh_every_time(project, monkeypatch):
    monkeypatch.setenv("TTV_BUNDLE_CACHE", "off")
    a, b = bc.bundle(run=project.run), bc.bundle(run=project.run)
    assert a != b and len(project.calls) == 2


def test_old_bundles_are_evicted(project, monkeypatch):
    monkeypatch.setattr(bc, "KEEP", 2)
    for i in range(4):
        (project.rem / "src" / "v.ts").write_text("export const v = %d;\n" % i)
        bc.bundle(run=project.run)
    assert len([d for d in os.listdir(project.tmp / "cache") if not d.startswith(".")]) == 2


def test_the_same_media_in_another_temp_folder_is_the_same_bundle(project):
    # every gate stages its public folder in its own temp dir: only what is IN it may key the bundle
    one, two = project.tmp / "work1" / "public", project.tmp / "work2" / "public"
    for d in (one, two):
        d.mkdir(parents=True)
    (one / "plate.webm").write_bytes(b"x" * 10)
    os.link(one / "plate.webm", two / "plate.webm")             # minimal_public links the film's own file
    assert bc.bundle(str(one), run=project.run) == bc.bundle(str(two), run=project.run)
    assert len(project.calls) == 1
