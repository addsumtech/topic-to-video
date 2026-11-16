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


_REMOTION_DIR = os.path.realpath(os.path.join(os.path.dirname(HERE), "remotion"))


def _bundled(argv, kw):
    """`argv` with `src/index.ts` replaced by the CACHED bundle of the code as it is now (scripts/bundle_cache, keyed by
    the code, so a test that mutates the runtime gets a fresh one): 44 test files each bundled the project afresh,
    ~25 s a render (audit 2026-11-15, step 7). Anything unusual keeps its own entry point — another cwd, a public dir
    of its own, `TTV_TEST_BUNDLE=off`, or a bundle that cannot be built (the render then says why itself)."""
    if os.environ.get("TTV_TEST_BUNDLE", "") == "off" or "src/index.ts" not in argv:
        return argv
    if os.path.realpath(str(kw.get("cwd") or os.getcwd())) != _REMOTION_DIR:
        return argv
    if any(a.startswith(("--public-dir", "--bundle")) for a in argv):
        return argv
    try:
        import bundle_cache
        b = bundle_cache.bundle(env=kw.get("env"), run=_REAL_SUBPROCESS_RUN)
    except Exception:  # noqa: BLE001 — the test's own render reports a broken project
        return argv
    return [b if a == "src/index.ts" else a for a in argv]


def _watched_test_run(cmd, *args, **kw):
    argv = [str(a) for a in cmd] if isinstance(cmd, (list, tuple)) else []
    if args or not any("remotion" in a for a in argv) or not ({"still", "render"} & set(argv)):
        return _REAL_SUBPROCESS_RUN(cmd, *args, **kw)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
    import _common
    cmd = _bundled(argv, kw)
    return _common.watched_run(cmd, fatal=_common.RENDER_FATAL, cap_s=900, **kw)   # a `timeout` keeps its meaning


@pytest.fixture(autouse=True)
def _watch_test_renders(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _watched_test_run)


@pytest.fixture(autouse=True)
def _private_taste_ledger(tmp_path_factory, monkeypatch):
    """No test reads the user's real taste ledger (~/.topic-to-video): a delivery gate that consults it would pass or
    fail by what this machine's user once taught. A test that needs entries sets TTV_TASTE_LEDGER itself."""
    if "TTV_TASTE_LEDGER" not in os.environ:
        monkeypatch.setenv("TTV_TASTE_LEDGER", str(tmp_path_factory.mktemp("taste") / "ledger.json"))
