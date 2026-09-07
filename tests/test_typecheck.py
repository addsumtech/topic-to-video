"""The registers are TypeScript, and until now nothing ever checked that.

Remotion bundles with esbuild, which strips types without looking at them. So a call with the wrong number of
arguments, a prop that does not exist, a misspelled field — all of them bundle, render, and produce a picture
that is quietly wrong. That is not hypothetical: `SurfaceCarousel` was written calling
`seg(t, a, b, easeInOutCubic)` against a three-parameter `seg`. The easing was dropped on the floor, every
beat of the carousel ran linear, and the shot still rendered a plausible frame. It cost a render and a node
probe to find something `tsc` names in a tenth of a second.

The library carries no debt here — 156 registers, zero errors — so this gate starts clean and stays that way.
"""
import os
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
_TSC = os.path.join(_REM, "node_modules", ".bin", "tsc")


@pytest.mark.skipif(not os.path.exists(_TSC), reason="needs the remotion toolchain (npm install)")
def test_every_register_typechecks():
    r = subprocess.run([_TSC, "--noEmit"], cwd=_REM, capture_output=True, text=True)
    errs = [ln for ln in (r.stdout + r.stderr).splitlines() if "error TS" in ln]
    assert not errs, (
        "%d TypeScript error(s) — esbuild would bundle and render every one of these:\n%s"
        % (len(errs), "\n".join(errs[:25])))


@pytest.mark.skipif(not os.path.exists(_TSC), reason="needs the remotion toolchain (npm install)")
def test_the_three_js_tags_are_actually_typed():
    """The gate is only worth having if its output is signal.

    r3f v8 augments the GLOBAL `JSX` namespace; under `jsx: react-jsx` the compiler reads
    `React.JSX.IntrinsicElements`, so without the bridge in `src/three-jsx.d.ts` every three.js tag in the
    WebGL registers reports "Property 'mesh' does not exist" — 53 lines of noise that would bury the one real
    error under them and get the whole check switched off. And `three` ships no types of its own, so without
    `@types/three` every material's props resolve to `{}` and a real typo in `meshStandardMaterial` passes.
    Both are load-bearing, so both are asserted rather than remembered.
    """
    assert os.path.exists(os.path.join(_REM, "src", "three-jsx.d.ts")), (
        "the r3f JSX bridge is gone; the typecheck will drown in intrinsic-element noise")
    assert os.path.isdir(os.path.join(_REM, "node_modules", "@types", "three")), (
        "@types/three is not installed; three's classes resolve to {} and material props stop being checked")
