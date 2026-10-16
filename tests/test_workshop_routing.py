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
    # This unit test never renders anything (subprocess.run is replaced above), so it must not depend on the
    # real toolchain being installed either — only the one os.path.isdir check that gates a render is forced;
    # every other isdir call (a workshop's own folders included) reaches the real filesystem.
    real_isdir = os.path.isdir
    node_modules = os.path.join(rr._REMOTION2_DIR, "node_modules")
    monkeypatch.setattr(rr.os.path, "isdir", lambda p: True if p == node_modules else real_isdir(p))
    monkeypatch.delenv("SLIDES_WORKSHOP", raising=False)
    out = _film(tmp_path) if with_workshop else str(tmp_path)
    rr._render_remotion(out, {"meta": {"renderer": "remotion"}, "slides": [{"index": 1}]}, whole=True)
    return out, calls


def test_the_whole_film_render_runs_with_the_workshop(monkeypatch, tmp_path):
    out, calls = _whole(monkeypatch, tmp_path, True)
    assert calls and calls[0]["env"]["SLIDES_WORKSHOP"] == ws.workshop_dir(out)


def test_without_a_workshop_the_whole_film_render_passes_no_extra_environment(monkeypatch, tmp_path):
    _out, calls = _whole(monkeypatch, tmp_path, False)
    # the render itself is the call that does not capture output (the sync census's pre-pass does)
    assert [c for c in calls if not c.get("capture_output")] == [{}]
    assert not any("SLIDES_WORKSHOP" in (c.get("env") or {}) for c in calls)


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


def test_editing_one_built_object_re_renders_only_the_beats_that_use_it(tmp_path):
    """The segment key used to hash the WHOLE workshop, so one edited object re-rendered every beat. Now each
    segment hashes the workshop files its own scenes are built from (the beat, and the one dissolving out of it
    in the segment's opening frames): its shot, the objects its props reference, and their relative imports."""
    out = _film(tmp_path)                              # shots/WsShotA, objects/WsDisc
    objs = os.path.join(ws.workshop_dir(out), "objects")
    with open(os.path.join(objs, "WsCube.tsx"), "w", encoding="utf-8") as fh:
        fh.write(OBJECT.replace("({w, h, color = '#ff0000'})", "({w, h, color = '#ff0000'})")
                 .replace("%(name)s", "WsCube").replace("import React from 'react';",
                                                         "import React from 'react';\nimport {EDGE} from './cubeEdge';"))
    with open(os.path.join(objs, "cubeEdge.ts"), "w", encoding="utf-8") as fh:
        fh.write("export const EDGE = 2;\n")
    ref = lambda i: {"fill": "#000000", "object": {"id": i, "props": {}}}  # noqa: E731
    props = {"scenes": [{"shot": "WsShotA", "props": ref("WsDisc"), "durF": 60},
                        {"shot": "Aliasing", "props": {}, "durF": 60},
                        {"shot": "WsShotA", "props": ref("WsCube"), "durF": 60},
                        {"shot": "Aliasing", "props": {}, "durF": 60}]}

    def keys():
        return [s["key"] for s in rs.plan(props, out, {"gl": "angle"})[0]]

    def changed(before):
        return [k for k, (x, y) in enumerate(zip(before, keys())) if x != y]

    def edit(path):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n// edited\n")

    k0 = keys()
    assert keys() == k0
    edit(os.path.join(objs, "WsDisc.tsx"))
    assert changed(k0) == [0, 1], "WsDisc is beat 0's; beat 1's segment opens on the dissolve out of it"
    k1 = keys()
    edit(os.path.join(objs, "cubeEdge.ts"))            # reached only through WsCube's relative import
    assert changed(k1) == [2, 3]
    k2 = keys()
    edit(os.path.join(ws.workshop_dir(out), "shots", "WsShotA.tsx"))
    assert changed(k2) == [0, 1, 2, 3]
    k3 = keys()
    with open(os.path.join(objs, "WsNew.tsx"), "w", encoding="utf-8") as fh:
        fh.write(OBJECT % {"name": "WsNew"})           # a new item changes the generated index every beat bundles
    assert changed(k3) == [0, 1, 2, 3]


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


def test_seam_plan_judges_a_workshop_shot_on_its_declared_ground(tmp_path):
    import seam_plan
    out = _film(tmp_path)
    seam_plan.install_workshop(out)
    try:
        assert seam_plan.dna_ground_y("WsShotA", {"bg": "#000000", "surface": "#ffffff"}) == pytest.approx(0.0)
        assert seam_plan.dna_ground_y("NotAShot", {"surface": "#ffffff"}) is None
    finally:
        seam_plan.clear_workshop()


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
    """A bug in film code is reported as the film code's own message by every gate — not as the last line of a
    stack, and never as a clean or blank frame."""
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


# ── a workshop shot's DURATION reads the same way in every gate ───────────────────────────────────────────
_DUR_TYPED = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION: number = 40;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{}> = () => <AbsoluteFill style={{background: '#112233'}} />;
"""

# A commented-out decoy ABOVE the real declaration — a regex that does not strip comments first, or is not
# anchored to a line start, reads the decoy's number instead of the one that actually governs the clip.
_DUR_COMMENTED = """import React from 'react';
import {AbsoluteFill} from 'remotion';
// export const DURATION = 45;
export const DURATION = 40;
export const GROUND = 'bg';
export const PROVENANCE = 'motion-graphics';
export const %(name)s: React.FC<{}> = () => <AbsoluteFill style={{background: '#112233'}} />;
"""


def _dur_film(tmp_path):
    out = tmp_path / "durfilm"
    d = out / "workshop" / "shots"
    d.mkdir(parents=True)
    for n, src in (("WsDurTyped", _DUR_TYPED), ("WsDurCommented", _DUR_COMMENTED)):
        (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "language": "zh"},
             "slides": [{"index": 1, "shot": "WsDurTyped", "narration": "一", "shot_props": {}},
                        {"index": 2, "shot": "WsDurCommented", "narration": "二", "shot_props": {}}]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    return str(out)


def test_shot_proof_proves_a_workshop_shot_at_the_gates_shared_settled_frame(monkeypatch, tmp_path):
    import shot_proof as sp
    import render_remotion as rr
    out = _dur_film(tmp_path)
    seen = {}

    class R:
        returncode, stdout, stderr = 1, "", "boom"

    def spy(cmd, **kw):
        if len(cmd) > 4 and cmd[:3] == ["npx", "remotion", "still"]:
            frame = next(a for a in cmd if a.startswith("--frame=")).split("=", 1)[1]
            seen[cmd[4]] = int(frame)
        return R()
    monkeypatch.setattr(sp.subprocess, "run", spy)
    sp.main([out])
    want = int(round(rr.frame_at_t(40, rr.SETTLED_T)))
    assert seen.get("WsDurTyped") == want, seen
    assert seen.get("WsDurCommented") == want, seen


# ── the segment cache key does not depend on where the film sits on disk ──────────────────────────────────
def test_the_cache_key_does_not_depend_on_which_side_of_the_skill_the_film_sits(tmp_path):
    out = _film(tmp_path)
    real = os.path.realpath(out)
    alias = os.path.join("/System/Volumes/Data", real.lstrip("/"))
    if not (os.path.isdir(alias) and os.stat(alias).st_ino == os.stat(real).st_ino):
        pytest.skip("no /System/Volumes/Data alias for this machine's tmp_path")
    assert rs.code_hash(alias) == rs.code_hash(real)


# ── film-scoped module state never outlives the run that set it ───────────────────────────────────────────
def test_shot_proof_s_film_state_is_cleared_after_main_returns(tmp_path):
    import shot_proof as sp
    out = _film(tmp_path)
    sp.main([out, "--no-stills"])
    assert sp._FILM_SHOTS == [] and sp._FILM_ENV == {}


def test_shot_proof_s_film_state_is_cleared_after_main_raises(monkeypatch, tmp_path):
    import shot_proof as sp
    out = _film(tmp_path)

    def boom(*_a, **_k):
        raise RuntimeError("boom")
    monkeypatch.setattr(sp, "static_checks", boom)
    with pytest.raises(RuntimeError):
        sp.main([out, "--no-stills"])
    assert sp._FILM_SHOTS == [] and sp._FILM_ENV == {}


def test_seam_plan_s_workshop_state_is_cleared_after_main_returns(tmp_path):
    import seam_plan
    out = _film(tmp_path)
    seam_plan.main([out, "--dry-run"])
    assert seam_plan._EXTRA_GROUNDS == {} and seam_plan._EXTRA_PROVENANCE == {}


def test_seam_plan_s_workshop_state_is_cleared_after_main_raises(monkeypatch, tmp_path):
    import seam_plan
    out = _film(tmp_path)

    def boom(*_a, **_k):
        raise RuntimeError("boom")
    monkeypatch.setattr(seam_plan, "plan", boom)
    with pytest.raises(RuntimeError):
        seam_plan.main([out])
    assert seam_plan._EXTRA_GROUNDS == {} and seam_plan._EXTRA_PROVENANCE == {}


def test_cjk_type_s_run_env_is_none_after_sweep_raises(monkeypatch, tmp_path):
    import cjk_type_qa as c
    out = _film(tmp_path)

    def boom():
        raise RuntimeError("boom")
    monkeypatch.setattr(c, "evidence_props", boom)
    with pytest.raises(RuntimeError):
        c.sweep(["WsShotA"], film_props={"WsShotA": {"fill": "#000000"}}, out_dir=out)
    assert c._RUN_ENV is None


# ── the seam planner's workshop declarations reach shot_director's own call path too ──────────────────────
def test_shot_director_installs_the_workshop_before_planning_seams(monkeypatch, tmp_path):
    import shot_director
    import seam_plan
    out = _film(tmp_path)
    # the plan runs on ROUTED beats only (a proposal's camera would be planned for a register the beat drops)
    b = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    for sl in b["slides"]:
        sl["shot_fit"] = {"verdict": "build", "ref": "WsShotA", "ideal": "a disc the beat built for itself"}
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)
    seen = {}
    real_plan = seam_plan.plan

    def spy_plan(slides, dna=None):
        seen["grounds"] = dict(seam_plan._EXTRA_GROUNDS)
        return real_plan(slides, dna)
    monkeypatch.setattr(seam_plan, "plan", spy_plan)
    monkeypatch.setattr(sys, "argv", ["shot_director.py", out])
    shot_director.main()
    assert seen.get("grounds", {}).get("WsShotA") == ["bg"], seen
    assert seam_plan._EXTRA_GROUNDS == {} and seam_plan._EXTRA_PROVENANCE == {}


# ── a broken workshop is a named problem and exit 2, in every gate — never a raw traceback ────────────────
def _broken_workshop_film(tmp_path):
    out = tmp_path / "broken"
    d = out / "workshop" / "shots"
    d.mkdir(parents=True)
    (d / "WsBad.tsx").write_text((SHOT % {"name": "WsBad"}).replace("DURATION = 30", "DURATION = 0"),
                                 encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "design_dna": "product", "language": "zh"},
             "slides": [{"index": 1, "shot": "WsBad", "narration": "一", "shot_props": {}}]}
    (out / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    return str(out)


def test_a_broken_workshop_is_named_and_exits_2_from_every_gate(capsys, tmp_path):
    import text_safe_qa as g
    import cjk_type_qa as c
    import shot_proof as sp
    out = _broken_workshop_film(tmp_path)
    for mod, name, extra in ((g, "text_safe_qa", []), (c, "cjk_type_qa", []), (sp, "shot_proof", ["--no-stills"])):
        rc = mod.main([out] + extra)
        printed = capsys.readouterr().out
        assert rc == 2, (name, rc, printed)
        assert "DURATION" in printed, (name, printed)


# ── a direct film-mode sweep renders against the film's own assets, not the library's ─────────────────────
def test_cjk_type_sweep_renders_against_the_film_s_own_public_dir(monkeypatch, tmp_path):
    import cjk_type_qa as c
    out = _film(tmp_path)
    prev_public = c.PUBLIC_DIR
    seen = []

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(c.subprocess, "run", lambda cmd, **k: seen.append(cmd) or R())
    monkeypatch.setattr(c, "_ink_fraction", lambda p: 1.0)
    monkeypatch.setattr(c, "evidence_props", lambda: {})
    c.sweep(["WsShotA"], film_props={"WsShotA": {"fill": "#000000"}}, out_dir=out)
    assert seen and all(("--public-dir=" + os.path.abspath(out)) in cmd for cmd in seen), seen
    assert c.PUBLIC_DIR == prev_public, "the library's public dir was not restored after the sweep"


def test_shot_director_plans_no_camera_for_beats_it_only_proposed(monkeypatch, tmp_path, capsys):
    # the GPS test film: the material pass wrote a camera on beat 1 for a register it merely proposed, and
    # seam_plan then skipped that beat as "authored"
    import shot_director
    out = _film(tmp_path)
    b = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    for sl in b["slides"]:
        sl["shot_fit"] = {"verdict": "unjudged", "material": sl["shot"]}
        sl["relation"] = "new-topic"
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8"), ensure_ascii=False)
    monkeypatch.setattr(sys, "argv", ["shot_director.py", out])
    shot_director.main()
    said = capsys.readouterr().out
    assert "still carry proposed material" in said and "seam_plan.py" in said, said
    after = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    assert not any(sl.get("camera") or sl.get("transition_in") for sl in after["slides"])


def test_the_proposals_name_the_films_own_material_first(tmp_path):
    """The keyword proposals never read the ideal (the compound test drew LiquidChrome for a passbook's cloth cover);
    the film's own workshop is named before them, and the built half is stated."""
    import subprocess
    out = tmp_path / "film"
    d = out / "workshop" / "shots"
    d.mkdir(parents=True)
    from test_build_list import SHOT
    (d / "PassbookCarry.tsx").write_text(SHOT % {"name": "PassbookCarry"}, encoding="utf-8")
    (out / "storyboard.json").write_text(json.dumps({"meta": {}, "slides": [
        {"index": 1, "narration": "x", "shot_fit": {"ideal": "a passbook page prints its first line"}}]}),
        encoding="utf-8")
    p = subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "shot_director.py"), str(out)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "OWN material" in p.stdout and "PassbookCarry" in p.stdout, p.stdout
    assert "HALF the non-exempt beats BUILT" in p.stdout, p.stdout
