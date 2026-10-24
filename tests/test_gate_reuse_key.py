"""A recorded gate verdict is reused under a key over what THAT gate reads — not over every file near the film.

Three benchmark films lost 13-43 min per re-gate to files no gate opens: the run's notes written beside the film, a
contact sheet saved next to it, an edit to `meta.script_review`, and another agent merging a branch into the skill
(critic_brief.gate_inputs hashed all of scripts/ and remotion/src for every gate). And a plain brief after a clean
`--gates` left `_gate_runs.json` holding 11 of 15 gates — failures were not recorded at all — with nothing saying why
a pass had turned into a failure on the same render."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, HERE)
import critic_brief as cb  # noqa: E402
import critic_ledger as cl  # noqa: E402
from test_review_html import SHARES, _html_film  # noqa: E402


def _film(tmp_path, monkeypatch, codes=None):
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    calls = []

    def fake(script, out_dir, *a, **k):
        calls.append(cl.gate_name(script, a))
        return cb.GateOutput("(stub %s)" % script, (codes or {}).get(script, 0))
    monkeypatch.setattr(cb, "_run", fake)
    # keyframe_qa runs before the sheet and keeps its own record (critic_brief.keyframe_qa), never this one
    need = sorted(cl.gate_name(s, a) for _l, s, a, _t, _b in cl.delivery_gates(out) if s != "keyframe_qa.py")
    return out, calls, need


def _record(out):
    return json.load(open(os.path.join(out, cb.GATE_RUNS), encoding="utf-8"))


def test_notes_a_sheet_beside_the_film_and_the_script_review_are_not_gate_inputs(tmp_path, monkeypatch):
    out, calls, need = _film(tmp_path, monkeypatch)
    assert cb.main([out, "--gates"]) == 0 and sorted(set(calls) & set(need)) == need
    open(os.path.join(out, "bench_notes.md"), "w").write("# notes written after the gates\n")
    open(os.path.join(out, "contact_sheet_settled.png"), "wb").write(b"\x89PNG not a gate input")
    open(os.path.join(out, "script_review.json"), "w").write('{"verdict": "REVISE"}')
    b = json.load(open(os.path.join(out, "storyboard.json")))
    b["meta"]["script_review"] = {"mode": "combined", "rounds": 1}
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    calls.clear()
    assert cb.main([out]) == 0
    assert [c for c in calls if c != "keyframe_qa.py"] == [], "the brief re-ran %s for files no gate reads" % calls


def test_a_top_level_picture_the_board_names_is_an_input(tmp_path, monkeypatch):
    out, calls, need = _film(tmp_path, monkeypatch)
    assert cb.main([out, "--gates"]) == 0
    b = json.load(open(os.path.join(out, "storyboard.json")))
    b["slides"][0]["props"]["image"] = "hero.png"
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    cb.main([out, "--gates"])
    open(os.path.join(out, "hero.png"), "wb").write(b"a new picture of the beat")
    calls.clear()
    cb.main([out, "--gates"])
    assert sorted(set(calls) & set(need)) == need, "a picture the board draws changed and %s were reused" % sorted(set(need) - set(calls))


def test_a_failure_is_recorded_with_its_output_and_a_flip_is_said(tmp_path, monkeypatch, capsys):
    codes = {}
    out, calls, need = _film(tmp_path, monkeypatch, codes)
    assert cb.main([out, "--gates"]) == 0
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    open(os.path.join(out, "media", "new.png"), "wb").write(b"x")       # an input: every gate runs again
    codes["check_av.py"] = 1
    capsys.readouterr()
    cb.main([out, "--gates"])
    said = capsys.readouterr().out
    rec = _record(out)
    assert sorted(rec["gates"]) == need, "the record lost gates: %s" % sorted(set(need) - set(rec["gates"]))
    assert rec["gates"]["check_av.py"]["exit"] == 1 and "(stub check_av.py)" in rec["gates"]["check_av.py"]["output"]
    assert "check_av.py PASSED on this same render" in said and "media/new.png" in said
    # ...and a recorded failure is never replayed: the next run runs it again (and only it)
    codes.pop("check_av.py")
    calls.clear()
    cb.main([out, "--gates"])
    assert [c for c in calls if c != "keyframe_qa.py"] == ["check_av.py"], calls


def test_an_interrupted_run_keeps_the_earlier_entries(tmp_path, monkeypatch):
    out, calls, need = _film(tmp_path, monkeypatch)
    assert cb.main([out, "--gates"]) == 0
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    open(os.path.join(out, "media", "new.png"), "wb").write(b"x")
    n = [0]

    def dies(script, out_dir, *a, **k):
        n[0] += 1
        if n[0] == 3:
            raise KeyboardInterrupt
        return cb.GateOutput("(stub %s)" % script, 0)
    monkeypatch.setattr(cb, "_run", dies)
    with pytest.raises(KeyboardInterrupt):
        cb.main([out, "--gates"])
    assert sorted(_record(out)["gates"]) == need, "an interrupted run left a half-written record"


def _skill(tmp_path):
    sk = tmp_path / "skill"
    (sk / "scripts").mkdir(parents=True)
    (sk / "remotion" / "src").mkdir(parents=True)
    (sk / "scripts" / "gate_a.py").write_text("import helper\nCMD = ['npx', 'remotion', 'still']\n")
    (sk / "scripts" / "helper.py").write_text("def f():\n    import deep\n")
    (sk / "scripts" / "deep.py").write_text("X = 1\n")
    (sk / "scripts" / "gate_b.py").write_text("import json\nRUN = 'tool.cjs'\n")
    (sk / "scripts" / "tool.cjs").write_text("// node helper\n")
    (sk / "scripts" / "unrelated.py").write_text("Y = 1\n")
    (sk / "remotion" / "src" / "Film.tsx").write_text("export const A = 1;\n")
    film = tmp_path / "film"
    film.mkdir()
    (film / "storyboard.json").write_text("{}")
    return sk, film


def test_a_gate_key_follows_that_gates_own_code(tmp_path, monkeypatch):
    sk, film = _skill(tmp_path)
    monkeypatch.setattr(cb, "_HERE", str(sk / "scripts"))
    keys = lambda: {g: cb.gate_key(g, (), cb.input_files(str(film))) for g in ("gate_a.py", "gate_b.py")}
    k0 = keys()
    (sk / "scripts" / "unrelated.py").write_text("Y = 2\n")                    # another agent's merge
    assert keys() == k0, "an edit no gate imports re-ran a gate"
    (sk / "scripts" / "deep.py").write_text("X = 2\n")                         # gate_a imports it, two levels down
    k1 = keys()
    assert k1["gate_a.py"] != k0["gate_a.py"] and k1["gate_b.py"] == k0["gate_b.py"]
    (sk / "scripts" / "tool.cjs").write_text("// changed\n")                   # gate_b names it by literal
    k2 = keys()
    assert k2["gate_b.py"] != k1["gate_b.py"] and k2["gate_a.py"] == k1["gate_a.py"]
    (sk / "remotion" / "src" / "Film.tsx").write_text("export const A = 2;\n")  # only the gate that renders
    k3 = keys()
    assert k3["gate_a.py"] != k2["gate_a.py"] and k3["gate_b.py"] == k2["gate_b.py"]
    (film / "storyboard.json").write_text('{"slides": []}')                    # the film is every gate's input
    k4 = keys()
    assert k4["gate_a.py"] != k3["gate_a.py"] and k4["gate_b.py"] != k3["gate_b.py"]
