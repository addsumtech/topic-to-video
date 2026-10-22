"""energy_skeleton — the film's registers must follow the energy its plan declared.

The five rules are pinned one at a time (and mutated one at a time) in test_rules_are_load_bearing.py on a
synthetic six-register library. These tests are the OTHER half: the module against the real sweep, the real
candidate pools, the storyboard on disk, validate, and the deterministic director — where the defect this
exists for actually lived (a delivered film's climax on a register under the motion floor).
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "scripts"))

import energy_skeleton as es          # noqa: E402
import shot_director as sd            # noqa: E402


def _sweep():
    motion, floor, qc, kc, why = es.load_sweep()
    if why:
        pytest.skip(why)
    return motion, floor, qc, kc


def test_the_library_sweep_gives_ordered_bands():
    motion, floor, qc, kc = _sweep()
    assert 0 < qc <= kc and floor > 0 and len(motion) > 100
    assert any(m >= max(qc, floor) for m in motion.values()), "there is always something to give a peak"


def test_declared_energy_precedence():
    assert es.declared({"energy": "HIGH"}, {"energy": "low"}) == "high", "the board's own field wins"
    assert es.declared({}, {"energy": "peak"}) == "peak"
    assert es.declared({"relation": "close"}, {}) == "low", "a close with nothing declared is the sparse hold"
    assert es.declared({}, {"climax": True}) == "peak"
    assert es.declared({"energy": "wild"}, {}) == "medium", "an unknown word is not an energy"


def test_alternatives_are_in_band_unused_and_family_varied():
    motion, floor, qc, kc = _sweep()
    stillest = min((c for c in sd.CANDIDATES["statement"] if c in motion), key=motion.get)
    slides = [{"index": 0, "shot": "ChatThread"}, {"index": 1, "shot": stillest, "energy": "high"},
              {"index": 2, "shot": "QuadSplit"}]
    plan = {"beats": [{"id": i + 1, "visual_intent": "statement"} for i in range(3)]}
    hits = [f for f in es.findings(slides, motion, floor, qc, kc, plan) if f["kind"] == "high-on-quiet"]
    assert hits and hits[0]["beat"] == 2 and hits[0]["alternatives"], "a fix is named, not just a fault"
    used = {"ChatThread", stillest, "QuadSplit"}
    near = {sd.FAMILY.get("ChatThread"), sd.FAMILY.get("QuadSplit")}
    for a in hits[0]["alternatives"]:
        assert motion[a] >= qc and a not in used and sd.FAMILY.get(a) not in near, a


def test_stale_rows_are_dropped_not_fatal(monkeypatch):
    import register_energy as reg
    names = sorted(json.load(open(reg.MANIFEST, encoding="utf-8"))["registers"])
    monkeypatch.setattr(reg, "stale", lambda d: [(names[0], "source changed since it was measured")])
    motion, floor, qc, kc, why = es.load_sweep()
    assert why is None and names[0] not in motion and names[1] in motion, "ONE edited register drops one row"
    monkeypatch.setattr(reg, "stale", lambda d: [(n, "changed") for n in names[: len(names) // 2]])
    motion, floor, qc, kc, why = es.load_sweep()
    assert motion is None and "STALE" in why, "half the library changed: no basis, and it says so"


def test_check_reads_the_out_dir_and_the_curve_aligns(tmp_path):
    motion, floor, qc, kc = _sweep()
    stillest, liveliest = min(motion, key=motion.get), max(motion, key=motion.get)
    board = {"meta": {"renderer": "remotion"},
             "slides": [{"index": 0, "shot": stillest, "energy": "high"},
                        {"index": 1, "shot": liveliest, "energy": "low"},
                        {"index": 2, "shot": "NoSuchRegister", "energy": "peak"}]}
    json.dump(board, open(tmp_path / "storyboard.json", "w", encoding="utf-8"))
    fs, cv, why = es.check(str(tmp_path))
    assert why is None
    kinds = {f["kind"] for f in fs}
    assert "high-on-quiet" in kinds and "low-on-kinetic" in kinds
    assert not [f for f in fs if f.get("shot") == "NoSuchRegister" and f["kind"] in es.HARD], \
        "an unmeasured register is reported as unmeasured, never as a mismatch"
    assert cv[0] == "HLP" and len(cv[1]) == 3 and cv[1].endswith("?")


def test_cli_exit_code_follows_the_hard_findings(tmp_path, capsys):
    motion, floor, qc, kc = _sweep()
    stillest = min(motion, key=motion.get)
    json.dump({"slides": [{"index": 0, "shot": stillest, "energy": "peak"}]},
              open(tmp_path / "storyboard.json", "w", encoding="utf-8"))
    assert es.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "declared" in out and "measured" in out and "under the delivery motion floor" in out
    calm = min((n for n, m in motion.items() if m < kc), key=motion.get)
    json.dump({"slides": [{"index": 0, "shot": calm, "energy": "low"}]},
              open(tmp_path / "storyboard.json", "w", encoding="utf-8"))
    assert es.main([str(tmp_path)]) == 0
    assert "follow the plan's skeleton" in capsys.readouterr().out


def test_validate_repeats_the_findings_as_warnings(tmp_path):
    import validate
    motion, floor, qc, kc = _sweep()
    stillest = min((c for c in sd.CANDIDATES["statement"] if c in motion), key=motion.get)
    board = {"meta": {"renderer": "remotion", "title": "t"},
             "slides": [{"index": 0, "shot": stillest, "energy": "peak", "narration": "one", "shot_props": {}}]}
    r = validate.evaluate(board, str(tmp_path), pre_tts=True)
    hits = [w for w in r["warnings"] if "energy skeleton" in w]
    assert hits and "beat 1" in hits[0] and "under the delivery motion floor" in hits[0], r["warnings"]


def test_the_deterministic_director_follows_the_skeleton():
    """The path that shipped the defect: a plan with a high beat, a peak and a close, assigned mechanically."""
    motion, floor, qc, kc = _sweep()
    energies = ["medium", "high", "medium", "peak", "medium", "low"]
    board = {"meta": {}, "slides": [{"index": i} for i in range(6)]}
    plan = {"beats": [{"id": i + 1, "visual_intent": "statement", "energy": e} for i, e in enumerate(energies)]}
    plan["beats"][-1]["relation"] = "close"
    sd.assign_shots(board, plan)
    shots = [s["shot"] for s in board["slides"]]
    fs = es.findings(board["slides"], motion, floor, qc, kc, plan)
    assert not [f for f in fs if f["kind"] in es.HARD], [es.describe(f) for f in fs]
    assert motion[shots[3]] == max(motion[x] for x in shots), "the peak beat is the film's summit: %r" % shots
    fams = [sd.FAMILY.get(x) for x in shots]
    assert all(a != b for a, b in zip(fams, fams[1:])), "family variety still holds"
    assert len(set(shots)) == 6, "freshness still holds"


# ── COVERAGE: the sweep is a second universe, and being blind in it must not read as a pass ───────────
#
# A beat whose register has no row — or whose row `stale()` drops — used to leave `findings()` on a bare
# `continue`. It appeared in the sparkline as `?` and nowhere else, so with no other finding the CLI
# printed "the registers follow the plan's skeleton" over beats nobody had looked at, and exited 0.

def _board(tmp_path, shots, name="film"):
    d = tmp_path / name
    d.mkdir(parents=True)
    json.dump({"meta": {"renderer": "remotion"},
               "slides": [{"index": i, "shot": s} for i, s in enumerate(shots)]},
              open(d / "storyboard.json", "w", encoding="utf-8"))
    return str(d)


def _stale_manifest(monkeypatch, tmp_path, names):
    """The real manifest with `names` deliberately out of date — the state after a shot is edited."""
    import register_energy as reg
    data = json.load(open(reg.MANIFEST, encoding="utf-8"))
    for n in names:
        data["_source"][n] = "0" * 16
    p = tmp_path / "register_energy.json"
    json.dump(data, open(p, "w", encoding="utf-8"))
    monkeypatch.setattr(reg, "MANIFEST", str(p))


@pytest.mark.parametrize("n", [1, 3, 8])
def test_the_coverage_line_derives_its_universe_from_the_board(tmp_path, capsys, n):
    """M is parsed from `slides`. A restated or survivor-derived M would keep printing full coverage."""
    motion, _f, _q, _k = _sweep()
    calm = min(motion, key=motion.get)
    es.main([_board(tmp_path, [calm] * n, name="f%d" % n)])
    assert "measured %d of %d" % (n, n) in capsys.readouterr().out


def test_a_beat_with_no_row_is_a_named_finding_not_a_pass(tmp_path, capsys):
    motion, _f, _q, _k = _sweep()
    calm = min((m for m in motion if motion[m] < _sweep()[3]), key=motion.get)
    out = _board(tmp_path, [calm, "NoSuchRegister", None])
    rc = es.main([out])
    text = capsys.readouterr().out
    assert "measured 1 of 3" in text, text
    assert "follow the plan's skeleton" not in text, "a pass sentence was printed over unmeasured beats"
    assert "NoSuchRegister" in text and "register_energy.py" in text, text
    assert "no register assigned" in text, text
    assert rc == 1, "beats that could not be checked must not exit 0"


def test_a_stale_row_is_told_apart_from_a_missing_one(tmp_path, capsys, monkeypatch):
    """Both leave the beat unmeasured and the FIXES differ — one is the shot-director, the other is a
    re-run of the sweep. Reporting both as 'not measured' sends the reader to the wrong one."""
    motion, _f, _q, _k = _sweep()
    victim = sorted(motion)[0]
    _stale_manifest(monkeypatch, tmp_path, [victim])
    es.main([_board(tmp_path, [victim], name="stale")])
    text = capsys.readouterr().out
    assert "measured 0 of 1" in text, text
    assert "STALE" in text and "register_energy.py" in text, text
    assert "has no row in the sweep" not in text, "a stale row was reported as a missing one"


def test_the_json_report_carries_the_coverage_too(tmp_path, capsys):
    motion, _f, _q, _k = _sweep()
    calm = min(motion, key=motion.get)
    es.main([_board(tmp_path, [calm, "NoSuchRegister"], name="js"), "--json"])
    r = json.loads(capsys.readouterr().out)
    assert r["coverage"]["measured"] == 1 and r["coverage"]["universe"] == 2
    assert r["coverage"]["not_measured"][0]["beat"] == 2


def test_the_mutation_that_hides_an_unmeasured_beat_is_caught(tmp_path, capsys):
    """THE MUTATION. Restore the bare `continue` in `findings()`: the sparkline still prints `?` and the
    findings no longer mention the beat, so coverage would read 2 of 2. The curve/findings cross-check
    has to refuse rather than let the two disagree."""
    import types
    src = open(es.__file__, encoding="utf-8").read()
    old = ('            out.append(dict(r, kind="unmeasured", alternatives=[],\n'
           '                            why=malformed.get(i) or unmeasured_reason(r["shot"], stale_rows, film_shots)))\n'
           '            continue')
    assert old in src, "the mutation target has drifted out of the source"
    mod = types.ModuleType("energy_skeleton_mutant")
    mod.__file__ = es.__file__
    exec(compile(src.replace(old, "            continue", 1), es.__file__, "exec"), mod.__dict__)
    with pytest.raises(RuntimeError, match="dropping a beat without recording it"):
        mod.main([_board(tmp_path, [min(_sweep()[0], key=_sweep()[0].get), "NoSuchRegister"], name="mut")])


def test_a_film_s_own_workshop_shot_is_unmeasured_with_advice_that_can_help(tmp_path, capsys):
    """A beat on a shot the film built has no row in the sweep BY DESIGN — register_energy.py is a library
    sweep and never sees a workshop. The CLI told the author to run it anyway, on an espresso film's
    ExtractionFlow beat; validate already said "unmeasured BY DESIGN". The beat stays unmeasured (exit 1,
    named in the coverage), but its line now points at what can measure it: the render."""
    motion = _sweep()[0]
    calm = min(motion, key=motion.get)
    out = _board(tmp_path, [calm, "FilmBuiltFlow"], name="ws")
    shots = os.path.join(out, "workshop", "shots")
    os.makedirs(shots)
    open(os.path.join(shots, "FilmBuiltFlow.tsx"), "w", encoding="utf-8").write("export const DURATION = 150;\n")
    rc = es.main([out, "--no-render"])
    text = capsys.readouterr().out
    assert rc == 1, text                                            # still not measured — never a silent pass
    assert "FilmBuiltFlow is this film's own workshop shot" in text, text
    # the advice is the command that CAN measure it now — this one, rendering the film's own shots
    assert "energy_skeleton.py <out_dir>" in text and "register_energy.py" not in text, text
    # the same name as a LIBRARY register that lacks a row keeps the old advice
    rc2 = es.main([_board(tmp_path, [calm, "FilmBuiltFlow"], name="lib")])
    assert rc2 == 1 and "register_energy.py" in capsys.readouterr().out


def test_the_light_cut_is_the_librarys_own_and_not_a_whole_films_threshold():
    """A per-register light reading was judged against a number that describes a whole FILM.

    `film_energy_qa.LUMA_RANGE_FLOOR` is 0.135 — half the lowest reference launch film — and a film's
    luminance range is mostly the CUT: it comes from moving between a dark beat and a light one. A single
    register paints on ONE ground by construction, so it cannot produce a film's range and was never the
    thing that number described.

    Measured before this changed: of 180 registers, 147 cleared ink, 63 cleared motion, and 12 cleared
    light — and the twelve that cleared light were EXACTLY the twelve that cleared all three. "Clears all
    three" was the light axis wearing three hats, and the twelve were the registers whose own composition
    happens to span dark to light, not the ones with an arc. That is the same category error the ink floor
    was retired for, one axis over, and the fix is the same: the library's own distribution.

    The gate keeps its constant — there it judges films, and there it is right.
    """
    import register_energy as re_
    man = json.load(open(os.path.join(_HERE, "..", "remotion", "register_energy.json"), encoding="utf-8"))
    rows = man["registers"]

    assert re_.floors()["luma_range"] is None, (
        "floors() is taking a light constant again; a whole-film threshold cannot judge one shot")
    cut = re_._light_cut(rows)
    assert cut is not None and cut < re_.fe.LUMA_RANGE_FLOOR, (
        "the library's own light cut (%r) is not below the FILM floor (%r) — either the library changed "
        "shape or the cut is being taken from the gate again" % (cut, re_.fe.LUMA_RANGE_FLOOR))

    def clears(key, floor):
        return {n for n, r in rows.items() if (r.get(key) or 0) >= floor}

    fl = {"motion_p75": re_.fe.MOTION_P75_FLOOR, "ink_median": re_._ink_cut(rows), "luma_range": cut}
    ink, mot, lum = (clears("ink_median", fl["ink_median"]), clears("motion_p75", fl["motion_p75"]),
                     clears("luma_range", fl["luma_range"]))
    all3 = ink & mot & lum
    # THE POINT: the three axes must say three different things. Under the film floor they did not —
    # `lum` WAS `all3`, so two of the columns carried no information of their own.
    assert lum != all3, (
        "the light axis still decides the whole test on its own: %d clear light, %d clear all three"
        % (len(lum), len(all3)))
    assert len(all3) > len(man.get("_failed") or []), "nothing clears all three; the cut cannot be right"


def test_a_measured_built_shot_under_the_floor_is_named_with_its_own_fix(tmp_path):
    """The compound-interest test built 11 of 11 beats and measured 0 of them here; 8 were under the motion floor.
    A built beat's motion comes from the cache own_motion() writes; under the floor it is named, with the fix that
    lives in its own source (no library alternative exists for it)."""
    motion, floor = _sweep()[0], _sweep()[1]
    calm = min(motion, key=motion.get)
    out = _board(tmp_path, [calm, "FilmBuiltFlow"], name="cached")
    shots = os.path.join(out, "workshop", "shots")
    os.makedirs(shots)
    open(os.path.join(shots, "FilmBuiltFlow.tsx"), "w", encoding="utf-8").write("export const DURATION = 150;\n")
    board = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    key = es._own_key(out, board["slides"][1], board["meta"])
    json.dump({key: round(floor / 4, 5)}, open(os.path.join(out, es.OWN_CACHE), "w"))
    fs, _cv, why = es.check(out)
    assert not why, why
    own = [f for f in fs if f["kind"] == "own-under-floor"]
    assert own and own[0]["beat"] == 2, fs
    assert "keeps the subject alive" in es.describe(own[0])
    assert not [f for f in fs if f["kind"] == "unmeasured" and f["beat"] == 2], fs
    # the cache is keyed on the workshop's bytes: an edit to the shot drops the old number
    open(os.path.join(shots, "FilmBuiltFlow.tsx"), "a", encoding="utf-8").write("// edited\n")
    fs, _cv, _w = es.check(out)
    assert [f for f in fs if f["kind"] == "unmeasured" and f["beat"] == 2], fs


@pytest.mark.skipif(not os.path.isdir(os.path.join(_HERE, "..", "remotion", "node_modules")),
                    reason="needs the remotion toolchain")
def test_the_films_own_shots_are_rendered_measured_and_cached(tmp_path, monkeypatch):
    """A static built shot (a solid frame) is rendered with its props, measured by the delivery gate's instrument,
    and cached; the second run reads the cache and renders nothing."""
    sys.path.insert(0, _HERE)
    from test_workshop_bundle import SHOT
    out = _board(tmp_path, ["StillPage"], name="own")
    shots = os.path.join(out, "workshop", "shots")
    os.makedirs(shots)
    open(os.path.join(shots, "StillPage.tsx"), "w", encoding="utf-8").write(SHOT % {"name": "StillPage"})
    board = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    rel = os.path.relpath(out)                          # a relative out_dir, as a user types it — the render runs
    got = es.own_motion(rel, board["slides"], board["meta"], render=True)   # from remotion/, not from here
    assert set(got) == {1} and got[1] < 0.001, got
    assert os.path.exists(os.path.join(out, es.OWN_CACHE))
    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("rendered again")))
    assert es.own_motion(out, board["slides"], board["meta"], render=True) == got


def test_a_built_peak_beat_is_never_told_to_become_a_template(tmp_path):
    """A built shot on a PEAK beat under the floor got `peak-under-floor` (HARD) and three library registers to swap
    in — design-first's opposite. A built shot's mismatch is advisory and about the shot itself."""
    motion, floor, qc, kc = _sweep()
    slides = [{"shot": "FilmHero", "energy": "peak"}, {"shot": "FilmCalm", "energy": "high"},
              {"shot": "FilmBusy", "energy": "low"}]
    fs = es.findings(slides, motion, floor, qc, kc, film_shots={"FilmHero", "FilmCalm", "FilmBusy"},
                     beat_motion={1: floor / 3, 2: (floor + qc) / 2 if qc > floor else floor * 1.01, 3: kc * 2})
    kinds = {}
    for f in fs:
        kinds.setdefault(f.get("beat"), set()).add(f["kind"])
    assert "own-under-floor" in kinds[1] and "own-off-energy" in kinds[3], fs
    assert not [f for f in fs if f["kind"] in es.HARD or f.get("alternatives")], fs
    assert "liveliest" in es.describe([f for f in fs if f["beat"] == 3][0])


def test_the_own_shot_cache_key_sees_assets_and_library_code_but_not_generated_stills(tmp_path, monkeypatch):
    import beat_key as bk
    out = tmp_path / "film"
    (out / "workshop" / "shots").mkdir(parents=True)
    (out / "workshop" / "shots" / "A.tsx").write_text("export const DURATION = 30;\n")
    (out / "workshop" / "shots" / "B.tsx").write_text("export const DURATION = 30;\n")
    (out / "workshop" / "assets").mkdir()
    (out / "workshop" / "assets" / "foil.png").write_bytes(b"\x00")
    slide, meta = {"shot": "A", "shot_props": {}}, {}
    monkeypatch.setattr(bk, "shared_hash", lambda: "L1")
    k = es._own_key(str(out), slide, meta)
    (out / "workshop" / "_stills").mkdir()
    (out / "workshop" / "_stills" / "A.png").write_bytes(b"\x01")
    assert es._own_key(str(out), slide, meta) == k, "a preview still is an output, not an input"
    (out / "workshop" / "shots" / "B.tsx").write_text("export const DURATION = 31;\n")
    assert es._own_key(str(out), slide, meta) == k, "another shot's edit does not re-measure this one"
    (out / "workshop" / "assets" / "foil.png").write_bytes(b"\x02")
    k2 = es._own_key(str(out), slide, meta)
    assert k2 != k, "an asset the shot draws changes its motion"
    monkeypatch.setattr(bk, "shared_hash", lambda: "L2")
    assert es._own_key(str(out), slide, meta) != k2, "library code a built shot imports changes it too"
