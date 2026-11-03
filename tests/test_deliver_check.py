"""deliver_check — every delivery gate a film needs, run as one, recorded against the film it measured.

WHY. The skill has twenty-odd gates and no one command ran the blocking ones: on the topic-to-video promo (2026-11-03)
the gates were run from memory, film_energy_qa was missed, and a film that measured as a slideshow (motion p75 0.0027,
floor 0.0037) reached the user's Desktop — deliver.py copied it although the render had written NOT_DELIVERED.md.
Two tiers keep the cost down: the FAST tier reads out.mp4 (~30 s, run by deliver.py on every hand-off); the FULL tier
adds the three gates that render a census (~10 min), run once for the final cut. A result is keyed by the film's bytes
and its board, so an unchanged film is never re-checked.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import deliver_check as dc  # noqa: E402
import deliver  # noqa: E402


def _film(tmp_path, meta=None):
    out = tmp_path / "film"
    out.mkdir(parents=True)
    (out / "out.mp4").write_bytes(b"not really a film")
    (out / "storyboard.json").write_text(json.dumps({"meta": dict({"renderer": "remotion", "title": "Film"}, **(meta or {})),
                                                     "slides": []}))
    return str(out)


def _runner(results, calls):
    def run(gate, out_dir):
        calls.append(gate)
        return results.get(gate, (0, "[%s] OK" % gate))
    return run


def test_the_fast_tier_runs_the_gates_that_read_the_film_and_records_them(tmp_path):
    out, calls = _film(tmp_path), []
    rec = dc.check(out, run=_runner({}, calls))
    assert rec["ok"] and rec["tier"] == "fast"
    assert set(calls) == set(dc.gates_for({"renderer": "remotion"}, "fast"))
    assert "film_energy_qa" in calls and "seam_ledger" in calls and "jitter_qa" not in calls
    again = dc.check(out, run=_runner({}, calls))
    assert again["ok"] and len(calls) == len(set(calls)), "an unchanged film is not re-checked"
    open(os.path.join(out, "out.mp4"), "ab").write(b"x")
    dc.check(out, run=_runner({}, calls))
    assert len(calls) > len(set(calls)), "a changed film is"


def test_a_failing_gate_fails_the_check_unless_the_board_waives_it_by_name(tmp_path):
    out = _film(tmp_path)
    bad = {"film_energy_qa": (1, "[film_energy] FAIL  motion p75 0.0027")}
    rec = dc.check(out, run=_runner(bad, []))
    assert not rec["ok"] and [g["name"] for g in rec["gates"] if g["status"] == "fail"] == ["film_energy_qa"]
    out2 = _film(tmp_path / "w", meta={"delivery_waivers": {"film_energy_qa": "a deliberately still essay film"}})
    rec2 = dc.check(out2, run=_runner(bad, []))
    assert rec2["ok"] and [g["status"] for g in rec2["gates"] if g["name"] == "film_energy_qa"] == ["waived"]


def test_a_gate_that_could_not_measure_is_not_a_pass(tmp_path):
    rec = dc.check(_film(tmp_path), run=_runner({"flash_qa": (2, "[flash] NOT MEASURED")}, []))
    assert not rec["ok"] and [g["status"] for g in rec["gates"] if g["name"] == "flash_qa"] == ["not measured"]


def test_the_full_tier_adds_the_census_gates_and_the_html_tier_runs_only_its_own(tmp_path):
    full = dc.gates_for({"renderer": "remotion"}, "full")
    assert {"media_res_qa", "text_safe_qa", "jitter_qa"} <= set(full)
    html = dc.gates_for({"renderer": "local"}, "full")
    assert "seam_ledger" not in html and "jitter_qa" not in html and "check_av" in html


def test_deliver_refuses_a_film_whose_check_fails_and_says_why(tmp_path, monkeypatch, capsys):
    out = _film(tmp_path)
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(dc, "_run_gate", _runner({"check_av": (1, "[check_av] FAIL drift 0.6s")}, []))
    assert deliver.main([out, "--to", str(home / "Desktop")]) == 1
    assert "check_av" in capsys.readouterr().out and not os.listdir(home / "Desktop")
    assert deliver.main([out, "--to", str(home / "Desktop"), "--anyway"]) == 0
    assert [f for f in os.listdir(home / "Desktop") if f.endswith(".mp4")] == ["Film (unchecked).mp4"]
