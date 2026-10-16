"""A conceived direction must reach the screen as ITSELF.

`contest_sample.py --conceived` exists so an author can state a direction as FRAMES and have the user SEE
it. It put the direction's `dna` into the Film's `template` prop, and a conceived DNA is an OBJECT, which
`dnaFromTemplate()` cannot resolve — so every conceived direction rendered in the default look and the
contest asked a user to choose between three ballots none of which had been applied. Measured on a real
three-direction Chinese film: a direction declaring `bg: #F2EDE3` (paper, Y=0.850) came back near-black and
its props file carried no `dna` key at all. That is worse than having no contest, because the ballot looks
real.
"""
import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")


def _mod():
    spec = importlib.util.spec_from_file_location(
        "contest_sample", os.path.join(_SCRIPTS, "contest_sample.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _spec(**kw):
    d = {"key": "paper-dossier", "pitch": "卷宗", "shots": [["EdStat", {"figure": "1000 万"}],
                                                          ["EdCompare", {"kicker": "两种做法"}]]}
    d.update(kw)
    return d


def test_a_conceived_dna_reaches_the_film_as_a_dna_not_as_a_template_name():
    m = _mod()
    dna = {"id": "paper", "bg": "#F2EDE3", "fg": "#101A33", "accent": "#133C9A"}
    p = m.build_props_conceived(_spec(dna=dna), "介绍飞书")
    assert p.get("dna") == dna, (
        "the conceived look went to %r instead of the Film's `dna` prop, so it renders as the default"
        % sorted(p))
    assert "template" not in p, "a conceived DNA must not also claim a preset name: %r" % p.get("template")


def test_a_preset_NAME_still_goes_to_template():
    """The seed path is unchanged — a string names a preset, and `render_remotion.py` routes it the same way."""
    m = _mod()
    p = m.build_props_conceived(_spec(dna="editorial"), "介绍飞书")
    assert p.get("template") == "editorial", p
    assert "dna" not in p, p


def test_the_marked_seam_keeps_its_direction():
    """A film's seam is `{type, direction}`. Wrapping it as `{"type": <the whole object>}` makes the one
    marked cut in the sample anonymous, which is the same defect one layer down."""
    m = _mod()
    p = m.build_props_conceived(_spec(dna={"id": "x"}, seam={"type": "wipe", "direction": "from-top"}),
                                "介绍飞书")
    assert p["scenes"][1]["transitionIn"] == {"type": "wipe", "direction": "from-top"}, \
        p["scenes"][1]["transitionIn"]
    # ...and a bare string is still accepted, since that is how the seeds spell it
    q = m.build_props_conceived(_spec(dna={"id": "x"}, seam="clock"), "介绍飞书")
    assert q["scenes"][1]["transitionIn"] == {"type": "clock"}, q["scenes"][1]["transitionIn"]


def test_a_direction_with_no_frames_is_refused():
    """A direction that cannot be rendered is a pitch, and the contest exists so the user SEES it."""
    m = _mod()
    import pytest
    with pytest.raises(SystemExit):
        m.build_props_conceived(_spec(shots=[]), "介绍飞书")


# ── a direction is DESIGNED first: its ideal, its palette's provenance, and a hero BUILT for this film ─────────

def _film_with_hero(tmp_path, name="OrbitPulse"):
    out = tmp_path / "film"
    (out / "workshop" / "shots").mkdir(parents=True)
    (out / "workshop" / "shots" / ("%s.tsx" % name)).write_text("export const %s = () => null;\n" % name)
    return str(out)


def test_a_library_register_cannot_be_a_directions_hero(tmp_path):
    # the GPS film's first contest: SplitFlap / MapPlate / HudReticle as heroes, in signal red — the user rejected all
    # three as existing templates suited to nothing in the subject
    m = _mod()
    out = _film_with_hero(tmp_path)
    good = _spec(ideal="four light-speed pulses converge on one phone while its clock is corrected",
                 palette_source=[{"colour": "#0b1d3a", "from": "the night sky the orbits sit in"}],
                 shots=[["OrbitPulse", {}], ["EdStat", {"figure": "3 纳秒"}]])
    assert m.direction_problems(good, out) == []
    bad = dict(good, shots=[["SplitFlap", {}], ["OrbitPulse", {}]])
    probs = m.direction_problems(bad, out)
    assert any("'SplitFlap' is a library register" in p and "new-shot" in p for p in probs), probs
    probs = m.direction_problems(dict(good, shots=[["NotBuiltYet", {}]]), out)
    assert any("not a shot in this film's workshop" in p for p in probs), probs


def test_a_direction_needs_an_ideal_and_a_palette_traced_to_the_subject(tmp_path):
    m = _mod()
    out = _film_with_hero(tmp_path)
    base = _spec(shots=[["OrbitPulse", {}]])
    probs = m.direction_problems(base, out)
    assert any("no `ideal`" in p for p in probs) and any("no `palette_source`" in p for p in probs), probs
    named = dict(base, ideal="a SplitFlap board of satellites announcing their send times",
                 palette_source=[{"colour": "#c62828", "from": "x"}])
    probs = m.direction_problems(named, out)
    assert any("names a library register (SplitFlap)" in p for p in probs), probs
    assert any("no `palette_source`" in p for p in probs), "a `from` too thin to name a source is no provenance"


def test_the_cli_refuses_an_undesigned_direction_and_renders_nothing(tmp_path):
    import json
    import subprocess
    import sys
    out = _film_with_hero(tmp_path)
    spec = tmp_path / "dirs.json"
    spec.write_text(json.dumps([_spec(shots=[["MapPlate", {}]])], ensure_ascii=False))
    p = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "contest_sample.py"), "--route", "GPS 怎么定位",
                        "--out", out, "--conceived", str(spec), "--render"], capture_output=True, text=True)
    assert p.returncode == 2 and "REFUSED" in p.stdout and "'MapPlate' is a library register" in p.stdout, p.stdout
    assert not [f for f in os.listdir(out) if f.startswith("_contest_") and f.endswith(".mp4")]


def test_the_routers_printed_render_command_runs_as_printed(tmp_path):
    # it printed `contest_sample.py --conceived <file.json> --out <dir> --render`, which exits 2: --route is required
    import subprocess
    import sys
    p = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "shot_templates.py"), "--route",
                        "一支关于宋代茶盏釉色的短片", "--audacity", "balanced", "--out", str(tmp_path)],
                       capture_output=True, text=True)
    line = next(x for x in p.stdout.splitlines() if "contest_sample.py" in x)
    assert "python3 scripts/contest_sample.py --route" in line and "--audacity balanced" in line, line


def test_the_still_is_the_hero_before_the_seam_and_a_shot_may_set_its_length():
    # frame 67 of a 75-frame hero slot fell inside the 12-frame seam into scene 2: every still of the GPS film's
    # second contest showed its hero half wiped. And HeldInstant refuses 2.5 s, which aborted a whole direction.
    m = _mod()
    p = m.build_props_conceived(_spec(shots=[["OrbitPulse", {}, 120], ["EdStat", {"figure": "3 纳秒"}]]), "GPS")
    assert [sc["durF"] for sc in p["scenes"]] == [120, m.SCENE_F]
    assert m.settled_frame(p) == int((120 - m.TR_F) * 0.9) < 120 - m.TR_F
    one = m.build_props_conceived(_spec(shots=[["OrbitPulse", {}]]), "GPS")
    assert m.settled_frame(one) == int(m.SCENE_F * 0.9), "a lone hero has no seam to avoid"
