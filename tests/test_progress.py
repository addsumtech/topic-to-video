"""A long step says where it is (_progress.json + a self-reloading _progress.html): the ANC render sat 1 h 35 min on
one beat with an empty, block-buffered log and nobody could tell."""
import json
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import progress as pg  # noqa: E402


def test_progress_records_the_item_and_an_eta_from_measured_items(tmp_path, monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(pg.time, "time", lambda: t[0])
    pg.write(str(tmp_path), "render", 0, 4, "beat 1")
    t[0] = 1030.0
    pg.write(str(tmp_path), "render", 1, 4, "beat 2")
    rec = json.load(open(tmp_path / pg.FILE))
    assert rec["eta_s"] == 90.0 and rec["item"] == "beat 2"          # 30 s an item, 3 left
    page = open(tmp_path / pg.PAGE).read()
    assert "http-equiv=refresh" in page and "render 1/4" in page
    assert "about 1:30 left" in pg.line(rec, now=1030.0)


def test_progress_never_fails_its_caller(tmp_path):
    pg.write(str(tmp_path / "missing" / "dir"), "render", 1, 2)          # no folder: silently nothing


def test_the_per_beat_render_reports_each_beat(tmp_path, monkeypatch):
    import remotion_segments as rs
    monkeypatch.setattr(rs, "render_segment", lambda *a, **k: None)
    segs = [{"k": i, "a": i * 10, "b": i * 10 + 9, "key": str(i)} for i in range(3)]
    seen = []
    real = pg.write
    monkeypatch.setattr(pg, "write", lambda *a, **k: (seen.append(a[1:4]), real(*a, **k)))
    rs._render_stale(segs, segs, "/p.json", str(tmp_path), str(tmp_path), [], None, None, lambda k: k + 1, lambda *_: None)
    assert seen[0] == ("render", 0, 3) and seen[-1] == ("render", 3, 3), seen
    assert json.load(open(tmp_path / pg.FILE))["done"] == 3


def test_the_cli_prints_one_line(tmp_path):
    pg.write(str(tmp_path), "gates", 2, 5, "jitter_qa.py")
    r = subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "progress.py"), str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "gates 2/5" in r.stdout and "jitter_qa.py" in r.stdout
