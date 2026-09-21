"""A driver written against `t` must complete the cycle it was authored to repeat — and the tool that finds
them must not invent findings.

`useT()` returns 0→1 across the WHOLE clip, so `Math.sin(t * 2)` is two radians in five seconds: a third of
one cycle. The constant reads like radians per second and is nothing of the kind. Thirteen were found by
grepping `Math.sin(t *`, and that grep MISSED a second class with no trig in it at all — a conveyor's
`(t * 0.85) % 1`, a helix's `spin = t * 2.4` — which took a different grep to see. A defect class that needs
the right grep will be missed by whoever adds register 153, so it is a script.

Most of these tests are about the tool being WRONG in the two ways it was actually wrong:

  reading past the modulus  `(t * 0.6) % (1 / 16)` is 9.6 cycles, not 0.6. The first pass reported it.
  calling a ramp a cycle    `clamp01(t * 4)` on a title's opacity is a fade-in that saturates and stops.
                            Twenty-six of the library's ninety drivers are this, and none is a finding.

And one about the finding's SHAPE: "under one cycle" alone over-reported immediately (0.61 of a hue rotation
is 220 degrees of visible colour), so a finding is the intersection with a MEASURED motion score.
"""
import os

import clock_qa as ck


def _rows(src):
    return ck.scan_source(src, "Probe")


def test_a_stalled_trig_driver_is_found():
    rows = _rows("const wob = 0.8 + 0.25 * Math.sin(t * 2 + i);")
    assert rows and rows[0]["kind"] == "trig"
    assert abs(rows[0]["cycles"] - 2 / 6.283) < 0.02, rows


def test_the_modulus_is_read_and_not_skipped():
    """NeonGrid's real line. Reported as 0.6 cycles it would send an author to fix a driver running 9.6."""
    rows = _rows("const scroll = (t * 0.6) % (1 / 16);")
    assert rows and rows[0]["kind"] == "modulo"
    assert rows[0]["cycles"] > 9, "the divisor in the modulus was ignored: %r" % (rows,)


def test_a_saturating_ramp_is_never_a_finding():
    """A quarter of the library's drivers are `clamp01(t * k)` title fades. Calling those cycles would bury
    every real finding under twenty-six false ones."""
    rows = _rows("opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>")
    assert rows and rows[0]["kind"] == "ramp" and rows[0]["cycles"] is None
    stalled, _ = ck.findings(rows)
    assert not stalled


def test_a_healthy_oscillator_is_not_reported():
    stalled, _ = ck.findings(_rows("const spin = Math.sin(t * 26);"))
    assert not stalled


def test_comments_are_not_scanned():
    assert not _rows("// this used to be Math.sin(t * 2) before the fix")


def test_a_finding_requires_a_MEASURED_symptom_as_well():
    """"Under one cycle" alone over-reported the moment it ran: 0.61 of a hue rotation is 220 degrees of
    visible colour. A finding pairs a stalled driver with a register that measures under the motion floor."""
    rows = _rows("const flow = (t * 260) % 360;")
    assert ck.findings(rows)[0], "the candidate scan should still see it"
    assert not ck.confirmed(rows, {"Probe": 0.02}, 0.0037), "a register that MEASURES fine was reported"
    assert ck.confirmed(rows, {"Probe": 0.001}, 0.0037), "a register that measures frozen was not reported"


def test_it_refuses_to_judge_against_a_stale_sweep():
    """A finding built on a stale measurement is worse than no finding — and this actually fired mid-session,
    after a register was edited and before it was re-measured."""
    import inspect
    src = inspect.getsource(ck.measured_motion)
    assert "reg.stale(data)" in src and "STALE" in src


def test_the_tool_carries_its_own_caveat():
    """Three of the four registers it confirmed were reverted after rendering them: a register can measure
    frozen because the moving thing is SMALL, which no clock correction fixes. A tool whose findings were
    taken as work orders would have kept all four."""
    doc = ck.__doc__ or ""
    assert "CANDIDATE, NOT A WORK ORDER" in doc
    assert "reverted" in doc and "SpectrumPulse" in doc
    assert "NOT THE LEVER" in doc, "the tool does not say what it cannot do"


def test_it_still_sees_the_library():
    """A scanner that silently matches nothing is the failure mode this repo keeps finding."""
    rows = ck.scan_library()
    assert len(rows) > 60, "the library scan collapsed: %d rows" % len(rows)
    kinds = {r["kind"] for r in rows}
    assert {"trig", "modulo", "ramp", "linear"} <= kinds, kinds


# ---------------------------------------------------------------------------------------------------
# COVERAGE. The headline used to be "83 drivers against `t`" — a count of what the scan FOUND, with no
# denominator anywhere, so a run that read 40 files and one that read 170 printed the same shape of line.
# Three things can leave this gate's measurement: a register file it cannot read, a narrowing step whose
# manifest is unusable, and a stalled register the manifest has no score for. Each must be counted and
# named, and none may exit 0.

def _shots_dir(tmp_path, n, bad=False):
    """A synthetic library. The count the tests assert against is the one on DISK, so a coverage line
    printed from a constant cannot satisfy them."""
    d = tmp_path / "shots"
    d.mkdir()
    for i in range(n):
        (d / ("Reg%02d.tsx" % i)).write_text(
            "export const DURATION = 150;\nconst flow = (t * 260) %% 360;\n" % (), encoding="utf-8")
    if bad:
        (d / "BadBytes.tsx").write_bytes(b"const s = Math.sin(t * 2);\n\xff\xfe not utf-8")
    return str(d)


def test_the_headline_counts_the_universe_it_read_not_what_it_found(tmp_path, capsys, monkeypatch):
    """`measured N of M` where M is DERIVED from the shots directory. Asserted against the real file
    count, so a hardcoded denominator fails."""
    import glob as _g
    d = _shots_dir(tmp_path, 7)
    on_disk = len(_g.glob(os.path.join(d, "*.tsx")))
    monkeypatch.setattr(ck, "SHOTS", d)
    ck.main([])
    line = capsys.readouterr().out.splitlines()[0]
    assert "read %d of %d register file(s)" % (on_disk, on_disk) in line, line
    assert "%d hold a driver" % on_disk in line, line


def test_a_register_file_it_cannot_read_is_named_and_never_reads_as_driver_free(tmp_path, capsys,
                                                                                monkeypatch):
    """The clean-looking answer for an unreadable file is 'no drivers here'. It must be 'not scanned',
    with the error's own message, and the denominator must still count it."""
    d = _shots_dir(tmp_path, 4, bad=True)
    monkeypatch.setattr(ck, "SHOTS", d)
    rc = ck.main([])
    out = capsys.readouterr().out
    assert "read 4 of 5 register file(s)" in out, out.splitlines()[0]
    assert "NOT SCANNED" in out and "BadBytes" in out, out
    assert "utf-8" in out, "the reason names nothing a reader can act on: %s" % out
    assert rc != 0, "a run that could not read part of its universe exited clean"


def test_a_run_whose_narrowing_never_happened_does_not_exit_clean(monkeypatch, capsys):
    """This is the swallowed exception. `measured_motion` returns (None, None, why) for any failure —
    unreadable manifest, stale sweep, missing floors — and the run then confirms nothing at all. It
    printed NOT NARROWED and exited 0, which is what a caller reads as a pass."""
    monkeypatch.setattr(ck, "measured_motion", lambda: (None, None, "no usable sweep (test)"))
    rc = ck.main([])
    out = capsys.readouterr().out
    assert "NOT NARROWED BY MEASUREMENT" in out
    assert "of %d stalled driver(s) were confirmed or cleared" % len(ck.findings(ck.scan_library())[0]) in out
    assert rc == 2, "could not measure exited %r — indistinguishable from clean" % rc


def test_a_stalled_register_with_no_motion_score_is_named_not_dropped():
    """`motion.get(name)` returning None used to `continue`. Guarded today by register_energy.stale(),
    which is why this is asserted on the function rather than on a live run."""
    rows = ck.scan_source("const flow = (t * 260) % 360;", "Probe")
    hits, unnarrowed = ck.confirmed_covered(rows, {"Somebody": 0.001}, 0.0037)
    assert hits == []
    assert unnarrowed and unnarrowed[0][0] == "Probe", unnarrowed
    assert "neither confirmed nor cleared" in unnarrowed[0][1]


def test_the_json_report_carries_the_same_coverage(tmp_path, capsys, monkeypatch):
    import json as _j
    d = _shots_dir(tmp_path, 3, bad=True)
    monkeypatch.setattr(ck, "SHOTS", d)
    rc = ck.main(["--json"])
    got = _j.loads(capsys.readouterr().out)
    assert got["coverage"]["register_files"] == 4 and got["coverage"]["read"] == 3, got["coverage"]
    assert got["coverage"]["unreadable"][0][0] == "BadBytes"
    assert rc != 0
