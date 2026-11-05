"""A render whose process tree stops working is killed and retried — and a render that is working is never killed.

The watch reads the CPU of the whole process TREE as per-process deltas (`_common.watched_run`). Each test below is
the shape of a real failure: a hung still at 0% CPU (killed, retried once, reported), a busy run of short children
that a high-water-mark watch killed (left alone), and a detached child in a session of its own, which is where
Remotion puts Chrome (followed for its CPU, and killed with the tree instead of orphaned)."""
import os
import subprocess
import sys
import time

import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import _common as c  # noqa: E402

BURN = "import time\nt=time.time()\nwhile time.time()-t<%s: pass\n"


@pytest.fixture(autouse=True)
def _fast(monkeypatch, tmp_path):
    monkeypatch.setattr(c, "_POLL_S", 0.3)
    monkeypatch.delenv("TOPIC_VIDEO_RENDER_IDLE_S", raising=False)
    monkeypatch.setenv("TMPDIR", str(tmp_path))          # the diagnostics folder lands in the test's own tmp
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")         # no `sample` calls in a unit test


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    st = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(st) and not st.startswith("Z")


def test_a_hung_render_is_killed_retried_once_and_reported(capsys):
    t0 = time.time()
    r = c.watched_run([sys.executable, "-c", "import time; print('started', flush=True); time.sleep(60)"],
                      idle_s=1.5, capture_output=True, text=True)
    took = time.time() - t0
    assert r.returncode == 124
    assert "RenderHangError" in r.stderr and "attempt 2 of 2" in r.stderr
    assert r.stdout.count("started") == 1                 # each attempt's own output, not lost to the kill
    assert took < 20, "two 1.5 s idle windows took %.1f s" % took
    err = capsys.readouterr().err
    assert "retrying once" in err and "not retried again" in err
    # the failure reason a caller extracts names the hang, not a stack line
    assert c.render_error(r.stdout, r.stderr).startswith("RenderHangError")


def test_check_true_raises_on_a_hang():
    with pytest.raises(subprocess.CalledProcessError) as e:
        c.watched_run([sys.executable, "-c", "import time; time.sleep(60)"], idle_s=1.0, retries=0, check=True)
    assert e.value.returncode == 124


def test_a_busy_run_of_short_children_is_not_killed():
    # One 3 s child, then 0.5 s children back to back: 100% CPU throughout. A total over the LIVING processes drops
    # each time a child exits, so a high-water mark on it called this "no progress" and killed it.
    script = "%s -c '%s'; for i in 1 2 3 4 5 6 7 8 9 10 11 12; do %s -c '%s'; done; echo FINISHED" % (
        sys.executable, BURN % 3, sys.executable, BURN % 0.5)
    r = c.watched_run(["sh", "-c", script], idle_s=2.0, capture_output=True, text=True)
    assert r.returncode == 0 and "FINISHED" in r.stdout, r.stderr
    assert "RenderHangError" not in (r.stderr or "")


DETACHED = """
import os, subprocess, sys
child = subprocess.Popen([sys.executable, "-c", %r], start_new_session=True)
open(%r, "w").write(str(child.pid))
child.wait()
print("FINISHED", flush=True)
"""


def test_a_detached_child_is_watched_and_killed_with_the_tree(tmp_path):
    # Busy detached child (Remotion's Chrome is detached): its CPU is the render's progress — not killed.
    pidf = str(tmp_path / "busy.pid")
    r = c.watched_run([sys.executable, "-c", DETACHED % (BURN % 4, pidf)], idle_s=1.5, capture_output=True, text=True)
    assert r.returncode == 0 and "FINISHED" in r.stdout, r.stderr
    # Idle detached child: the tree is hung, and the kill reaches the child in its own session (no orphan).
    pidf = str(tmp_path / "idle.pid")
    r = c.watched_run([sys.executable, "-c", DETACHED % ("import time; time.sleep(60)", pidf)],
                      idle_s=1.5, retries=0, capture_output=True, text=True)
    assert r.returncode == 124
    child = int(open(pidf).read())
    deadline = time.time() + 5
    while _alive(child) and time.time() < deadline:
        time.sleep(0.1)
    assert not _alive(child), "the detached child %d outlived the kill — an orphan" % child


def test_the_hang_leaves_a_diagnostics_folder(tmp_path):
    r = c.watched_run([sys.executable, "-c", "import time; time.sleep(60)"], idle_s=1.0, retries=0,
                      capture_output=True, text=True)
    where = r.stderr.split("diagnostics in ", 1)[1].split()[0].rstrip(";")
    tree = open(os.path.join(where, "tree.txt"), encoding="utf-8").read()
    assert "time.sleep(60)" in tree and "cpu(s)" in tree


def test_a_normal_render_passes_through():
    r = c.watched_run([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"],
                      capture_output=True, text=True)
    assert (r.returncode, r.stdout.strip(), r.stderr.strip()) == (3, "out", "err")


def test_timeout_keeps_subprocess_meaning():
    with pytest.raises(subprocess.TimeoutExpired):
        c.watched_run([sys.executable, "-c", BURN % 30], idle_s=60, timeout=1.0, capture_output=True)


def test_run_render_watches_only_the_real_run(monkeypatch, tmp_path):
    monkeypatch.setattr(c, "RENDER_LOCK", str(tmp_path / ".render.lock"))
    seen = []
    fake = lambda *a, **k: seen.append(a) or subprocess.CompletedProcess(a[0], 0, "", "")
    assert c.run_render(fake, ["npx", "remotion", "still"], capture_output=True).returncode == 0
    assert seen == [(["npx", "remotion", "still"],)]       # a test's replaced run is called as given
    r = c.run_render(subprocess.run, [sys.executable, "-c", "print(7)"], capture_output=True, text=True)
    assert r.stdout.strip() == "7"


@pytest.mark.parametrize("txt,sec", [("0:05.64", 5.64), ("1:02:03.50", 3723.5), ("2-01:00:00", 176400.0),
                                     ("00:00:05", 5.0)])
def test_ps_time_formats(txt, sec):
    assert abs(c._cpu_seconds(txt) - sec) < 1e-6


# ── a render that BREAKS but keeps burning CPU (the anc film, 2026-11-05) ────────────────────────────────────────
# The Mac's network changed mid-render: Chrome lost Remotion's local server (net::ERR_NETWORK_CHANGED, then "A
# network error occurred" and "Session closed"), kept spinning on "Could not extract frame from compositor", and the
# idle watch — CPU only — never fired. The render sat 1 h 35 min on one beat.

BREAKS_ONCE = ("import os, sys, time\n"
               "m = sys.argv[1]\n"
               "if not os.path.exists(m):\n"
               "    open(m, 'w').close()\n"
               "    sys.stderr.write('[http://localhost:3000/x.ttf] Failed to load resource: net::ERR_NETWORK_CHANGED\\n')\n"
               "    sys.stderr.flush()\n"
               "    t = time.time()\n"
               "    while time.time() - t < 60: pass\n"
               "print('ok', flush=True)\n")


def test_a_render_that_logs_a_fatal_error_while_busy_is_killed_and_retried(tmp_path, capsys):
    t0 = time.time()
    r = c.watched_run([sys.executable, "-c", BREAKS_ONCE, str(tmp_path / "m")], idle_s=30, fatal=c.RENDER_FATAL)
    took = time.time() - t0
    assert r.returncode == 0                               # the retry, on a clean run, renders
    assert took < 20, "a fatal line took %.1f s to act on" % took
    err = capsys.readouterr().err
    assert "ERR_NETWORK_CHANGED" in err                    # the child's own stderr still reaches the log
    assert "RenderBrokeError" in err and "retrying once" in err


def test_a_busy_render_past_its_cap_is_killed_and_reported():
    t0 = time.time()
    r = c.watched_run([sys.executable, "-c", BURN % 60], idle_s=30, cap_s=2, retries=0, capture_output=True, text=True)
    assert r.returncode == 124 and time.time() - t0 < 15
    assert "RenderHangError" in r.stderr and "longer than its cap" in r.stderr


def test_a_render_segment_is_watched_for_fatal_lines_and_capped(monkeypatch):
    import remotion_segments as rs
    seen = {}

    def fake(cmd, **kw):
        seen.update(kw)
        raise RuntimeError("stop")
    monkeypatch.setattr(c, "watched_run", fake)
    with pytest.raises(RuntimeError):
        rs.render_segment({"key": "k", "a": 0, "b": 99, "k": 0}, False, "/p.json", "/pub", "/tmp", [],
                          run=c._REAL_RUN, serve="/b")
    assert seen.get("fatal") is c.RENDER_FATAL and seen.get("cap_s", 0) >= 300
