"""A finding that names the wrong beat sends its reader to the wrong frame.

`index` is written 1-BASED by every board this repo has produced — verified against five on disk. Three
scripts read it as 0-based and added one, so every message they printed named the beat AFTER the one it
meant: `validate` reported "beat 3 declares a `ground` on CompanionCard" while CompanionCard is beat 2, and
`density_advice` called TermSpace "beat 2" when it opens the film.

The repo already paid for this once. `contact_sheet.py` labelled the sheet a CRITIC reads by the same
arithmetic, and an independent reviewer caught it — the fix there was to number by POSITION, which needs no
convention to agree with. The same fix is now applied everywhere, and this test is what stops the third time.

It asserts the RULE, not the current call sites: any `index`-plus-one arithmetic anywhere in scripts/ fails
here, whoever writes it next.
"""
import glob
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


def test_no_script_numbers_a_beat_by_index_plus_one():
    bad = {}
    for f in sorted(glob.glob(os.path.join(_ROOT, "scripts", "*.py"))):
        src = open(f, encoding="utf-8").read()
        # Only a real READ of the index FIELD counts. The first version of this pattern matched its own
        # explanatory comments, a docstring, a string literal and `argv.index("--cols") + 1` — a check that
        # cries wolf on four files teaches people to delete it.
        code = "\n".join(l.split("#")[0] for l in src.splitlines())
        hits = re.findall(r'(?:\.get\(\s*["\']index["\']\s*(?:,[^)]*)?\)|\[["\']index["\']\])\s*\)?\s*\+\s*1',
                          code)
        if hits:
            bad[os.path.basename(f)] = hits[:3]
    assert not bad, (
        "these scripts number a beat from the `index` FIELD plus one; boards write `index` 1-based, so every "
        "finding they print names the following beat: %r" % (bad,))


def test_boards_on_disk_really_are_one_based():
    """The premise, checked rather than assumed — if a board ever wrote `index` 0-based, the fix above would
    be the bug instead."""
    found = 0
    for f in glob.glob("/private/tmp/claude-501/-Users-donghanglyu/*/*/storyboard.json"):
        try:
            slides = json.load(open(f, encoding="utf-8")).get("slides") or []
        except (OSError, ValueError):
            continue
        ix = [s.get("index") for s in slides if isinstance(s.get("index"), int)]
        if not ix:
            continue
        found += 1
        assert min(ix) == 1, "%s starts its `index` at %d, not 1" % (f, min(ix))
    if not found:
        import pytest
        pytest.skip("no boards on disk to check the premise against")


def test_the_numbers_a_report_prints_match_the_boards_own_order():
    """End to end, on a real board: the beat number `density_advice` prints must name the register that is
    actually at that position."""
    boards = sorted(glob.glob("/private/tmp/claude-501/-Users-donghanglyu/*/agenthalo/storyboard.json"))
    if not boards:
        import pytest
        pytest.skip("no film on disk")
    out_dir = os.path.dirname(boards[0])
    slides = json.load(open(boards[0], encoding="utf-8"))["slides"]
    r = subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "density_advice.py"), out_dir],
                       capture_output=True, text=True, timeout=600)
    rows = re.findall(r"^\s*beat\s+(\d+)\s+(\S+)", r.stdout, re.M)
    if not rows:
        import pytest
        pytest.skip("density_advice reported no starved beats: %s" % (r.stdout or r.stderr)[:200])
    for num, shot in rows:
        at = slides[int(num) - 1].get("shot")
        assert at == shot, ("density_advice calls %s 'beat %s', but beat %s of the board is %s"
                            % (shot, num, num, at))
