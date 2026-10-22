"""The machine-wide render lock: two processes rendering at once take turns; one process may re-enter it."""
import os
import subprocess
import sys
import time

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import _common as c  # noqa: E402

HOLD = ("import sys, time; sys.path.insert(0, %r); import _common as c\n"
        "with c.render_lock():\n    print('in', time.time(), flush=True); time.sleep(0.6); print('out', time.time(), flush=True)\n")


def test_two_renders_take_turns(tmp_path, monkeypatch):
    lock = str(tmp_path / ".render.lock")
    env = dict(os.environ, PYTHONPATH=SCRIPTS)
    code = HOLD % os.path.abspath(SCRIPTS)
    code = code.replace("import _common as c\n", "import _common as c; c.RENDER_LOCK = %r\n" % lock)
    procs = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, env=env) for _ in range(2)]
    spans = []
    for p in procs:
        out, _ = p.communicate(timeout=20)
        t = dict(l.split() for l in out.strip().splitlines())
        spans.append((float(t["in"]), float(t["out"])))
    spans.sort()
    assert spans[1][0] >= spans[0][1] - 0.01, "the second render started before the first one ended: %r" % spans


def test_one_process_may_re_enter(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "RENDER_LOCK", str(tmp_path / ".render.lock"))
    with c.render_lock():
        with c.render_lock():
            pass
    assert c._LOCK_DEPTH == [0, None]


def test_the_lock_can_be_turned_off(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "RENDER_LOCK", str(tmp_path / "nope" / ".render.lock"))   # unopenable: proves it is skipped
    monkeypatch.setenv("TOPIC_VIDEO_RENDER_LOCK", "0")
    with c.render_lock():
        pass
