"""The flow reaches the agents that run it. A capability the authoring path cannot name is indistinguishable from
one that was never built — this repo has shipped that shape before (a seam vocabulary complete, tested and unused)."""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


def _read(*p):
    return open(os.path.join(_ROOT, *p), encoding="utf-8").read()


def test_the_shot_director_is_told_to_build_and_how():
    d = _read("agents", "shot-director.md")
    for needle in ("## Step 0.55 — NEED FIRST", "meta.build_list", '"ref"', "workshop.py <out_dir> new-object",
                   "workshop.py <out_dir> new-shot", "workshop.py <out_dir> still", "ObjectStage", "ObjectCompare",
                   "ObjectPath", "ObjectTurntable", "references/object-authoring.md", "references/building-blocks.md",
                   "scripts/promote.py"):
        assert needle in d, needle


def test_s15_is_a_dimension_the_ledger_requires():
    import critic_ledger
    dims = dict(critic_ledger.dimensions())
    assert "S15" in dims and "BUILT THINGS" in dims["S15"]
    assert critic_ledger.precedents()["S15"] is None          # doctrine: no film has failed it yet


def test_the_critic_brief_lists_what_the_film_built(tmp_path, monkeypatch):
    import critic_brief
    monkeypatch.setattr(critic_brief, "_run", lambda *a, **k: "(stubbed)")
    board = {"meta": {"renderer": "remotion", "language": "zh",
                      "build_list": [{"id": "EspressoPuck", "kind": "object", "beats": [3], "slot": "ObjectStage",
                                      "means": "water forced through a packed bed",
                                      "accept": "caption hidden, the bed resists"}]},
             "slides": [{"index": 3, "shot": "ObjectStage", "shot_fit": {"verdict": "build", "ref": "EspressoPuck"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    text = critic_brief.build(str(tmp_path))
    assert "**Built things**" in text and "`EspressoPuck`" in text
    assert "water forced through a packed bed" in text and "caption hidden, the bed resists" in text


def test_skill_md_names_the_workshop_the_build_list_and_promotion():
    s = _read("SKILL.md")
    for needle in ("scripts/workshop.py", "meta.build_list", "scripts/promote.py", "references/object-authoring.md",
                   "PROMOTION IS THE USER'S CHOICE"):
        assert needle in s, needle


def test_the_authoring_reference_points_at_the_builder_s_two_references():
    a = _read("references", "remotion-shot-authoring.md")
    assert "references/building-blocks.md" in a and "references/object-authoring.md" in a


def test_every_workshop_command_in_the_docs_puts_the_film_before_the_subcommand():
    """`workshop.py <out_dir> <subcommand> …` is the only order its parser accepts; a command written the other
    way round (`workshop.py still <out_dir> <Name>`) exits 2 for whoever copies it. A bare subcommand name with
    no argument after it is a mention, not a command, and is left alone."""
    import re
    import workshop
    subs = "|".join(re.escape(c) for c in ("list", "check", "new-object", "new-shot", "still"))
    wrong = re.compile(r"workshop\.py\s+(?:%s)\s+(?![|`)\]])\S" % subs)
    found = []
    for folder, ext in (("references", ".md"), ("agents", ".md"), (os.path.join("remotion", "cards"), ".md")):
        for f in sorted(os.listdir(os.path.join(_ROOT, folder))):
            if f.endswith(ext):
                found += ["%s/%s: %s" % (folder, f, m.group(0)) for m in wrong.finditer(_read(folder, f))]
    for f in ("SKILL.md", "README.md"):
        found += ["%s: %s" % (f, m.group(0)) for m in wrong.finditer(_read(f))]
    assert not found, found
    # and the parser really does refuse the reversed order, so this is a real defect and not a style rule
    try:
        workshop.main(["still", "some_film", "SomeObject"])
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("workshop.py accepted a subcommand where the film's folder belongs")


def test_the_critic_brief_reads_a_film_that_built_its_own_shot(tmp_path, monkeypatch):
    """A film-built shot belongs to no library family. Counted as one, its family is None, and sorting None
    against the family letters crashes the brief — on exactly the films the build flow exists for."""
    import critic_brief
    import workshop as ws
    from test_workshop_bundle import SHOT
    monkeypatch.setattr(critic_brief, "_run", lambda *a, **k: "(stubbed)")
    d = tmp_path / "workshop" / "shots"
    d.mkdir(parents=True)
    (d / "WsGradient.tsx").write_text(SHOT % {"name": "WsGradient"}, encoding="utf-8")
    board = {"meta": {"renderer": "remotion", "language": "zh",
                      "build_list": [{"id": "WsGradient", "kind": "shot", "beats": [2], "slot": "own",
                                      "means": "rates spread with position", "accept": "caption hidden, it spreads"}]},
             "slides": [{"index": 1, "shot": "SpinningProton", "narration": "一"},
                        {"index": 2, "shot": "WsGradient", "narration": "二",
                         "shot_fit": {"verdict": "build", "ref": "WsGradient"}}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    text = critic_brief.build(str(tmp_path))
    assert "| 2 | WsGradient | built (this film) |" in text, text
    assert "and 1 beat(s) on this film's own shots (WsGradient)" in text, text
    assert ws.shot_names(str(tmp_path)) == {"WsGradient"}


def test_library_growth_counts_what_the_film_built_not_the_beats_that_use_it(tmp_path, monkeypatch):
    """One object drawn for three beats is one built thing, not three new registers."""
    import critic_brief
    monkeypatch.setattr(critic_brief, "_run", lambda *a, **k: "(stubbed)")
    board = {"meta": {"renderer": "remotion", "language": "zh",
                      "build_list": [{"id": "EspressoPuck", "kind": "object", "beats": [1, 2, 3],
                                      "slot": ["ObjectStage", "ObjectCompare"], "means": "m", "accept": "a"}]},
             "slides": [{"index": i, "shot": "ObjectStage", "narration": "x",
                         "shot_fit": {"verdict": "build", "ref": "EspressoPuck"}} for i in (1, 2, 3)]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    text = critic_brief.build(str(tmp_path))
    assert "this film built 1 object(s), used on beats [1, 2, 3]" in text, text
    assert "new register(s)" not in text
