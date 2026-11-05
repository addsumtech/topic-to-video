"""A render a test starts cannot hang the suite: the 2026-11-05 run sat 24 min on test_kinetic's `remotion still`
at 0% CPU. conftest routes every real Remotion render a test runs through _common.watched_run."""
import os
import subprocess
import sys
import time


def test_a_hung_remotion_call_in_a_test_is_killed(monkeypatch):
    monkeypatch.setenv("TOPIC_VIDEO_RENDER_IDLE_S", "1.5")
    t0 = time.time()
    # stands in for `npx remotion still …`: the conftest wrapper keys on the argv naming remotion and still/render
    r = subprocess.run([sys.executable, "-c", "import time; time.sleep(60)", "remotion", "still"],
                       capture_output=True, text=True)
    assert r.returncode == 124 and time.time() - t0 < 20
    assert "RenderHangError" in r.stderr


def test_other_commands_pass_straight_through():
    r = subprocess.run([sys.executable, "-c", "print('hi')"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "hi"
