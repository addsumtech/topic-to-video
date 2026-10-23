"""The anchored seams — container, grow, through-window, punch — and the camera hand-off.

WHAT THESE TESTS HOLD, and why each is a behaviour rather than a spelling. A seam that goes quiet is the worst kind
of bug in this tier (the board says one thing, the film draws a fade, every gate is green), and these four seams
have one more way to go quiet than the others: they take hold of an ANCHOR a register draws, and an anchor the
register does not draw would make the seam a no-op. So the anchor is checked three times — in the source
(scripts/carry_anchors.py), on the board (validate.py) and on the frame (seams.tsx stops the render) — and each
check is tested here by breaking the thing it guards (E7).

The geometry and the camera curves are pure functions; they are bundled with esbuild and RUN, the way
tests/test_camera_pan.py runs depth.tsx. Three tests render (needs the remotion toolchain): reduced motion turns a
container into the plain fade, a missing anchor stops the render with the anchor's name, and a dark->light
container stays monotone in the frame's mean luminance (the measurement its exemption from the guard rests on).
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

import carry_anchors as ca
import render_remotion as rr
import seam_plan as sp
import sfx
import validate as v

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
_SRC = os.path.join(_REM, "src")
FILM = open(os.path.join(_SRC, "Film.tsx"), encoding="utf-8").read()
SEAMS = open(os.path.join(_SRC, "seams.tsx"), encoding="utf-8").read()

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")
NEW = ("container", "grow", "through-window", "punch")


# ── the vocabulary reaches the film ────────────────────────────────────────────────────────────────────────────
def test_every_new_word_resolves_and_reaches_a_case_in_the_picker():
    picker = FILM[FILM.index("const pickPresentation"):]
    picker = picker[:picker.index("\n};")]
    cases = set(re.findall(r"case '([a-z-]+)':", picker))
    for w in NEW:
        assert rr.seam_type(w) == w and w in rr._KINETIC_TYPES, w
        assert w in cases, "%s resolves on the board and no presentation draws it" % w
    for alias, want in (("container-transform", "container"), ("shared-element", "container"),
                        ("expand", "grow"), ("zoom-through", "through-window"), ("push-cut", "punch")):
        assert rr.seam_type(alias) == want, alias


def test_the_anchor_travels_with_the_word_to_the_film():
    """`_transition_in` used to copy `type` and `direction` only — an anchored seam would reach Film with no anchor
    and Film would refuse it at render, after validate had passed the board."""
    got = rr._transition_in({"transition_in": {"type": "container", "carry": {"from": "hero", "to": "figure"}}})
    assert got == {"type": "container", "carry": {"from": "hero", "to": "figure"}}, got
    got = rr._transition_in({"transition_style": "grow", "transition_in": {"carry": "screen"}})
    assert got == {"type": "grow", "carry": "screen"}, got
    # the unanchored words carry nothing they do not use
    assert rr._transition_in({"transition_in": {"type": "punch", "carry": "x"}}) == {"type": "punch"}


def test_a_match_cut_is_now_the_container_it_always_described():
    prev = {"match_cut": {"shape": "dot", "from": [0.2, 0.3, 0.1, 0.1], "to": [0.5, 0.5, 0.2, 0.2]}}
    got = rr._transition_in({}, None, prev)
    assert got == {"type": "container", "from": [0.2, 0.3, 0.1, 0.1], "to": [0.5, 0.5, 0.2, 0.2], "shape": "dot"}
    # a seam the arriving beat names itself wins (validate refuses the conflict — tested below)
    assert rr._transition_in({"transition_in": {"type": "wipe"}}, None, prev) == {"type": "wipe"}
    # a malformed match_cut is no seam at all, never a container with garbage rects
    assert rr._transition_in({}, None, {"match_cut": {"from": [1, 2], "to": [0, 0, 1, 1]}}) is None


# ── the anchors in the source ─────────────────────────────────────────────────────────────────────────────────
def test_the_library_declares_the_anchors_the_planner_relies_on():
    want = {"DeviceHero": {"device", "screen"}, "DeviceDemo": {"device", "screen"}, "CodeCompose": {"window"},
            "TermTable": {"window"}, "ObjectStage": {"figure"}, "CardStage": {"hero"}, "CinematicTitle": {"word"}}
    for shot, ids in want.items():
        a = ca.anchors_of(shot)
        assert a and ids <= a["ids"], (shot, a)
    assert "card:" in ca.anchors_of("CardStage")["prefixes"]
    assert ca.has_anchor("CardStage", "card:clock") is True
    assert ca.has_anchor("CardStage", "card:") is False, "a prefix alone names no card"
    assert ca.has_anchor("MapPlate", "window") is False
    assert ca.has_anchor("NoSuchRegister", "window") is None, "an unreadable register is UNKNOWN, not anchor-less"


def test_an_anchor_is_credited_only_to_a_register_that_DRAWS_its_component(tmp_path, monkeypatch):
    """`Device` marks the screen; a register that imports deviceGeometry from the same file and draws no <Device>
    must not be credited with a screen it never puts on the frame. Mutation-checked: a synthetic register that
    does write <Device is credited."""
    shots = tmp_path / "shots"
    shots.mkdir()
    rt = os.path.relpath(os.path.join(_SRC, "runtime", "device"), str(shots))     # a register imports relatively
    (shots / "OnlyGeom.tsx").write_text("import {deviceGeometry} from %s;\nexport const X = 1;\n" % json.dumps(rt))
    (shots / "DrawsIt.tsx").write_text("import {Device, deviceGeometry} from %s;\nconst y = <Device g={g} />;\n"
                                       % json.dumps(rt))
    monkeypatch.setattr(ca, "SRC", str(tmp_path))
    assert ca.anchors_of("OnlyGeom") == {"ids": set(), "prefixes": set()}
    assert {"screen", "device"} <= ca.anchors_of("DrawsIt")["ids"]


def test_a_part_is_not_an_anchor(tmp_path, monkeypatch):
    shots = tmp_path / "shots"
    shots.mkdir()
    (shots / "Parts.tsx").write_text('const a = <div data-carry-part="window" data-carry-radius="4" />;\n')
    monkeypatch.setattr(ca, "SRC", str(tmp_path))
    assert ca.anchors_of("Parts") == {"ids": set(), "prefixes": set()}


# ── the board: validate refuses what the render would refuse ───────────────────────────────────────────────────
def _check(slides, meta=None):
    errors, warnings = [], []
    v._anchored_seams(dict({"design_dna": "product"}, **(meta or {})), slides, errors, warnings)
    return errors, warnings


def test_a_container_onto_a_register_without_the_anchor_is_an_error():
    errs, _ = _check([{"shot": "CodeCompose"}, {"shot": "MapPlate", "transition_in": {"type": "container",
                                                                                     "carry": "window"}}])
    assert any("draws no such anchor" in e and "MapPlate" in e for e in errs), errs
    # the positive control: both ends draw it
    errs, _ = _check([{"shot": "CodeCompose"}, {"shot": "TermTable", "transition_in": {"type": "container",
                                                                                      "carry": "window"}}])
    assert not errs, errs


def test_an_anchored_seam_that_names_no_anchor_is_an_error_not_a_fade():
    for word in ("container", "grow", "through-window"):
        errs, _ = _check([{"shot": "CodeCompose"}, {"shot": "TermTable", "transition_in": {"type": word}}])
        assert any("names" in e and "anchor" in e for e in errs), (word, errs)
    errs, _ = _check([{"shot": "CodeCompose"}, {"shot": "TermTable", "transition_style": "grow"}])
    assert errs, "a style word alone names no anchor and must be refused"


def test_grow_and_window_check_only_the_LEAVING_beats_anchor():
    errs, _ = _check([{"shot": "TermTable"}, {"shot": "MapPlate", "transition_in": {"type": "through-window",
                                                                                   "carry": "window"}}])
    assert not errs, errs
    errs, _ = _check([{"shot": "MapPlate"}, {"shot": "TermTable", "transition_in": {"type": "grow", "carry": "figure"}}])
    assert any("leaving beat" in e for e in errs), errs


def test_the_punch_is_once_per_film():
    one = [{"shot": "MapPlate"}, {"shot": "MapPlate", "relation": "payoff", "transition_in": {"type": "punch"}}]
    assert not _check(one)[0]
    two = one + [{"shot": "MapPlate"}, {"shot": "MapPlate", "relation": "payoff", "transition_in": {"type": "punch"}}]
    errs, _ = _check(two)
    assert any("2 punch seams" in e for e in errs), errs
    _, warns = _check([{"shot": "MapPlate"}, {"shot": "MapPlate", "relation": "continuation",
                                              "transition_in": {"type": "punch"}}])
    assert any("neither the payoff nor the climax" in w for w in warns), warns


def test_a_match_cut_must_have_a_next_beat_and_must_not_fight_its_seam():
    errs, _ = _check([{"shot": "MapPlate", "match_cut": {"from": [0.5, 0.5, 0.2, 0.2], "to": [0.5, 0.5, 0.3, 0.3]}},
                      {"shot": "MapPlate", "transition_in": {"type": "wipe"}}])
    assert any("one cut, two claims" in e for e in errs), errs
    errs, _ = _check([{"shot": "MapPlate", "match_cut": {"from": [0.5, 0.5, 0.2, 0.2], "to": [0.5, 0.5, 0.3, 0.3]}},
                      {"shot": "MapPlate"}])
    assert not errs, errs
    # on the last scene the existing match_cut check is an ERROR now that it renders
    src = open(os.path.join(_ROOT, "scripts", "validate.py"), encoding="utf-8").read()
    assert 'errors.append(f"{tag}: match_cut is on the LAST scene' in src


def test_a_new_seam_on_a_crossing_warns_that_the_guard_will_draw_a_fade():
    _, warns = _check([{"shot": "MapPlate"}, {"shot": "ObjectStage", "key": "light",
                                              "transition_in": {"type": "punch"}, "relation": "payoff"}])
    assert any("dark/light boundary" in w for w in warns), warns
    # the container is exempt from the guard, so it does NOT warn on the same crossing
    _, warns = _check([{"shot": "ObjectStage"}, {"shot": "ObjectStage", "key": "light",
                                                 "transition_in": {"type": "container", "carry": "figure"}}])
    assert not any("dark/light boundary" in w for w in warns), warns


def test_the_camera_handoff_refusals():
    def hand(cam, nxt=None):
        e, w = [], []
        sl = [{"shot": "MapPlate", "camera": cam}]
        if nxt is not None:
            sl.append(nxt)
        v._camera_handoffs(sl, e, w)
        return e, w
    assert not hand({"move": "push", "handoff": True}, {"shot": "MapPlate", "relation": "continuation"})[0]
    assert hand({"move": "hold", "handoff": True}, {"shot": "MapPlate"})[0]
    assert hand({"move": "push", "handoff": True, "pan": [1, 0]}, {"shot": "MapPlate"})[0]
    assert hand({"move": "push", "handoff": True})[0], "the last beat has no one to hand to"
    assert hand({"move": "push", "handoff": True}, {"shot": "MapPlate", "camera": {"move": "pull"}})[0]
    assert hand({"move": "push", "handoff": "yes"}, {"shot": "MapPlate"})[0]
    _, w = hand({"move": "push", "handoff": True}, {"shot": "MapPlate", "relation": "new-topic",
                                                     "transition_in": {"type": "wipe"}})
    assert len(w) == 2, w


# ── the planner ───────────────────────────────────────────────────────────────────────────────────────────────
def _film(n=20, fill="MapPlate"):
    sl = [{"shot": fill, "relation": "continuation"} for _ in range(n)]
    sl[0]["relation"] = "open"
    return sl


def test_the_planner_carries_a_shared_anchor_across_a_continuation_and_only_then():
    sl = _film()
    sl[9], sl[10] = {"shot": "DeviceHero", "relation": "continuation"}, {"shot": "DeviceDemo", "relation": "continuation"}
    got = sp.plan(sl, "product")
    assert got.get(10, {}).get("type") == "container" and got[10]["carry"] == "device", got
    # MUTATION: the same board with the arriving register swapped for one that draws no device — no container
    sl[10] = {"shot": "MapPlate", "relation": "continuation"}
    assert sp.plan(sl, "product") == {}, "a continuation with nothing shared must stay an invisible cut"


def test_a_new_topic_out_of_a_window_goes_through_it_and_out_of_a_thing_grows():
    sl = _film()
    sl[9], sl[10] = {"shot": "CodeCompose"}, {"shot": "MapPlate", "relation": "new-topic"}
    got = sp.plan(sl, "product")
    assert got[10]["type"] == "through-window" and got[10]["carry"] == "window", got
    sl[9] = {"shot": "ObjectStage"}
    assert sp.plan(sl, "product")[10]["type"] == "clock", "a grow onto the SAME ground would be invisible"
    sl[10]["ground"] = "#26324d"
    got = sp.plan(sl, "product")
    assert got[10] == {"type": "grow", "carry": "figure", "why": got[10]["why"]}, got


def test_a_crossing_beat_key_is_a_crossing_for_the_planner():
    """`_crosses` reads registers only; a `key: light` beat on a dark film crosses whatever its register paints,
    and Film draws a fade there. The planner must route it the crossing way."""
    sl = _film()
    sl[9], sl[10] = {"shot": "ObjectStage"}, {"shot": "MapPlate", "relation": "new-topic", "key": "light"}
    assert sp.plan(sl, "product")[10]["type"] == "through-dark"


def test_the_punch_goes_to_the_climax_payoff_once():
    sl = _film(30)
    sl[8] = {"shot": "MapPlate", "relation": "payoff", "climax": True}
    sl[20] = {"shot": "MapPlate", "relation": "payoff", "energy": "peak"}
    got = sp.plan(sl, "product")
    punches = [i for i, m in got.items() if m["type"] == "punch"]
    assert len(punches) == 1, got
    plain = _film(30)
    plain[8] = {"shot": "MapPlate", "relation": "payoff"}
    assert sp.plan(plain, "product")[8]["type"] == "dissolve", "an ordinary payoff keeps its dissolve"


def test_every_anchored_proposal_names_an_anchor_its_registers_draw():
    """The planner and the validator must agree: whatever the plan writes, validate passes."""
    sl = _film(30)
    sl[4], sl[5] = {"shot": "DeviceHero"}, {"shot": "DeviceHero", "relation": "continuation"}
    sl[12], sl[13] = {"shot": "TermTable"}, {"shot": "MapPlate", "relation": "new-topic"}
    sl[22] = {"shot": "MapPlate", "relation": "payoff", "climax": True}
    marks = sp.plan(sl, "product")
    for i, m in marks.items():
        sl[i]["transition_in"] = {k: x for k, x in m.items() if k != "why"}
    errs, _ = _check(sl)
    assert not errs, (marks, errs)
    assert {"container", "through-window", "punch"} <= {m["type"] for m in marks.values()}, marks


def test_the_handoff_plan_needs_a_continuation_across_an_unmarked_cut():
    sl = _film(12)
    cams = {3: {"move": "push"}}
    assert sp.plan_handoffs(sl, cams, {}) == [3]
    assert sp.plan_handoffs(sl, cams, {4: {"type": "wipe"}}) == [], "a marked seam moves the frame itself"
    sl[4]["relation"] = "new-topic"
    assert sp.plan_handoffs(sl, cams, {}) == []
    sl[4]["relation"] = "continuation"
    assert 3 not in sp.plan_handoffs(sl, {3: {"move": "push"}, 4: {"move": "push"}}, {}), "one channel per beat"


# ── sound ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_cues_peak_on_each_seams_own_fastest_frame():
    assert set(sfx.SEAM_PEAK) == set(NEW), sfx.SEAM_PEAK
    m = re.search(r"export const PUNCH_CUT = (\d+) / (\d+);", SEAMS)
    assert m and abs(sfx.SEAM_PEAK["punch"] - int(m.group(1)) / int(m.group(2))) < 1e-9
    fps, n = 30, 12
    scenes = [{"durationInFrames": 120, "transitionIn": None}, {"durationInFrames": 120, "transitionIn": {"type": "punch"}},
              {"durationInFrames": 120, "transitionIn": {"type": "through-window", "carry": "window"}},
              {"durationInFrames": 120, "transitionIn": {"type": "container", "carry": "x"}}]
    cues = sfx.plan_cues(scenes, fps, seam_frames=n)
    impact = [c for c in cues if c[1] == "impact"]
    assert impact and abs(impact[0][0] - (4.0 + 5 / fps)) < 1e-6, cues      # ON the cut, frame 5 of the seam
    wh = [c for c in cues if c[1] == "whoosh"]
    assert abs(wh[0][0] - (8.0 + 5 / fps)) < 1e-6, "a whoosh peaks a frame before the window's cut"
    assert wh[1][2] < wh[0][2], "a container is the softest seam — the element never leaves the screen"


# ── the pure geometry and the camera curves, RUN ──────────────────────────────────────────────────────────────
def _run(entry_src, body):
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(_REM, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="seam_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        open(entry, "w", encoding="utf-8").write(
            "import * as M from %s;\nconst out: any = {};\n%s\nconsole.log(JSON.stringify(out));\n"
            % (json.dumps(entry_src), body))
        out = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--external:react",
                            "--external:remotion", "--outfile=" + out, "--log-level=error"],
                           cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", out], cwd=_REM, capture_output=True, text=True,
                           env=dict(os.environ, NODE_PATH=os.path.join(_REM, "node_modules")))
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_the_container_lands_exactly_and_arcs_only_when_it_travels_far_diagonally():
    out = _run(os.path.join(_SRC, "seams"), """
      const a = {x: 1500, y: 100, w: 200, h: 120, r: 8}, b = {x: 500, y: 400, w: 900, h: 500, r: 18};
      out.p0 = M.containerAt(0, a, b, 1920, 1080); out.p1 = M.containerAt(1, a, b, 1920, 1080);
      out.mid = M.containerAt(0.5, a, b, 1920, 1080);
      const near = {x: 520, y: 410, w: 900, h: 500, r: 18};
      out.near = M.containerAt(0.5, b, near, 1920, 1080);
    """)
    for k in ("x", "y", "w", "h"):
        assert abs(out["p0"][k] - [1500, 100, 200, 120][("x", "y", "w", "h").index(k)]) < 1e-6
        assert abs(out["p1"][k] - [500, 400, 900, 500][("x", "y", "w", "h").index(k)]) < 1e-6
    # a long diagonal travel is an ARC: the centre at mid-travel is off the straight line between the two centres
    c0, c1 = (1600, 160), (950, 650)
    m = out["mid"]
    cx, cy = m["x"] + m["w"] / 2, m["y"] + m["h"] / 2
    fx, fy = (cx - c0[0]) / (c1[0] - c0[0]), (cy - c0[1]) / (c1[1] - c0[1])
    assert abs(fx - fy) > 0.05, "the long diagonal went in a straight line (%.3f vs %.3f)" % (fx, fy)
    nm = out["near"]
    nfx, nfy = (nm["x"] - 500) / 20, (nm["y"] - 400) / 10
    assert abs(nfx - nfy) < 1e-6, "a short move should not arc"


def test_the_window_push_is_exponential_starts_at_rest_and_never_uncovers_the_frame():
    out = _run(os.path.join(_SRC, "seams"), """
      const a = {x: 1500, y: 700, w: 300, h: 200, r: 12};
      out.s = []; for (let i = 0; i <= 6; i++) out.s.push(M.windowAt(i / 12, a, 1920, 1080));
    """)
    s = out["s"]
    assert abs(s[0]["k"] - 1) < 1e-9 and abs(s[0]["tx"]) < 1e-6 and abs(s[0]["ty"]) < 1e-6
    K = s[-1]["K"]
    assert abs(s[-1]["k"] - K) < 1e-6
    # at the cut the anchor box covers the frame with the 1.06 to spare it settles from
    a = (1500, 700, 300, 200)
    k, tx, ty = s[-1]["k"], s[-1]["tx"], s[-1]["ty"]
    assert tx + k * a[0] <= 0 and ty + k * a[1] <= 0 and tx + k * (a[0] + a[2]) >= 1920 and ty + k * (a[1] + a[3]) >= 1080
    for f in s:
        assert f["tx"] <= 1e-6 and f["tx"] + f["k"] * 1920 >= 1920 - 1e-6, f
        assert f["ty"] <= 1e-6 and f["ty"] + f["k"] * 1080 >= 1080 - 1e-6, f
    # accelerating: each frame's zoom step (in log scale) is larger than the one before it
    import math
    steps = [math.log(s[i + 1]["k"]) - math.log(s[i]["k"]) for i in range(len(s) - 1)]
    assert all(b > a for a, b in zip(steps, steps[1:])), steps


def test_the_handoff_hands_over_its_velocity_and_never_reverses():
    out = _run(os.path.join(_SRC, "runtime", "handoff"), """
      const dur = 180, amp = 0.05;
      out.a = []; for (let f = 0; f < dur; f++) out.a.push(M.handoffOut(f, dur, amp, 'push'));
      const v = out.a[dur - 1].v;
      out.v = v;
      out.b = []; for (let f = 0; f < 150; f++) out.b.push(M.handoffIn(f, 150, v, 0.06));
      out.pull = []; for (let f = 0; f < 150; f++) out.pull.push(M.handoffIn(f, 150, -v, 0.06));
      out.tight = []; for (let f = 0; f < 150; f++) out.tight.push(M.handoffIn(f, 150, v, v * 14));
    """)
    a = [x["extra"] for x in out["a"]]
    assert a[0] == 0 and abs(a[-1] - 0.05) < 1e-9, "the move spends exactly its budget"
    va = a[-1] - a[-2]
    b = out["b"]
    assert abs((b[1] - b[0]) - va) < 1e-9, "B starts at A's end velocity (%g vs %g)" % (b[1] - b[0], va)
    assert all(y >= x - 1e-12 for x, y in zip(b, b[1:])), "the inherited push reverses"
    assert max(b) <= 0.06 + 1e-9
    assert b[-1] - b[-2] < va * 0.05, "the inherited velocity has not decayed by the end of the beat"
    p = out["pull"]
    assert all(y <= x + 1e-12 for x, y in zip(p, p[1:])) and abs(p[-1]) < 0.06 * 0.05
    t = out["tight"]
    assert max(t) <= out["v"] * 14 + 1e-9, "a hand-off overran the room it was given"


def test_a_word_window_aims_at_the_ink_with_the_most_room():
    """The glyph window pushes into the centre of the thickest stroke: on a thin bar beside a fat block the room is
    found in the block, at its centre, and is its half-width (chamfer distance, within a pixel)."""
    out = _run(os.path.join(_SRC, "seams"), """
      const w = 60, h = 40, ink = new Uint8Array(w * h);
      for (let y = 5; y < 35; y++) for (let x = 2; x < 5; x++) ink[y * w + x] = 1;        // a thin stroke
      for (let y = 5; y < 35; y++) for (let x = 20; x < 50; x++) ink[y * w + x] = 1;      // a 30x30 block
      const r = M.inkRoom(ink, w, h);
      out.x = r.i % w; out.y = Math.floor(r.i / w); out.d = r.d;
      out.none = M.inkRoom(new Uint8Array(w * h), w, h);
    """)
    assert 32 <= out["x"] <= 37 and 17 <= out["y"] <= 22, out
    assert 14 <= out["d"] <= 16.5, out
    assert out["none"]["i"] == -1, "no ink must answer 'no room', and the seam refuses it"


# ── on the frame ──────────────────────────────────────────────────────────────────────────────────────────────
_PAIR = [{"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone"}},
         {"shot": "DeviceDemo", "durF": 60, "props": {"device": "phone", "placement": "left"}}]


def _still(tmp_path, name, scenes, frame, reduced=False):
    props = {"scenes": scenes, "dna": "product", "captions": False, "camera": 0, "cameraBed": False}
    if reduced:
        props["reducedMotion"] = True
    pf = str(tmp_path / (name + ".json"))
    json.dump(props, open(pf, "w", encoding="utf-8"))
    png = str(tmp_path / (name + ".png"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png, "--frame=%d" % frame, "--gl=angle",
                        "--timeout=150000", "--scale=0.5", "--log=error", "--props=" + pf],
                       cwd=_REM, capture_output=True, text=True, timeout=900)
    return r, png


@needs_toolchain
def test_under_reduced_motion_a_container_is_the_plain_fade(tmp_path):
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    sc = json.loads(json.dumps(_PAIR))
    sc[1]["transitionIn"] = {"type": "container", "carry": "device"}
    r1, a = _still(tmp_path, "c", sc, 53, reduced=True)
    sc[1]["transitionIn"] = {"type": "dissolve"}
    r2, b = _still(tmp_path, "f", sc, 53, reduced=True)
    assert r1.returncode == 0 and r2.returncode == 0, (r1.stderr + r2.stderr)[-600:]
    d = float(np.abs(np.asarray(Image.open(a).convert("L"), dtype=float)
                     - np.asarray(Image.open(b).convert("L"), dtype=float)).mean())
    assert d < 2.0, "a container under reduced motion still draws its own move (mean |diff| %.2f)" % d


@needs_toolchain
def test_a_missing_anchor_stops_the_render_with_its_name(tmp_path):
    sc = json.loads(json.dumps(_PAIR))
    sc[1] = {"shot": "MapPlate", "durF": 60, "props": {}, "transitionIn": {"type": "container", "carry": "device"}}
    r, _png = _still(tmp_path, "missing", sc, 53)
    assert r.returncode != 0, "a container onto a register that draws no 'device' rendered anyway"
    assert "device" in (r.stdout + r.stderr) and "anchor" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-800:]


@needs_toolchain
def test_a_dark_to_light_container_is_monotone_in_luminance(tmp_path):
    """The measurement the container's place in CANNOT_FLASH rests on, kept as a test: every frame's mean sits
    between the two beats' and the seam never turns back."""
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    sc = json.loads(json.dumps(_PAIR))
    sc[1]["key"] = "light"
    sc[1]["transitionIn"] = {"type": "container", "carry": "screen"}
    means = []
    for f in (47, 50, 53, 56, 59, 61):
        r, png = _still(tmp_path, "m%d" % f, sc, f)
        assert r.returncode == 0, (r.stdout + r.stderr)[-600:]
        means.append(float(np.asarray(Image.open(png).convert("L"), dtype=float).mean()))
    assert all(b >= a - 0.5 for a, b in zip(means, means[1:])), means
    assert means[0] < means[-1] and min(means) >= means[0] - 0.5 and max(means) <= means[-1] + 0.5, means
