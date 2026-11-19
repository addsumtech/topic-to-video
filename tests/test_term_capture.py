"""term_capture + Stage3D.terminal: a terminal program's real screen, cell by cell (colours, wide CJK characters, block
characters), with account text replaced and the runner's home path refused; drawn back as markup the film can show."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "term_capture.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402

pyte = pytest.importorskip("pyte")
PROG = "import sys,time; sys.stdout.write('\\x1b[31mred\\x1b[0m \\u4e2d\\u6587 \\x1b[38;2;215;119;87m\\u259b\\u2588\\x1b[0m %s\\n'); sys.stdout.flush(); time.sleep(5)"


def _cap(tmp_path, *opts, say="Claude Pro"):
    out = tmp_path / "cap.json"
    r = subprocess.run([sys.executable, SCRIPT, "--out", str(out), "--cols", "40", "--rows", "4", "--wait", "1.5", *opts,
                        "--", sys.executable, "-c", PROG % say], capture_output=True, text=True, timeout=60)
    return r, (json.loads(out.read_text()) if out.exists() else None)


def test_the_screen_is_kept_cell_by_cell(tmp_path):
    r, cap = _cap(tmp_path)
    assert r.returncode == 0, r.stderr
    runs = cap["frames"][-1]["rows"][0]
    assert ["red", {"fg": "red", "bg": "default"}] in runs, runs
    wide = [x for x in runs if x[1].get("w") == 2]
    assert [x[0] for x in wide] == ["中", "文"], "each CJK character is one run across two cells: %s" % runs
    assert any(x[0].startswith("▛") and x[1]["fg"] == "d77757" for x in runs), "truecolor kept as hex: %s" % runs


def test_account_text_is_replaced_in_place_and_must_fit(tmp_path):
    r, cap = _cap(tmp_path, "--replace", "Claude Pro=>Plan")
    assert r.returncode == 0, r.stderr
    line = "".join(x[0] for x in cap["frames"][-1]["rows"][0])
    assert "Plan" in line and "Claude Pro" not in line and line.index("Plan") == line.index("█") + 2, line
    r, _ = _cap(tmp_path, "--replace", "Claude Pro=>a much longer plan name")
    assert r.returncode == 2 and "longer" in r.stderr


def test_the_runners_home_path_is_refused(tmp_path):
    home = os.path.expanduser("~")
    r, _ = _cap(tmp_path, say=home)
    assert r.returncode == 2 and home in r.stderr and "--replace" in r.stderr, r.stderr
    r, cap = _cap(tmp_path, "--replace", "%s=>~" % home, say=home)
    assert r.returncode == 0, r.stderr


def test_typing_keeps_one_frame_per_character(tmp_path):
    out = tmp_path / "cap.json"
    r = subprocess.run([sys.executable, SCRIPT, "--out", str(out), "--cols", "30", "--rows", "2", "--wait", "0.6",
                        "--type", "abc", "--type-at", "0.5", "--type-every", "0.15", "--", "cat"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    lines = ["".join(x[0] for x in f["rows"][0]).strip() for f in json.loads(out.read_text())["frames"]]
    assert lines[:3] == ["a", "ab", "abc"], lines


try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_a_frame_is_drawn_with_block_characters_filled_by_quadrant(tmp_path):
    import _filmpage as fp
    from PIL import Image
    r, cap = _cap(tmp_path)
    assert r.returncode == 0, r.stderr
    shutil.copy(os.path.join(ROOT, "assets", "html", "stage3d.js"), tmp_path)
    (tmp_path / "p.html").write_text("""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0"><canvas id="c"></canvas>
<script src="stage3d.js"></script><script>
window.filmReady = (async () => { const cap = %s; const t = Stage3D.terminal(cap.frames[cap.frames.length - 1], {px: 20, title: null, pad: 0});
  const c = document.getElementById('c'); c.width = t.size[0]; c.height = t.size[1];
  await Stage3D.screen(c, t.html, {size: t.size, css: t.css, name: 't'}); window.__size = t.size; return 'ok'; })();
window.seek = () => {};</script></body></html>""" % json.dumps(cap))
    port, srv = fp.serve(str(tmp_path))
    try:
        p = fp.FilmPage(port, "p.html", 900, 200)
        try:
            size = p.ev("window.__size")
            p.shot(str(tmp_path / "s.png"), "png")
        finally:
            p.close()
    finally:
        srv.shutdown()
    cw, rh = 20 * 0.6021, 25
    assert abs(size[0] - round(40 * cw)) <= 1 and size[1] == 4 * rh, size
    im = Image.open(tmp_path / "s.png").convert("RGB")
    x0 = 11 * cw                       # "red " (4) + two CJK (4) + " " (1) = column 9; the quadrant char at column 9..
    col = lambda x, y: im.getpixel((int(x), int(y)))
    ul, lr = col(9 * cw + cw * 0.25, rh * 0.25), col(9 * cw + cw * 0.75, rh * 0.75)
    assert ul[0] > 180 and ul[2] < 120, "the upper-left quadrant of the block character is filled orange: %s" % (ul,)
    assert lr[0] < 60, "its lower-right quadrant is empty (U+259B leaves it out): %s" % (lr,)
    full = col(x0 - cw * 0.5, rh * 0.5)
    assert full[0] > 180, "the full block next to it fills its cell: %s" % (full,)
