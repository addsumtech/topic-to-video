import os, subprocess, sys, pytest
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)

@pytest.fixture(scope="session", autouse=True)
def _build_fixtures():
    if not os.path.exists(os.path.join(HERE, "fixtures", "deck.pptx")):
        subprocess.run([sys.executable, os.path.join(HERE, "fixtures", "make_fixtures.py")], check=True)

@pytest.fixture
def fixtures_dir():
    return os.path.join(HERE, "fixtures")


# A RENDER A TEST STARTS CANNOT HANG THE SUITE. The 2026-11-05 full run sat 24 min on one `remotion still` at 0% CPU,
# and an orphaned one burned 66% CPU for 50 min. Every real Remotion render a test runs (argv naming remotion and
# still/render) goes through _common.watched_run — idle, fatal-line and wall-clock watch, the tree killed on a hang —
# unless the test patches subprocess.run itself, which replaces this wrapper for that test.
_REAL_SUBPROCESS_RUN = subprocess.run


def _watched_test_run(cmd, *args, **kw):
    argv = [str(a) for a in cmd] if isinstance(cmd, (list, tuple)) else []
    if args or not any("remotion" in a for a in argv) or not ({"still", "render"} & set(argv)):
        return _REAL_SUBPROCESS_RUN(cmd, *args, **kw)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
    import _common
    return _common.watched_run(cmd, fatal=_common.RENDER_FATAL, cap_s=900, **kw)   # a `timeout` keeps its meaning


@pytest.fixture(autouse=True)
def _watch_test_renders(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _watched_test_run)
