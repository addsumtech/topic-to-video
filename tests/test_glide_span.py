"""The baseline unlock is held for the whole SPAN its type can move in — never switched on and off with the motion.

WHY. runtime/glide's header: switched on with the motion itself, type jumps from whole-pixel to quarter-pixel on the
frame the motion starts, and back on the frame it lands. Measured twice: a fridge film's builders keyed it to
`0 < e < 1` and jitter_qa failed 18 lines with 0.6-1.0 px landing pops; a slide-maker promo shipped a 0.89 px step in
the library's own CommandSummon, whose `inP !== 1 || (fired && t < 0.62)` turned the unlock off while the palette was
still easing to rest. The library held 121 such calls in 87 registers. `scripts/glide_lint.py` reads every
`glide(transform, on, under?)` call and accepts `on` only as the literal `true` or a name declared constant for the
beat (`const x = true`, or a declaration carrying `@glide-span: <why it is constant over the beat>`).
"""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import glide_lint as gl  # noqa: E402


def test_a_motion_condition_is_flagged_and_true_is_not():
    src = ("const a = glide(`translateY(${y}px)`, e !== 1);\n"
           "const b = glide(`translate(${f(x, y)}px, 0)`, true);\n"
           "const c = glide(t, open > 0 && open < 1, 0.5);\n")
    found = gl.switched(src)
    assert [(ln, on) for ln, on in found] == [(1, "e !== 1"), (3, "open > 0 && open < 1")]


def test_a_name_is_accepted_only_when_declared_constant_for_the_beat():
    src = ("const lensMoves = true;\n"
           "const moving = enter !== 1;\n"
           "const span = camera.move !== 'hold'; // @glide-span: the camera's move is fixed for the beat\n"
           "glide(a, lensMoves); glide(b, moving); glide(c, span);\n")
    assert [on for _, on in gl.switched(src)] == ["moving"]


def test_commas_inside_template_literals_and_calls_do_not_split_arguments():
    src = "glide(`translate(${lerp(-20, 0, clamp01(rev))}px, ${y}px)`, rev !== 1)\n"
    assert [on for _, on in gl.switched(src)] == ["rev !== 1"]


def test_the_definition_of_glide_itself_is_not_a_call():
    src = ("export const glide = (transform: string | undefined, on: boolean, under = 1) => {};\n"
           "return (transform, on, under = 1) => glide(transform, allowed && on, under);\n")
    assert gl.switched(src, path="runtime/glide.ts") == []


def test_the_library_holds_every_unlock_for_its_span():
    bad = gl.scan(os.path.join(_ROOT, "remotion", "src", "shots"))
    assert not bad, "%d glide call(s) switch the unlock with the motion, e.g. %s" % (
        len(bad), ["%s:%d %s" % b for b in bad[:6]])


def test_a_films_own_shot_that_switches_the_unlock_fails_the_workshop_check(tmp_path):
    import workshop
    shots = tmp_path / "workshop" / "shots"
    shots.mkdir(parents=True)
    (shots / "Bad.tsx").write_text("import {useGlide} from '@runtime/glide';\n"
                                   "export const Bad = () => { const glide = useGlide(); "
                                   "return glide('translateY(2px)', e !== 1); };\n", encoding="utf-8")
    problems = workshop.glide_problems(str(tmp_path))
    assert problems and "Bad.tsx" in problems[0] and "e !== 1" in problems[0]
