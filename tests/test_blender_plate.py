"""scripts/blender_plate.py — a beat's Blender plate: where Blender is, the board contract, the keyed build.

A Blender plate is a 3D render a workshop shot draws under its own overlay (docs/superpowers/specs/
2026-11-04-blender-plates-design.md). These tests pin the host side; tests/test_blender_runner.py runs Blender."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import blender_plate as bp  # noqa: E402


def test_blender_bin_order(tmp_path, monkeypatch):
    fake = tmp_path / "Blender"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("TTV_BLENDER", str(fake))
    assert bp.blender_bin({"blender": str(fake)}) == str(fake)
    assert bp.blender_bin({}) == str(fake)
    monkeypatch.setenv("TTV_BLENDER", str(tmp_path / "missing"))
    monkeypatch.setattr(bp, "_APP_PATHS", ())
    monkeypatch.setattr(bp.shutil, "which", lambda n: None)
    assert bp.blender_bin({}) is None


@pytest.mark.parametrize("line,want", [("Blender 5.2.4 LTS Release Candidate", (5, 2, 4, True)),
                                       ("Blender 5.0.1", (5, 0, 1, False))])
def test_version_parse(line, want, monkeypatch):
    monkeypatch.setattr(bp, "_version_line", lambda b: line)
    assert bp.blender_version("x") == want


def test_version_without_a_version_line_is_refused(monkeypatch):
    monkeypatch.setattr(bp, "_version_line", lambda b: "")
    with pytest.raises(bp.PlateError, match="version"):
        bp.blender_version("x")


def test_version_floor_refused(monkeypatch, tmp_path):
    fake = tmp_path / "Blender"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setattr(bp, "_version_line", lambda b: "Blender 4.2.0")
    with pytest.raises(bp.PlateError, match="5.0"):
        bp.require_blender({"blender": str(fake)})


def test_missing_blender_refused(monkeypatch):
    monkeypatch.setattr(bp, "blender_bin", lambda meta=None: None)
    with pytest.raises(bp.PlateError, match="not found"):
        bp.require_blender({})


def test_doctor_lists_blender():
    import doctor
    assert any(row[0] == "blender" and row[1] is False for row in doctor.CHECKS)
