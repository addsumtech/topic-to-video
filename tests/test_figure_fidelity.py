"""A figure on a settled frame is the film's string, byte for byte — `runtime/figure.ts`.

Eight registers printed a number by stripping the film's string to digits and re-formatting what was left
(`parseFloat(String(v).replace(/[^\\d.]/g, ''))`), which turned "−12" into 12, "3–5" into 35, "2019-2024"
into 20,192,024 and "N/A" into 0, and then rounded 4.2 to 4. These pin the helper every register now prints
through: the settled text is the input, and only a string that states exactly ONE number may count up to it.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(os.path.dirname(_HERE), "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")


def _probe(values, ps=(0.0, 0.5, 1.0)):
    tmp = tempfile.mkdtemp(prefix="figure_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        open(entry, "w", encoding="utf-8").write(
            "import {parseFigure, figureAt, figureValue} from %s;\n"
            "const vals: any[] = %s; const ps = %s;\n"
            "console.log(JSON.stringify(vals.map((v) => { const f = parseFigure(v);"
            " return {num: f.num, at: ps.map((p: number) => figureAt(f, p)), value: figureValue(v)}; })));\n"
            % (json.dumps(os.path.join(_REM, "src", "runtime", "figure")), json.dumps(values), json.dumps(list(ps))))
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return dict(zip(values, json.loads(r.stdout.strip().splitlines()[-1])))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@_NEEDS_NODE
def test_settled_frame_prints_the_films_string_exactly():
    """Every string the old strip-and-reformat line mangled, read back at p=1 as the film wrote it."""
    vals = ["−12", "-12", "3–5", "2019-2024", "N/A", "1.2M", "+18%", "~40", "1,5", "2024", "1234.5",
            "4.2", "99.6", "1,234.5", "$3.50", "0", " 42 ", "v2", "3 个", "2.5×"]
    got = _probe(vals)
    for v in vals:
        assert got[v]["at"][-1] == v.strip(), (v, got[v])


@_NEEDS_NODE
def test_only_one_number_counts_up():
    """A range, a span, a word or a version string has no number to count to: it is shown whole at every frame."""
    got = _probe(["3–5", "2019-2024", "N/A", "v2", "two", ""])
    for v, g in got.items():
        assert g["num"] is None and g["value"] is None, (v, g)
        assert len(set(g["at"])) == 1, ("a non-figure must not animate", v, g)


@_NEEDS_NODE
def test_count_up_keeps_the_films_form():
    """Sign, prefix, decimals, grouping and suffix survive every intermediate frame; the magnitude is what moves."""
    got = _probe(["−12", "+18%", "$3.50", "1,234.5", "2.5×", "3 个"], ps=(0.0, 0.5))
    assert got["−12"]["at"] == ["0", "−6"], got["−12"]          # the film's own minus sign, not a hyphen
    assert got["+18%"]["at"][1] == "+9%"
    assert got["$3.50"]["at"][1] == "$1.75"
    assert got["1,234.5"]["at"] == ["0.0", "617.3"], got["1,234.5"]
    assert got["2.5×"]["at"][1] == "1.3×"
    assert got["3 个"]["at"][1] == "2 个"
    assert got["−12"]["value"] == -12 and got["+18%"]["value"] == 18 and got["1,234.5"]["value"] == 1234.5
