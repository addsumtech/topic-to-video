"""Every film-scoped render goes through the film's workshop (scripts/workshop.py), and nothing else does.

The unit half proves each caller hands the workshop's environment to the CLI — and hands NOTHING when a film has
no workshop, so that film runs exactly the call it always did. The rendered half runs a real two-beat film with a
workshop through the per-beat renderer, and makes an object that throws say its own message in every gate."""
import json
import os
import shutil
import subprocess
import sys

import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workshop as ws  # noqa: E402
import remotion_segments as rs  # noqa: E402
from test_workshop_bundle import SHOT, OBJECT  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

BOOM = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps & {bars?: unknown}> = ({bars}) => {
  if (typeof bars !== 'number') throw new Error('WsBoom: pressure must be a number of bars, got ' + JSON.stringify(bars));
  return <div />;
};
"""


def _film(tmp_path, audio=False, obj="WsDisc", obj_src=OBJECT, second="WsShotA"):
    out = tmp_path / "film"
    for kind, n, src in (("shots", "WsShotA", SHOT), ("objects", obj, obj_src)):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    slides = [{"index": 1, "shot": "WsShotA", "narration": "一", "shot_props":
               {"fill": "#0000ff", "object": {"id": obj, "props": {"color": "#ff0000"}}}},
              {"index": 2, "shot": second, "narration": "二", "shot_props": {"fill": "#000000"} if second == "WsShotA" else {}}]
    if audio:
        (out / "audio").mkdir()
        for s in slides:
            mp3 = "audio/%02d.mp3" % s["index"]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                            "-t", "2", str(out / mp3)], check=True)
            s.update(audio=mp3, duration=2.0)
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "language": "zh"}, "slides": slides}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    return str(out)


def test_the_film_s_valid_ids_include_its_workshop(monkeypatch, tmp_path):
    import render_remotion as rr
    out = _film(tmp_path)
    seen = {}

    def fake_build(slides, out_dir, valid, fps=30, **kw):
        seen["valid"] = set(valid)
        return []
    monkeypatch.setattr(rr, "build_scenes", fake_build)
    rr.film_props(out, json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8")))
    assert "WsShotA" in seen["valid"] and "TermTable" in seen["valid"]


def _whole(monkeypatch, tmp_path, with_workshop):
    import render_remotion as rr
    calls = []
    monkeypatch.setattr(rr.subprocess, "run", lambda cmd, cwd=None, check=True, **kw: calls.append(kw))
    monkeypatch.setattr(rr, "_remotion_deliverables", lambda *a, **k: None)
    monkeypatch.setattr(rr, "build_scenes", lambda slides, out_dir, valid, fps=30, **kw: [{"shot": "TermTable", "durF": 60}])
    monkeypatch.setattr(rr.shutil, "which", lambda _x: "/usr/bin/npx")
    monkeypatch.delenv("SLIDES_WORKSHOP", raising=False)
    out = _film(tmp_path) if with_workshop else str(tmp_path)
    rr._render_remotion(out, {"meta": {"renderer": "remotion"}, "slides": [{"index": 1}]}, whole=True)
    return out, calls


def test_the_whole_film_render_runs_with_the_workshop(monkeypatch, tmp_path):
    out, calls = _whole(monkeypatch, tmp_path, True)
    assert calls and calls[0]["env"]["SLIDES_WORKSHOP"] == ws.workshop_dir(out)


def test_without_a_workshop_the_whole_film_render_is_the_call_it_always_was(monkeypatch, tmp_path):
    _out, calls = _whole(monkeypatch, tmp_path, False)
    assert calls == [{}]


def test_the_segment_bundle_carries_the_environment_it_is_given(tmp_path):
    calls = []

    def fake(cmd, cwd=None, check=True, **kw):
        calls.append(kw)
        dest = next(a for a in cmd if a.startswith("--out-dir=")).split("=", 1)[1]
        os.makedirs(dest, exist_ok=True)
        open(os.path.join(dest, "index.html"), "w").close()
    rs._bundle(str(tmp_path / "b"), str(tmp_path), run=fake, env={"SLIDES_WORKSHOP": "/x"})
    rs._bundle(str(tmp_path / "c"), str(tmp_path), run=fake)
    assert calls == [{"env": {"SLIDES_WORKSHOP": "/x"}}, {}]


def test_render_film_bundles_with_the_film_s_workshop(monkeypatch, tmp_path):
    out = _film(tmp_path)
    got = {}

    class Stop(Exception):
        pass

    def spy(dest, public, run=None, env=None):
        got["env"] = env
        raise Stop()
    monkeypatch.setattr(rs, "_bundle", spy)
    with pytest.raises(Stop):
        rs.render_film(out, {"scenes": [{"shot": "WsShotA", "durF": 60}]}, os.path.join(out, "p.json"),
                       os.path.join(out, "o.mp4"), [], {"gl": "angle"}, log=lambda *_: None)
    assert got["env"]["SLIDES_WORKSHOP"] == ws.workshop_dir(out)


def test_the_segment_cache_key_sees_the_workshop_and_not_where_the_film_lives(tmp_path):
    out = _film(tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    h0 = rs.code_hash(str(plain))
    assert h0 == rs.code_hash()
    h1 = rs.code_hash(out)
    assert h1 != h0
    ws.write_index(out)
    assert rs.code_hash(out) == h1                 # the generated index is not a source
    moved = tmp_path / "elsewhere" / "film"
    shutil.copytree(out, str(moved))
    assert rs.code_hash(str(moved)) == h1           # moving the film does not re-render it
    with open(os.path.join(ws.workshop_dir(out), "objects", "WsDisc.tsx"), "a", encoding="utf-8") as fh:
        fh.write("\n// edited\n")
    assert rs.code_hash(out) != h1                  # editing a built thing does


def test_text_safe_measures_workshop_beats_in_their_bundle(monkeypatch, tmp_path):
    import text_safe_qa as g
    out = _film(tmp_path)
    seen = []

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(g.subprocess, "run", lambda cmd, **k: seen.append(k) or R())
    findings, checked, universe, skipped = g.scan_film(out)
    assert (checked, universe, skipped) == (2, 2, []), skipped
    assert seen and all(k.get("env", {}).get("SLIDES_WORKSHOP") == ws.workshop_dir(out) for k in seen)


def test_cjk_type_measures_workshop_beats_in_their_bundle(monkeypatch, tmp_path):
    import cjk_type_qa as c
    out = _film(tmp_path)
    seen = []

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(c.subprocess, "run", lambda cmd, **k: seen.append((cmd, k)) or R())
    monkeypatch.setattr(c, "_ink_fraction", lambda p: 1.0)
    monkeypatch.setattr(c, "evidence_props", lambda: {})
    res = c.sweep(["WsShotA"], film_props={"WsShotA": {"fill": "#000000"}}, out_dir=out)
    assert res["WsShotA"]["failed"] is False
    assert seen and all(k.get("env", {}).get("SLIDES_WORKSHOP") == ws.workshop_dir(out) for _c, k in seen)
    assert "--frame=%d" % int(30 * c.PROBE_FRAC) in seen[0][0]      # the workshop shot's own DURATION
    assert c._RUN_ENV is None                                         # the sweep's environment, not the module's


def test_shot_proof_reads_a_workshop_register_from_the_film(tmp_path):
    import shot_proof as sp
    out = _film(tmp_path)
    sp._FILM_SHOTS[:] = [os.path.join(ws.workshop_dir(out), "shots")]
    try:
        assert sp.exported_props("WsShotA") == {"fill", "object"}
        assert sp._src_path("TermTable").endswith(os.path.join("src", "shots", "TermTable.tsx"))
    finally:
        sp._FILM_SHOTS[:] = []


def test_seam_plan_judges_a_workshop_shot_on_its_declared_ground(monkeypatch):
    import seam_plan
    monkeypatch.setattr(seam_plan, "_EXTRA_GROUNDS", {"WsShotA": ["surface"]})
    assert seam_plan.dna_ground_y("WsShotA", {"surface": "#ffffff", "bg": "#000000"}) == pytest.approx(1.0)
    assert seam_plan.dna_ground_y("NotAShot", {"surface": "#ffffff"}) is None


@needs_toolchain
def test_a_real_film_with_a_workshop_renders_per_beat(tmp_path):
    """The whole path: board -> film_props -> segments (bundle once with the workshop, one render per beat) ->
    joined film, with the workshop shot and its object on the frame."""
    import render_remotion as rr
    out = _film(tmp_path, audio=True, second="TermTable")
    data = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    mp4 = rr._render_remotion(out, data)
    assert os.path.exists(mp4)
    segs = [f for f in os.listdir(os.path.join(out, rs.CACHE_DIR)) if f.endswith(".mov")]
    assert len(segs) == 2, segs
    png = str(tmp_path / "beat1.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.8", "-i", mp4, "-frames:v", "1", png], check=True)
    im = Image.open(png).convert("RGB")
    mid, ground = im.getpixel((960, 540)), im.getpixel((400, 540))
    assert mid[0] > 150 and mid[2] < 90, mid
    assert ground[2] > 150 and ground[0] < 90, ground


@needs_toolchain
def test_a_throwing_object_is_named_by_the_gates(tmp_path, capsys):
    """Review focus: a bug in film code must be reported as the film code's own message by every gate — not as
    the last line of a stack, and never as a clean or blank frame."""
    import text_safe_qa as g
    import cjk_type_qa as c
    import shot_proof as sp
    out = _film(tmp_path, obj="WsBoom", obj_src=BOOM)
    findings, _checked, _u, _s = g.scan_film(out)
    assert any("pressure must be a number" in f for f in findings), findings
    res = c.sweep(["WsShotA"], film_props={"WsShotA": json.load(open(os.path.join(out, "storyboard.json")))
                                           ["slides"][0]["shot_props"]}, out_dir=out)
    assert res["WsShotA"]["failed"] and "pressure must be a number" in (res["WsShotA"]["why"] or ""), res
    rc = sp.main([out])
    printed = capsys.readouterr().out
    assert rc != 0 and "pressure must be a number" in printed, printed[-1500:]
