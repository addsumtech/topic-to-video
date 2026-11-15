"""Gates that passed what they never measured — the audit of 2026-11-15, one test per failure it reproduced.

The owner had named the same three defects (type that trembles, a picture that goes back, type cut off) film after film.
The audit found that each protection reached one render path, and that several gates answered "clean" when they had
not looked: a gate with no node exited 0, a coverage of zero printed OK, an unreadable probe counted as full of ink,
a waiver passed a gate the final review never lets anyone waive. Each test below pins one of those shut.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import beat_key  # noqa: E402
import capability_reach  # noqa: E402
import caption_breaks_qa  # noqa: E402
import cjk_type_qa  # noqa: E402
import content_contract_qa as ccq  # noqa: E402
import critic_ledger  # noqa: E402
import deliver  # noqa: E402
import deliver_check as dc  # noqa: E402
import fidelity  # noqa: E402


def _film(tmp_path, meta=None, marker=False):
    out = tmp_path / "film"
    out.mkdir(parents=True)
    (out / "out.mp4").write_bytes(b"not really a film")
    (out / "storyboard.json").write_text(json.dumps({"meta": dict({"renderer": "remotion"}, **(meta or {})), "slides": []}))
    if marker:
        (out / "NOT_DELIVERED.md").write_text("# RENDERED, not DELIVERED\nthe review has not run\n")
    return str(out)


def _ok_runner(gate, out_dir):
    return 0, "[%s] OK" % gate


def test_a_film_whose_review_has_not_passed_is_not_handed_over(tmp_path, monkeypatch, capsys):
    out = _film(tmp_path, marker=True)
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(dc, "_run_gate", _ok_runner)
    assert deliver.main([out, "--to", str(home / "Desktop")]) == 1
    assert "NOT_DELIVERED.md" in capsys.readouterr().out
    assert deliver.main([out, "--to", str(home / "Desktop"), "--anyway"]) == 0
    assert any("unreviewed" in n for n in os.listdir(home / "Desktop")), "handed over anyway, and named so"


def test_a_user_waiver_never_passes_the_gates_no_one_may_waive(tmp_path):
    out = _film(tmp_path, meta={"delivery_waivers": {"check_av": "looks fine to me", "flash_qa": "a deliberate strobe"}})
    bad = {"check_av": (1, "[check_av] FAIL drift 0.6s"), "flash_qa": (1, "[flash] FAIL")}
    rec = dc.check(out, run=lambda g, o: bad.get(g, (0, "ok")))
    st = {g["name"]: g["status"] for g in rec["gates"]}
    assert st["check_av"] == "fail" and st["flash_qa"] == "waived" and not rec["ok"]


def test_the_review_and_the_fast_check_judge_the_same_film_gates():
    """seam_ledger and named_objects_qa ran in deliver_check's fast tier and in no list the review records"""
    full = {s[:-3] for _l, s, _a, _t, _b, _ap in critic_ledger.DELIVERY_GATES["remotion"]}
    assert set(dc.gates_for({"renderer": "remotion"}, "full")) <= full
    assert "caption_breaks_qa" in full


def test_caption_breaks_without_node_is_not_measured(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(caption_breaks_qa, "check", lambda out_dir: {"skipped": "node/npx unavailable", "beats": [],
                                                                     "errors": [], "warnings": []})
    assert caption_breaks_qa.main([str(tmp_path)]) == 2
    assert "UNMEASURED" in capsys.readouterr().out


def test_a_probe_that_cannot_be_read_is_not_full_of_ink(tmp_path):
    assert cjk_type_qa._ink_fraction(str(tmp_path / "missing.png")) is None


def test_capability_reach_reads_a_preset_named_by_a_string():
    _n, used, _w = capability_reach.narrated("/nonexistent", {"meta": {"design_dna": "editorial"},
                                                               "slides": [{"shot": "X"}]})
    assert used["material"] is False and used["optics"] is False


def test_an_apostrophe_in_jsx_copy_opens_no_string():
    src = ("export const META = {note: 'it\\'s kept'};\n"
           "export const Shot = () => <div data-part=\"wheel\">Don't stop, it's \"here</div>;\n"
           "const x = {'data-part': 'axle'};\n")
    assert fidelity.source_part_names(src) == ({"wheel", "axle"}, False)
    assert fidelity.meta_span(src) is not None
    assert fidelity.strip_comments("a // gone\n`multi\nline`") == "a  \n`multi\nline`"


def test_a_fidelity_sheet_goes_stale_when_its_record_changes(tmp_path, monkeypatch):
    d = tmp_path / fidelity.SHEET_DIR
    d.mkdir()
    rec = {"subject": "a watch", "depicts": "real"}
    (d / "Watch.json").write_text(json.dumps({"key": fidelity.sheet_key(rec, "src"), "problems": []}))
    monkeypatch.setattr(fidelity, "record_for", lambda o, n: (rec, o, "src", "w", "object"))
    assert fidelity.sheet_status(str(tmp_path), "Watch") == "ok"
    monkeypatch.setattr(fidelity, "record_for", lambda o, n: (dict(rec, parts=["crown"]), o, "src", "w", "object"))
    assert fidelity.sheet_status(str(tmp_path), "Watch") == "stale"


def test_a_picture_replaced_at_the_same_path_changes_the_beats_key(tmp_path):
    (tmp_path / "media").mkdir()
    pic = tmp_path / "media" / "a.png"
    pic.write_bytes(b"one")
    slide = {"shot": "", "shot_props": {"src": "media/a.png"}}
    tool = os.path.abspath(beat_key.__file__)
    k1 = beat_key.beat_key(str(tmp_path), slide, {}, tool)
    pic.write_bytes(b"two")
    assert beat_key.beat_key(str(tmp_path), slide, {}, tool) != k1


def test_the_films_own_list_cut_short_is_a_truncation_whatever_its_case():
    inside = ("export const S = ({layers: IN = []}) => {\n  const LAYERS = listOf(IN);\n"
              "  const rows = LAYERS.slice(0, n);\n};\n")
    assert [v[1] for v in ccq.violations(inside)] == ["truncate"]
    table = "const ROUTE = [[0, 0], [1, 1]];\nexport const S = ({steps}) => { const p = ROUTE.slice(0, n); };\n"
    assert ccq.violations(table) == [], "the register's own module-level table cut to the film's count is not"
    hexed = "const n = parseInt(hex.replace('#', '').slice(0, 6), 16);\n"
    assert ccq.violations(hexed) == []


def test_rewind_controls_separate():
    """the pixel rewind gate (scripts/rewind_qa.py): a ping-pong push, a reset and a replayed cut are caught; a steady
    push, a hold, a loop, a label that came and went and a cut inside one take are not"""
    import rewind_qa
    assert rewind_qa.calibrate() == 0
