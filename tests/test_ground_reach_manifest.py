"""`GROUND_FOLLOWS_MEASURED` is a safety allow list, and for its whole life nothing checked its evidence.

`runtime/light.tsx` consults that set before it lets a beat re-ground: a register not on it is REFUSED.
Absence is therefore fail-safe and deliberate — "not yet looked at", never "checked and safe". The other
direction is not safe at all, and nothing was watching it:

  * Three names (`CarryOver`, `StatedBy`, `ViewSwitch`) sat ON the list with NO measurement row anywhere.
    They were permitted to re-ground on no evidence, which is the exact reading of an absence the module's
    own header warns against, arriving from the other side.
  * Every row in the manifest recorded WHAT it measured and nothing about WHERE it came from. So the only
    way to ask "does this record still describe the code?" was to re-render all 185 shots — hours — which
    is why nobody asked, and why a register could be rewritten into one whose content the declared ground
    destroys and keep its place on a safety list. Both sibling manifests have answered that in seconds
    since a stale row was found in one of them.

These two tests cost no renders, so there is no excuse not to run them.
"""
import glob
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import measure_ground_reach as gr          # noqa: E402

_MANIFEST = os.path.join(_ROOT, "remotion", "_ground_reach.json")


def _data():
    if not os.path.exists(_MANIFEST):
        pytest.skip("no ground-reach manifest committed")
    return json.load(open(_MANIFEST, encoding="utf-8"))


def test_every_name_on_the_allow_list_has_a_measurement_behind_it():
    """The safety direction. A name on this list is a register `light.tsx` will let a beat re-ground; if no
    row measured it, the permission rests on nothing."""
    data = _data()
    rows = {r["shot"] for r in (data.get("rows") or [])}
    listed = gr.read_set()
    unevidenced = sorted(listed - rows)
    assert not unevidenced, (
        "these names are on GROUND_FOLLOWS_MEASURED with no row in _ground_reach.json, so a beat may "
        "re-ground them on no evidence: %s. Measure them: "
        "`python3 scripts/measure_ground_reach.py --only=%s --emit`"
        % (unevidenced, ",".join(unevidenced)))


def test_no_row_still_claims_to_describe_a_register_that_has_since_changed():
    """The staleness direction, asked cheaply. A row whose recorded source hash no longer matches is a
    measurement of code that does not exist; it must not keep backing a safety permission.

    Rows written before the hash existed report "cannot be confirmed" rather than "changed" — that is
    honest and it is DEBT, recorded below, not something this test can resolve. What it does catch, from
    here on, is a register edited after being measured.
    """
    data = _data()
    changed = [(shot, why) for shot, why in gr.stale(data) if "changed" in why or "unreadable" in why]
    assert not changed, (
        "these rows no longer describe their register's source: %s. Re-measure them: "
        "`python3 scripts/measure_ground_reach.py --only=%s --emit`"
        % (changed, ",".join(s for s, _ in changed)))


def test_the_hash_is_recorded_for_every_row_this_repo_measures_from_now_on():
    """A RECORD, and a ratchet. Rows written before `_source` existed cannot be confirmed without a full
    re-render of the library; this pins how many are in that state so the number can only go down, and so
    that a sweep which quietly dropped the hash again would be caught."""
    data = _data()
    rows = [r["shot"] for r in (data.get("rows") or [])]
    hashed = set(data.get("_source") or {})
    unconfirmable = sorted(set(rows) - hashed)
    assert len(unconfirmable) <= 170, (
        "%d row(s) carry no recorded source, up from the 170 inherited when the hash was added — a sweep "
        "has written rows without it: %s" % (len(unconfirmable), unconfirmable[:10]))


def test_the_manifest_covers_the_library_or_says_which_registers_it_does_not():
    """Coverage read as a number, the way this repo has learned to read every gate's own count."""
    data = _data()
    rows = {r["shot"] for r in (data.get("rows") or [])}
    shots = {os.path.basename(f)[:-4]
             for f in glob.glob(os.path.join(_ROOT, "remotion", "src", "shots", "*.tsx"))}
    missing = sorted(shots - rows)
    assert not missing, (
        "%d register(s) have no ground-reach row, so nothing is known about whether a declared ground "
        "reaches them: %s. They are refused by default, which is safe — but the gate's coverage is %d of "
        "%d, and a coverage hole read as a pass is the failure this repo keeps finding."
        % (len(missing), missing, len(rows & shots), len(shots)))


# ── the same question, asked of the OTHER measurement cache ────────────────────────────────────────────

def test_the_shot_luma_cache_can_say_which_of_its_entries_are_stale():
    """`_ground_luma.json` was the last measurement record in the repo with no input hash.

    It is lower stakes than the reach manifest — the table the runtime reads (`SHOT_LUMA` in shotLuma.ts)
    is complete and separately tested, and this file is the cache behind it — but the question is the same
    one, and until now the only way to ask it was `--check`, which re-renders the library. This pins that
    `stale()` exists and answers on BOTH sides, so the next full sweep leaves a record that can be
    confirmed in a second instead of an hour.
    """
    import measure_ground_luma as gl

    unhashed = {"table": {"Foo": "dark"}}
    assert [w for _, w in gl.stale(unhashed) if "before the SOURCE was hashed" in w], (
        "an entry with no recorded source reads as confirmed — silence must not mean agreement")

    fresh = {"table": {"TermTree": "dark"}, "_source": {"TermTree": gl._source_hashes(["TermTree"])["TermTree"]}}
    assert not gl.stale(fresh), "an entry whose source is unchanged is reported stale: %r" % (gl.stale(fresh),)

    moved = {"table": {"TermTree": "dark"}, "_source": {"TermTree": "0000000000000000"}}
    assert [w for _, w in gl.stale(moved) if "changed" in w], (
        "an entry measured from a source that has since moved is not reported")


def test_the_reach_hash_does_not_include_the_conclusion_it_is_evidence_for():
    """A record must not invalidate itself the moment it is applied.

    `register_energy.source_hash` folds a register's own membership of `GROUND_FOLLOWS_MEASURED` into its
    hash, and that is RIGHT for every reader of that table — `light.tsx` imports it, so a register's
    rendering can depend on whether it is permitted to re-ground. It is wrong for exactly one caller: the
    sweep whose rows are the evidence the membership is derived from. Applying a fresh 185-row sweep
    rewrote the membership bit and seven rows the sweep had just written reported themselves stale, on a
    library whose pixels had not moved. A check that cries wolf is a check that gets ignored, and this repo
    has already recorded that lesson twice.

    The exclusion is only sound because the probe does not consult the list, and that is not an assumption:
    nine registers that were NOT listed measured as following, which they could not have done if the
    permission gated the measurement.
    """
    import tempfile
    import register_energy as re_mod

    LISTED = ("export const GROUND_FOLLOWS_MEASURED = new Set([\n  'Foo', 'Probe', 'Bar',\n]);\n"
              "export const SHOT_LUMA: Record<string, string> = {\n  Probe: 'dark',\n};\n")
    NOT_LISTED = ("export const GROUND_FOLLOWS_MEASURED = new Set([\n  'Foo', 'Bar',\n]);\n"
                  "export const SHOT_LUMA: Record<string, string> = {\n  Probe: 'dark',\n};\n")

    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "shotLuma.ts")
        open(a, "w", encoding="utf-8").write(LISTED)
        listed_on = re_mod._dep_bytes(a, "Probe", ignore_follows=False)
        listed_off = re_mod._dep_bytes(a, "Probe", ignore_follows=True)
        open(a, "w", encoding="utf-8").write(NOT_LISTED)
        unlisted_on = re_mod._dep_bytes(a, "Probe", ignore_follows=False)
        unlisted_off = re_mod._dep_bytes(a, "Probe", ignore_follows=True)

    assert listed_on != unlisted_on, (
        "membership no longer reaches the ordinary hash — register_energy and prop_reach would stop "
        "noticing that a register's permission to re-ground changed under them")
    assert listed_off == unlisted_off, (
        "ignore_follows still lets membership move the hash, so applying a ground-reach sweep marks the "
        "rows it just wrote as stale and the check starts crying wolf")
