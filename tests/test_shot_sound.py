"""Shot-owned sound (runtime/sound.ts + scripts/shot_sounds.py) and the film's close (sfx.close_mode).

What is held here:
  * ONE vocabulary: every SOUND_KINDS kind the runtime offers has a synthesised cue and a gain in sfx, and every cue
    keeps its energy in the two bands the SFX bus passes (the voice owns 110-800 Hz);
  * a register's SOUNDS literal is read, refused when it is not a literal, and resolved against the beat's props the
    way runtime/sound.ts soundTs resolves it (the same numbers, run under node);
  * a declared t lands on the frame useT reaches it on, through the beat's sync warp;
  * the mix: a register's sounds are thinned and capped, a board's are kept, `sounds: "none"` silences a beat, a
    stage step's sound lands on its arrival, and the close is full / soft / none — soft by default on a calm film.
"""
import os
import sys

import numpy as np
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_SKILL, "scripts"))
sys.path.insert(0, _HERE)

import _tsprobe  # noqa: E402
import sfx  # noqa: E402
import shot_sounds  # noqa: E402
import stage_runs  # noqa: E402

needs_node = pytest.mark.skipif(not _tsprobe.available(), reason="needs node + remotion/node_modules")


def test_every_sound_kind_is_synthesised_and_gained():
    kinds = shot_sounds.sound_kinds()
    assert set(kinds) == set(sfx.EVENT_GAIN), "runtime/sound.ts SOUND_KINDS and sfx.EVENT_GAIN must name the same kinds"
    for k in kinds + ("settle",):
        c = sfx.cue(k)
        assert c is not None and len(c) > 0.04 * sfx.SR and 0.2 < float(np.max(np.abs(c))) <= 1.0, k
        assert np.array_equal(c, sfx.cue(k)), "%s must synthesise identically every time" % k


@pytest.mark.parametrize("kind", ["strike", "chime", "swell", "settle", "tick", "click"])
def test_a_cue_lives_in_the_bands_the_bus_passes(kind):
    """The SFX bus is highpassed at 800 Hz and lowpassed at 110 Hz into two bands; 110-800 Hz is the voice's. A cue
    whose energy sat there would be deleted by the chain — a sound designed and never heard."""
    c = sfx.cue(kind).astype(np.float64)
    spec = np.abs(np.fft.rfft(c)) ** 2
    f = np.fft.rfftfreq(len(c), 1.0 / sfx.SR)
    mid = spec[(f > sfx._SFX_LP) & (f < sfx._SFX_HP)].sum() / spec.sum()
    assert mid < 0.25, "%s puts %.0f%% of its energy where the bus deletes it" % (kind, mid * 100)


def test_a_register_declaration_is_read_and_a_non_literal_refused():
    assert shot_sounds.register_sounds("AuroraCurtain") == [{"kind": "swell", "at": "surgeAt"}]
    assert shot_sounds.register_sounds("LightShafts") == [{"kind": "swell", "at": "breakAt"}]
    assert shot_sounds.register_sounds("NebulaField") == [], "a nebula declares no sound"
    src = "export const SOUNDS = [\n  {kind: 'tick', each: 'items', at: 0.3, to: 0.7, gain: 0.5}, // a comment\n] as const;"
    assert shot_sounds.parse_sounds(src) == [{"kind": "tick", "each": "items", "at": 0.3, "to": 0.7, "gain": 0.5}]
    for bad in ("export const SOUNDS = [{kind: 'tick', at: T0}];",          # an expression
                "export const SOUNDS = [{kind: 'bell', at: 0.5}];",         # no such kind
                "export const SOUNDS = [{kind: 'tick', at: 1.5}];",         # off the clock
                "export const SOUNDS = [{kind: 'tick', at: 0.5, when: 'x'}];"):
        with pytest.raises(shot_sounds.SoundDeclError):
            shot_sounds.parse_sounds(bad)


@needs_node
def test_python_resolves_a_declaration_exactly_as_the_runtime_does():
    decls = [{"kind": "strike", "at": 0.72}, {"kind": "swell", "at": "surgeAt"}, {"kind": "tick", "each": "items", "at": 0.3,
                                                                                    "to": 0.7}]
    cases = [{}, {"surgeAt": 0.4}, {"items": [1, 2, 3, 4]}, {"items": ["a"], "surgeAt": 0.0}]
    import json
    r = _tsprobe.run_ts("import * as S from %s;\n" % _tsprobe.mod("sound"),
                        "const D = %s; const C = %s;\nout.ts = C.map((p: any) => D.map((d: any) => S.soundTs(d, p)));"
                        % (json.dumps(decls), json.dumps(cases)))
    py = [[shot_sounds.decl_ts(d, p) for d in decls] for p in cases]
    assert np.allclose(np.concatenate([np.ravel(x) for row in r["ts"] for x in row if x]),
                       np.concatenate([np.ravel(x) for row in py for x in row if x]))
    assert [[len(x) for x in row] for row in r["ts"]] == [[len(x) for x in row] for row in py]


def test_a_declared_point_lands_on_the_frame_useT_reaches_it_on():
    # useT holds its pads: t=ENTRY_T is the pad's last frame, t=1 the last frame before the closing pad
    assert shot_sounds.frame_at_t(shot_sounds.ENTRY_T, 180) == shot_sounds.SEAM_FRAMES
    assert shot_sounds.frame_at_t(1.0, 180) == 180 - 1 - shot_sounds.SEAM_FRAMES
    assert shot_sounds.frame_at_t(0.0, 180) == shot_sounds.SEAM_FRAMES, "before the entry the clock is held"
    sc = {"shot": "AuroraCurtain", "props": {"surgeAt": 0.7}, "durF": 180}
    ev = shot_sounds.scene_events(sc, 30)
    assert ev == [{"t": pytest.approx(shot_sounds.frame_at_t(0.7, 180) / 30.0), "name": "swell", "gain": 1.0,
                   "src": "shot"}]
    # through the beat's sync warp: the sound is where the PICTURE is, the warped frame unwarped to film time
    import sync_qa
    g = shot_sounds.frame_at_t(0.7, 180)
    warp = [[12, 12], [100, 80], [167, 167]]
    ev2 = shot_sounds.scene_events(dict(sc, warp=warp), 30)
    assert ev2[0]["t"] == pytest.approx(sync_qa.unwarp_frame(g, warp) / 30.0) and ev2[0]["t"] != ev[0]["t"]
    assert shot_sounds.scene_events(dict(sc, props={}), 30) == [], "no surgeAt, no surge, no sound"
    assert shot_sounds.scene_events(dict(sc, stage={"run": "w"}), 30) == [], "a stage beat's sounds are its steps'"


def _film(n=3, dur=150, **last):
    sc = [{"durationInFrames": dur, "transitionIn": None if i == 0 else {"type": "wipe"}} for i in range(n)]
    sc[-1]["shots"] = [{"startFrame": 0}]
    sc[-1].update(last)
    return sc


def test_the_close_is_full_soft_or_none():
    land = 2 * 150 / 30.0
    full = sfx.plan_cues(_film(), 30, close="full")
    soft = sfx.plan_cues(_film(), 30, close="soft")
    none = sfx.plan_cues(_film(), 30, close="none")
    assert {"riser", "impact", "sparkle"} <= {n for _t, n, _g in full}
    assert [(t, n) for t, n, _g in soft if n in ("riser", "impact", "sparkle", "settle")] == [(pytest.approx(land), "settle")]
    assert not {"riser", "impact", "sparkle", "settle"} & {n for _t, n, _g in none}
    # the seam into the close keeps its own whoosh when no riser is building across it
    assert any(n == "whoosh" and t > land for t, n, _g in soft) and any(n == "whoosh" and t > land for t, n, _g in none)
    assert not any(n == "whoosh" and t > land - 1e-9 for t, n, _g in full), "under the full close the riser IS that seam"
    with pytest.raises(ValueError):
        sfx.plan_cues(_film(), 30, close="loud")


def test_the_close_defaults_from_the_films_tempo():
    assert sfx.close_mode({}) == ("soft", sfx.close_mode({})[1]) and "calm" in sfx.close_mode({})[1]
    assert sfx.close_mode({"purpose": "launch"})[0] == "full"
    assert sfx.close_mode({"renderer": "remotion", "sound_design": True, "bgm": "auto"})[0] == "full", "a scored film lands"
    assert sfx.close_mode({"purpose": "launch", "close_sound": "none"}) == ("none", "meta.close_sound")
    with pytest.raises(ValueError):
        sfx.close_mode({"close_sound": "quiet"})


def test_a_registers_sounds_are_thinned_and_a_boards_are_kept():
    evs = [{"t": 1.0, "name": "tick", "src": "shot"}, {"t": 1.05, "name": "tick", "src": "shot"},
           {"t": 1.3, "name": "tick", "src": "shot"}, {"t": 2.0, "name": "chime", "src": "board", "gain": 0.5}]
    sc = _film(events=evs)
    cs = sfx.plan_cues(sc, 30, close="none")
    t0 = 2 * 150 / 30.0
    ticks = [t for t, n, _g in cs if n == "tick"]
    assert ticks == [pytest.approx(t0 + 1.0), pytest.approx(t0 + 1.3)], "two ticks 50 ms apart are one sound"
    chime = [(t, g) for t, n, g in cs if n == "chime"]
    assert chime == [(pytest.approx(t0 + 2.0), pytest.approx(sfx.EVENT_GAIN["chime"] * 0.5))]
    with pytest.raises(ValueError):
        sfx.plan_cues(_film(events=[{"t": 1.0, "name": "gong"}]), 30)
    # with no SFX bed, a register's sounds still play alone (meta.shot_sounds), thinned the same way
    alone = sfx.plan_cues(sc, 30, events_only=True)
    assert [n for _t, n, _g in alone] == ["tick", "tick", "chime"]


def test_a_silent_beat_plays_nothing_under_it():
    sc = _film(n=3)
    sc[1]["silent"] = True
    sc[1]["events"] = [{"t": 1.0, "name": "strike", "src": "shot"}]
    cs = sfx.plan_cues(sc, 30, close="soft")
    assert not any(150 / 30.0 <= t < 300 / 30.0 for t, _n, _g in cs), cs
    assert any(n == "settle" for _t, n, _g in cs), "the next beat's close still sounds"


def test_a_stage_steps_sound_lands_on_its_arrival():
    scenes = [{"stage": {"run": "w"}, "props": {"steps": [{"t": 1.5, "sound": "chime"},
                                                          {"t": 2.0, "sound": {"kind": "swell", "gain": 0.6}},
                                                          {"t": 2.5, "cursor": {"u": 0.5, "v": 0.5, "click": True}}]}}]
    assert stage_runs.sound_events(scenes) == [[{"t": 1.5, "name": "chime"}, {"t": 2.0, "name": "swell", "gain": 0.6},
                                                {"t": 2.5, "name": "click"}]]
    assert any("bell" in p for p in stage_runs.step_problems([{"at": 0.5, "sound": "bell"}]))


def test_a_board_sound_is_checked_before_the_render():
    slides = [{"index": 1, "shot": "AuroraCurtain", "narration": "极光在高处发光",
               "sounds": [{"kind": "chime", "at": {"cue": "高处"}}, {"kind": "swell", "at": 1.0, "gain": 0.4}]},
              {"index": 2, "shot": "NebulaField", "narration": "星云", "sounds": "none"},
              {"index": 3, "shot": "NebulaField", "narration": "星云", "sounds": [{"kind": "gong", "at": 1}]},
              {"index": 4, "shot": "NebulaField", "narration": "星云", "sounds": [{"kind": "tick", "at": {"cue": "太阳"}}]}]
    probs = shot_sounds.problems(slides)
    assert len(probs) == 2 and "slide 3" in probs[0] and "slide 4" in probs[1] and "does not say" in probs[1], probs


def test_a_strike_peaks_on_its_frame_in_the_built_track(tmp_path):
    """build_sfx_track aligns a cue by its envelope's peak: a strike planned at 1.0 s peaks there (within 5 ms)."""
    import wave
    out = str(tmp_path / "s.wav")
    assert sfx.build_sfx_track([(1.0, "strike", 0.7)], 2.0, out)
    with wave.open(out, "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64)
    win = int(0.005 * sfx.SR)
    env = np.sqrt(np.convolve(a ** 2, np.ones(win) / win, mode="same"))
    assert abs(np.argmax(env) / sfx.SR - 1.0) < 0.005


@needs_node
def test_a_typed_prop_keys_once_per_character_on_the_typing_curve_in_both_runtimes():
    """Every UI film types — a command, a prompt, code — and until now it typed in silence: only two registers declared
    any sound and none had a key (the peer launch skills put a key on each character's frame). `type` names a string
    prop; one key sounds where each character appears on the register's own typing curve (`ease`)."""
    decls = [{"kind": "key", "type": "command", "at": 0.14, "to": 0.44, "ease": "out-cubic"},
             {"kind": "key", "type": "line", "at": 0.2, "to": 0.6}]
    cases = [{"command": "npx skills add x"}, {"line": "ab"}, {}]
    import json
    r = _tsprobe.run_ts("import * as S from %s;\n" % _tsprobe.mod("sound"),
                        "const D = %s; const C = %s;\nout.ts = C.map((p: any) => D.map((d: any) => S.soundTs(d, p)));"
                        % (json.dumps(decls), json.dumps(cases)))
    py = [[shot_sounds.decl_ts(d, p) for d in decls] for p in cases]
    assert [[len(x) for x in row] for row in r["ts"]] == [[len(x) for x in row] for row in py] == [[16, 0], [0, 2], [0, 0]]
    assert np.allclose(r["ts"][0][0], py[0][0]) and np.allclose(r["ts"][1][1], py[1][1])
    ks = py[0][0]
    assert ks == sorted(ks) and 0.14 < ks[0] and ks[-1] == pytest.approx(0.44)
    assert ks[1] - ks[0] < ks[-1] - ks[-2], "out-cubic types fast first and slows into the last characters"
    # the character count the register draws, floor(n * ease(u)), reaches i exactly at the i-th key
    n = 16
    for i, t in enumerate(ks, 1):
        u = (t - 0.14) / 0.30
        assert int(n * (1 - (1 - u) ** 3) + 1e-9) >= i
    assert py[1][1] == [pytest.approx(0.4), pytest.approx(0.6)], "linear: evenly, the last on `to`"


def test_a_type_declaration_needs_a_string_prop_name_and_a_known_ease():
    for bad in ("export const SOUNDS = [{kind: 'key', type: 3, at: 0.1, to: 0.4}];",
                "export const SOUNDS = [{kind: 'key', type: 'x', at: 0.1, to: 0.4, ease: 'bounce'}];",
                "export const SOUNDS = [{kind: 'key', type: 'x', each: 'y', at: 0.1, to: 0.4}];"):
        with pytest.raises(shot_sounds.SoundDeclError):
            shot_sounds.parse_sounds(bad)


def test_a_register_that_rounds_its_typed_count_keys_half_a_character_earlier_in_both_runtimes():
    """TermFrame and TermTable draw round(n * u) characters, not floor: character i shows when n*u reaches i - 0.5, so
    a key placed on floor's curve sounded half a character late — 27 ms on TermTable's command. `draw: 'round'`."""
    decls = [{"kind": "key", "type": "cmd", "at": 0.05, "to": 0.16, "draw": "round"}]
    cases = [{"cmd": "ls -la"}, {"cmd": "a"}]
    import json
    r = _tsprobe.run_ts("import * as S from %s;\n" % _tsprobe.mod("sound"),
                        "const D = %s; const C = %s;\nout.ts = C.map((p: any) => D.map((d: any) => S.soundTs(d, p)));"
                        % (json.dumps(decls), json.dumps(cases)))
    py = [[shot_sounds.decl_ts(d, p) for d in decls] for p in cases]
    assert np.allclose(r["ts"][0][0], py[0][0]) and np.allclose(r["ts"][1][0], py[1][0])
    n = 6
    for i, t in enumerate(py[0][0], 1):
        u = (t - 0.05) / 0.11
        assert int(n * u + 0.5 + 1e-9) == i, (i, t)        # Math.round's count on the key's own instant is i
    assert py[1][0] == [pytest.approx(0.05 + 0.11 * 0.5)], "one character shows half-way along the curve"
    with pytest.raises(shot_sounds.SoundDeclError):
        shot_sounds.parse_sounds("export const SOUNDS = [{kind: 'key', type: 'x', at: 0.1, to: 0.4, draw: 'ceil'}];")


def test_every_terminal_types_its_command_with_a_key_on_termframes_own_curve():
    """TermFrame (runtime/dna.tsx) types `cmd` over [0.05, 0.05 + max(0.06, runAt - 0.09)] and draws round(n*u) of it;
    every register that hands it a command declares the key on exactly that span, read from the code, so a register
    that changes runAt or TermFrame that changes its curve fails here instead of keying off the picture."""
    import re
    dna = open(os.path.join(_SKILL, "remotion", "src", "runtime", "dna.tsx"), encoding="utf-8").read()
    m = re.search(r"Math\.round\(chars\.length \* clamp01\(\(t - ([\d.]+)\) / Math\.max\(([\d.]+), runAt - ([\d.]+)\)\)\)", dna)
    assert m, "TermFrame's typing curve changed — re-derive the terminals' key declarations"
    t0, lo, sub = map(float, m.groups())
    default_run = float(re.search(r"runAt = ([\d.]+), children\}\) =>", dna).group(1))
    shots = os.path.join(_SKILL, "remotion", "src", "shots")
    users = []
    for f in sorted(os.listdir(shots)):
        src = open(os.path.join(shots, f), encoding="utf-8").read()
        tag = re.search(r"<TermFrame\b[^>]*\bcmd=\{cmd\}[^>]*>", src)
        if not tag:
            continue
        users.append(f[:-4])
        ra = re.search(r"runAt=\{([A-Z_]+|[\d.]+)\}", tag.group(0))
        run = default_run
        if ra:
            v = ra.group(1)
            run = float(v) if v[0].isdigit() else float(re.search(r"const %s = ([\d.]+)" % v, src).group(1))
        keys = [d for d in shot_sounds.parse_sounds(src, where=f) if d["kind"] == "key"]
        assert keys == [{"kind": "key", "type": "cmd", "at": t0, "to": pytest.approx(t0 + max(lo, run - sub)),
                         "draw": "round"}], (f, keys)
    assert len(users) >= 7, users


def test_a_key_sounds_on_the_first_frame_its_character_is_drawn():
    """Measured on a rendered TermLog (2026-11-04): every key sounded ONE frame before its character showed. A key's
    instant T falls between frames, and the register draws the character on the first frame whose t reaches T — the
    ceiling — while the point mirror rounds to the nearest. A strike drawn on a continuous curve is right on the
    nearest frame; a discrete count is not. Simulated here on useT's own formula for every register that types."""
    import math
    import re
    dur, fps = 165, 30
    pad = min(shot_sounds.SEAM_FRAMES, (dur - 1) // 3)
    span = dur - 1 - 2 * pad
    t_of = lambda f: shot_sounds.ENTRY_T + (1 - shot_sounds.ENTRY_T) * min(1.0, max(0.0, (f - pad) / span))
    d = {"kind": "key", "type": "cmd", "at": 0.05, "to": 0.16, "draw": "round"}
    cmd = "build --pipeline"
    shots = os.path.join(_SKILL, "remotion", "src", "shots")
    assert re.search(r"to: 0\.16, draw: 'round'", open(os.path.join(shots, "TermLog.tsx"), encoding="utf-8").read())
    ev = shot_sounds.scene_events({"shot": "TermLog", "props": {"cmd": cmd}, "durF": dur}, fps)
    keys = sorted(round(e["t"] * fps) for e in ev if e["name"] == "key")
    n = len(cmd)
    count = lambda f: math.floor(n * min(1.0, max(0.0, (t_of(f) - 0.05) / 0.11)) + 0.5)
    drawn = [next(f for f in range(dur) if count(f) >= i) for i in range(1, n + 1)]
    typed = [f for f in drawn if f > pad]                 # a character already on the held entry was never typed in view
    assert drawn[0] <= pad < drawn[1], "the case covers a character drawn on the hold"
    assert keys == typed, (keys, typed)


_DEVICE_STEPS = [{"screen": {"page": "a"}, "t0": 0.06, "ta": 0.06, "t1": 0.12},
                 {"tap": [0.5, 0.3], "t0": 0.14, "ta": 0.2, "t1": 0.26},
                 {"type": "hello 世界!", "into": [0.5, 0.4], "t0": 0.3, "ta": 0.32, "t1": 0.55},
                 {"click": [0.2, 0.2], "t0": 0.6, "ta": 0.64, "t1": 0.7},
                 {"mark": [0.4, 0.4], "t0": 0.72, "ta": 0.74, "t1": 0.8}]


def test_a_device_script_keys_each_chunk_and_clicks_each_tap_in_both_runtimes():
    """DeviceDemo types a field in CHUNKS on a jittered rhythm (gesture.typedCount: a Latin key or a two-glyph CJK word
    per commit, each landing at the START of its share of [ta, t1]) and taps on `ta`; the steps' times come from
    device_script.prepare. `step: 'type'` keys each chunk where typedCount reaches it; `step: 'tap'` clicks each tap and
    click (a `mark` is a pointer, not a press). The times are checked against the runtime's own typedCount."""
    import json
    decls = [{"kind": "key", "step": "type"}, {"kind": "click", "step": "tap"}]
    props = {"steps": _DEVICE_STEPS}
    py = [shot_sounds.decl_ts(d, props) for d in decls]
    r = _tsprobe.run_ts("import * as S from %s;\nimport * as G from %s;\n" % (_tsprobe.mod("sound"), _tsprobe.mod("gesture")),
                        "const D = %s; const P = %s;\nout.ts = D.map((d: any) => S.soundTs(d, P));\n"
                        "const st = P.steps[2]; const ch = G.typeChunks(st.type);\n"
                        "const T = %s;\nout.after = T.map((t: number) => G.typedCount(t + 1e-9, st.ta, st.t1, ch));\n"
                        "out.before = T.map((t: number) => G.typedCount(t - 1e-9, st.ta, st.t1, ch));\nout.n = ch.length;"
                        % (json.dumps(decls), json.dumps(props), json.dumps(py[0])))
    assert np.allclose(r["ts"][0], py[0]) and np.allclose(r["ts"][1], py[1])
    assert len(py[0]) == r["n"] == 8, "h,e,l,l,o + space + 世界 as one commit + !"
    # the k-th key is the instant the runtime's count steps from k-1 to k — neither before it nor after
    assert r["after"] == list(range(1, r["n"] + 1)) and r["before"] == list(range(0, r["n"])), (r["before"], r["after"])
    assert py[1] == [0.2, 0.64], "taps and clicks press; a mark does not"
    assert shot_sounds.decl_ts(decls[0], {}) == [] and shot_sounds.decl_ts(decls[1], {"steps": []}) == []
    for bad in ("export const SOUNDS = [{kind: 'key', step: 'swipe', at: 0}];",
                "export const SOUNDS = [{kind: 'key', step: 'type', type: 'x', at: 0}];"):
        with pytest.raises(shot_sounds.SoundDeclError):
            shot_sounds.parse_sounds(bad)


def test_device_demo_declares_its_keys_and_taps():
    decls = shot_sounds.register_sounds("DeviceDemo")
    assert {"kind": "key", "step": "type"} in [{k: v for k, v in d.items() if k != "gain"} for d in decls]
    assert {"kind": "click", "step": "tap"} in [{k: v for k, v in d.items() if k != "gain"} for d in decls]
