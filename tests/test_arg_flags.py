"""An unparsed argument must never be a silent change of scope.

WHAT THIS COST, measured rather than imagined. Nine scripts here parsed their own flags with
`next((a.split("=", 1)[1] for a in argv if a.startswith("--only=")), None)`, and not one refused an argument
it did not understand. So `--only DollyZoom` — the spelling this repo's own docstrings use for
`cjk_type_qa`, and the one a person types — matched nothing in `register_energy`, fell through to `None`,
and ran a FULL 164-register sweep instead of the one register that was asked for. Twice in one session,
about forty-five minutes of renders each time, and nothing in the output said the filter had been dropped:
the progress counter read "measured 10/164" and that was the only clue.

`measure_ground_luma` had the same bug in a worse form — it matched `--only` with `startswith` and then set
the filter to `None` when the arg carried no `=`, so the flag did not narrow the sweep, it THREW IT AWAY.

Three scripts, three behaviours for one typed flag: `register_energy` swept everything in silence,
`cjk_type_qa` (argparse) accepted it, `text_safe_qa` crashed trying to open `--only/storyboard.json`. Only
the crash was honest, and only by accident.

THE TEST IS ON THE FAMILY, NOT ON ONE SCRIPT. A per-script test would have been written for
`register_energy` after the first hour and said nothing about the other eight.
"""
import importlib.util
import os
import subprocess
import sys

import pytest

import _common as c

_SCRIPTS = os.path.dirname(os.path.abspath(c.__file__))

# Every script that reads a flag by hand and sweeps or renders something, with the flag that narrows it.
# A script added to this list without the guard fails here rather than in someone's afternoon.
GUARDED = [
    ("register_energy.py", "--onlyy=Zed"),
    ("measure_ground_luma.py", "--onlyy=Zed"),
    ("text_safe_qa.py", "--library --onlyy=Zed"),
    ("measure_ground_reach.py", "--onlyy=Zed"),
    ("band_debt.py", "--check --stillss=/tmp/x"),
    ("sfx.py", "--calibrate --fpss=60"),
]


def test_both_spellings_of_a_flag_read_the_same():
    """`--only=A,B` and `--only A,B` are the same request. Supporting only the first is what made the second
    a silent full sweep."""
    assert c.argflag(["--only=Zed"], "only") == "Zed"
    assert c.argflag(["--only", "Zed"], "only") == "Zed"
    assert c.argflag_list(["--only", "A,B"], "only") == ["A", "B"]
    assert c.argflag_list(["--only=A,B"], "only") == ["A", "B"]
    # a switch standing between the flag and its value must not swallow it
    assert c.argflag(["--luma", "--only", "Zed", "--emit"], "only") == "Zed"
    # ...and a flag whose value is missing is not the next FLAG
    assert c.argflag(["--only", "--emit"], "only") is None


def test_a_flag_that_is_absent_still_returns_the_default():
    assert c.argflag([], "only", "D") == "D"
    assert c.argflag_list([], "only") is None
    assert c.argflag_list(["--only="], "only", "D") == "D", "an empty value is not a filter"


def test_an_unknown_argument_is_refused_rather_than_ignored():
    c.refuse_unknown(["--only", "Zed", "--dna=product", "--luma"],
                     valued=("only", "dna"), switches=("luma",))          # must not raise
    with pytest.raises(SystemExit) as e:
        c.refuse_unknown(["--onlyy=Zed"], valued=("only",))
    assert e.value.code == 2


def test_a_valued_flags_own_value_is_not_read_as_an_unknown_argument():
    """The guard walks the list; if it did not consume the value after `--only`, every targeted run would
    die claiming the register name was an unknown argument."""
    c.refuse_unknown(["--only", "Zed"], valued=("only",))
    c.refuse_unknown(["out_dir", "--library"], switches=("library",))      # a positional is not a flag


@pytest.mark.parametrize("script,args", GUARDED, ids=[s for s, _ in GUARDED])
def test_every_sweeping_script_refuses_a_misspelt_flag(script, args):
    """The whole point: a typo must cost a second, not an hour of renders."""
    r = subprocess.run([sys.executable, os.path.join(_SCRIPTS, script)] + args.split(),
                       capture_output=True, text=True, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 2, "%s accepted a misspelt flag (exit %s): %s" % (script, r.returncode, out[:400])
    assert "unknown argument" in out, "%s did not say WHICH argument: %s" % (script, out[:400])


def test_the_scripts_that_take_a_register_LIST_refuse_a_name_that_does_not_exist():
    """A filter that matches nothing is not a full sweep, and it is not an empty manifest either. Both
    happened: `--only=<typo>` left `names` empty and wrote a manifest with no rows."""
    for script, flag in (("register_energy.py", "--only=NoSuchRegister"),
                         ("text_safe_qa.py", "--library --only=NoSuchRegister")):
        r = subprocess.run([sys.executable, os.path.join(_SCRIPTS, script)] + flag.split(),
                           capture_output=True, text=True, timeout=300)
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode == 2, "%s ran anyway (exit %s): %s" % (script, r.returncode, out[:300])
        assert "do not exist" in out, out[:300]


def test_the_helpers_are_used_rather_than_re_implemented():
    """The failure this whole file is about is nine private copies of one parser. A tenth would bring the
    bug back in a file nobody thinks to check."""
    import glob
    offenders = []
    for path in glob.glob(os.path.join(_SCRIPTS, "*.py")):
        if os.path.basename(path) in ("_common.py",):
            continue
        src = open(path, encoding="utf-8").read()
        if 'startswith("--' in src and "_common" not in src and "argparse" not in src:
            offenders.append(os.path.basename(path))
    assert not offenders, (
        "these parse flags by hand without the shared reader or argparse, so a mistyped flag is silently "
        "ignored there: %s" % ", ".join(sorted(offenders)))
