"""stale_measurements — every measured manifest's stale rows, and the command that re-measures them, in one run.

WHY. A register's measured rows are keyed by the hash of its source AND everything it imports, so an edit to one
runtime file (runtime/gesture.tsx gaining `fingerPx`) quietly staled five registers in four manifests. Each
manifest has its own no-render staleness check, but nobody ran four of them before committing: three times the
full suite found it after a push. This runs all four, names each stale register under its manifest and prints the
exact re-measure command — no renders, a few seconds.
"""
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import stale_measurements as sm  # noqa: E402


def _copy(tmp_path):
    out = {}
    for c in sm.CHECKS:
        dst = tmp_path / os.path.basename(c.manifest)
        shutil.copy(c.manifest, dst)
        out[c.label] = str(dst)
    return out


def test_the_committed_manifests_are_all_fresh():
    found = sm.find()
    assert [f.label for f in found] == [c.label for c in sm.CHECKS], "every manifest is read, in order"
    assert all(not f.stale for f in found), [(f.label, f.stale[:3]) for f in found if f.stale]


@pytest.mark.parametrize("label", [c.label for c in sm.CHECKS])
def test_a_stale_row_is_named_under_its_manifest_with_its_command(tmp_path, label, capsys):
    paths = _copy(tmp_path)
    data = json.load(open(paths[label], encoding="utf-8"))
    name = sorted(data["_source"])[0]
    data["_source"][name] = "0000000000000000"
    json.dump(data, open(paths[label], "w"), indent=1)
    assert sm.main([], paths=paths) == 1
    out = capsys.readouterr().out
    check = next(c for c in sm.CHECKS if c.label == label)
    assert name in out and check.command.format(names=name) in out
    for other in sm.CHECKS:                            # the edit touched one manifest only
        if other.label != label:
            assert "[%s] OK" % other.label in out


def test_a_missing_manifest_fails_loudly_rather_than_reading_as_fresh(tmp_path, capsys):
    paths = _copy(tmp_path)
    os.remove(paths["prop_reach"])
    assert sm.main([], paths=paths) == 1
    assert "[prop_reach] MISSING" in capsys.readouterr().out


def test_every_printed_command_names_a_real_script_and_its_only_flag():
    for c in sm.CHECKS:
        script = c.command.split()[1]
        assert os.path.isfile(os.path.join(_ROOT, script)), c.command
        assert "{names}" in c.command and "--only" in c.command, c.command
