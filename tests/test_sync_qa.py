"""Does on-screen text appear when the narration says it? — the sync audit (scripts/sync_qa.py) and the remotion
tier's time warp that acts on it (Film.tsx BeatClock).

The reader is pinned on synthetic census frames; the warp's choice on synthetic measurements; and, with the
toolchain, the whole loop on a real Film: a warp must move a register's entrance to the frame it predicts, and
leave an unwarped beat exactly as it was.
"""
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, _HERE)
import sync_qa as sq  # noqa: E402


def _spoken(text, t_per_char=0.2):
    """Narration units timed one CJK char / Latin word per `t_per_char` seconds (no tts needed)."""
    words, t = [], 0.0
    for m in re.finditer(r"[A-Za-z0-9.]+|\S", text):
        words.append({"w": m.group(0), "t": round(t, 3)})
        t += t_per_char
    units, src = sq.spoken_units(text, words, duration=t + 1)
    assert src == "words"
    return units


def _samples(tracks, fps=30, n=None):
    """[(t, lines)] from {key: [(frame, text, opacity, visible)]}."""
    frames = {}
    for k, pts in tracks.items():
        for f, text, o, v in pts:
            line = {"k": k, "t": text, "o": o}
            if v < 1:
                line["v"] = v
            frames.setdefault(f, []).append(line)
    last = max(frames) if n is None else n
    return [(f / float(fps), frames.get(f, [])) for f in range(last + 1)]


def _on(key, text, start, end, o=1.0, v=1.0):
    return {key: [(f, text, o, v) for f in range(start, end)]}


# ── matching ──────────────────────────────────────────────────────────────────────────────────────────────────
def test_chinese_numerals_meet_digits():
    tu = sq.units("约 962 平方公里")
    hit = sq.best_match(tu, _spoken("今天建成区有九百六十二平方公里"))
    assert hit is not None
    s0, L, t0 = hit
    assert [u[1] for u in tu[t0:t0 + L]] == ["962", "平", "方", "公", "里"]


def test_a_lone_yi_or_a_bare_multiplier_is_a_word_not_a_number():
    assert [u[0] for u in sq.units("一枚")] == ["c", "c"]
    assert [u[0] for u in sq.units("万一")] == ["c", "c"]
    assert sq.units("零点零四二")[0][:2] == ("n", "0.042")


def test_a_particle_and_one_content_character_is_not_a_mention():
    # 「松散的粉」 against 「磨好的粉」 shares only 的粉 — it matched, and the label read 6 s late
    assert sq.best_match(sq.units("松散的粉"), _spoken("磨好的粉倒进手柄的滤碗")) is None


def test_a_lone_digit_needs_company():
    assert sq.best_match(sq.units("3"), _spoken("第3步")) is None
    assert sq.best_match(sq.units("3 步"), _spoken("第3步")) is not None


def test_latin_words_fold_plurals_and_skip_stop_words():
    sp = _spoken("then the signal decays quickly")
    assert sq.best_match(sq.units("Signals"), sp) is not None
    assert sq.best_match(sq.units("the"), sp) is None


def test_the_mention_with_more_of_the_element_nearby_wins():
    # 二线关 is said at the start AND in the sentence that also says 2018 and 撤 — the label is about the second
    sp = _spoken("一直长过了二线关关口成了堵点所以特区扩到了全市2018年二线关也撤了")
    s0, _L, _t0 = sq.best_match(sq.units("2018 · 二线关撤销"), sp)
    assert sp[s0][4] > 3.0, sp[s0]


def test_a_long_line_sharing_one_term_is_not_the_voice_saying_it():
    credit = "原图：511KeV · CC BY-SA 4.0 · Wikimedia Commons；k 空间与逐步重建由该图傅里叶变换计算（示意）"
    sp = _spoken("做一次傅里叶变换频率被翻译回位置")
    samples = _samples(_on("/a", credit, 0, 30))
    assert sq.measure_beat(samples, sp) == []


def test_digits_on_screen_meet_a_normalised_voice():
    # edge-tts speaks "1.5" as 一点五 and reports THOSE tokens; the board's narration still holds the digits
    words = [{"w": "场强", "t": 0.0}, {"w": "一点五", "t": 0.6}, {"w": "特斯拉", "t": 1.4}]
    units, src = sq.spoken_units("场强1.5特斯拉", words, duration=3)
    assert src == "words"
    hit = sq.best_match(sq.units("1.5 T"), units) or sq.best_match(sq.units("1.5 特斯拉"), units)
    assert hit is not None and 0.5 <= units[hit[0]][4] <= 1.5


def test_no_word_times_falls_back_to_text_position():
    units, src = sq.spoken_units("前半句很长很长很长，后半句说磁场", [], duration=10)
    assert src == "text"
    s0, _L, _t0 = sq.best_match(sq.units("磁场"), units)
    assert units[s0][4] > 5.0


# ── appearance ────────────────────────────────────────────────────────────────────────────────────────────────
def test_appear_is_the_first_readable_frame():
    sp = _spoken("这叫进动", t_per_char=0.1)     # 进动 at 0.2 s
    tracks = _on("/a", "进动", 0, 30, o=0.3)
    tracks["/a"] += [(f, "进动", 1.0, 1.0) for f in range(30, 60)]
    [rec] = sq.measure_beat(_samples(tracks), sp)
    assert rec["appear"] == 1.0 and rec["spoken"] == pytest.approx(0.2) and sq.level(rec) == "warn"


def test_half_hidden_by_a_mask_is_not_yet_readable():
    sp = _spoken("这叫进动")
    tracks = {"/a": [(f, "进动", 1.0, 0.2) for f in range(0, 30)] + [(f, "进动", 1.0, 1.0) for f in range(30, 60)]}
    [rec] = sq.measure_beat(_samples(tracks), sp)
    assert rec["appear"] == 1.0


def test_a_typing_line_appears_when_it_holds_the_words():
    sp = _spoken("压粉器把它压实压平")
    full = "压实压平，水才走得匀"
    tracks = {"/a": [(f, full[:1 + f // 3], 1.0, 1.0) for f in range(0, 30)] + [(f, full, 1.0, 1.0)
                                                                                 for f in range(30, 40)]}
    [rec] = sq.measure_beat(_samples(tracks), sp)
    assert rec["text"] == full and rec["appear"] == pytest.approx(9 / 30.0)    # 压实压平 complete on frame 9


def test_an_element_is_its_text_not_its_dom_slot():
    # the same DOM path first shows one label, then — after a sibling mounts — another; the second label is
    # also drawn under a NEW path later. It must appear when it first does, under either path.
    sp = _spoken("二线关撤销了")
    tracks = {"/a": [(f, "二线关", 1.0, 1.0) for f in range(0, 30)] + [(f, "2018 · 二线关撤销", 1.0, 1.0)
                                                                         for f in range(30, 60)],
              "/b": [(f, "2018 · 二线关撤销", 1.0, 1.0) for f in range(60, 90)]}
    recs = {r["text"]: r for r in sq.measure_beat(_samples(tracks), sp)}
    assert recs["2018 · 二线关撤销"]["appear"] == 1.0


def test_levels():
    def lv(lag):
        return sq.level({"lag": lag})
    assert [lv(x) for x in (0.0, 0.6, 0.61, 1.5, 1.51, -3.0, -3.01)] == \
        ["ok", "ok", "warn", "warn", "error", "ok", "early"]


def test_census_lines_belong_to_the_beat_whose_register_drew_them():
    import text_safe_qa as tq
    frames = {f: {"lines": [{"k": "/cap", "t": "caption words", "o": 1},                 # no beat: the caption
                            {"k": "/r", "t": "label", "o": 1, "b": "0" if f < 100 else "1"}]}
              for f in range(0, 200, 10)}
    got = tq.beat_samples(frames, [(0, 99), (88, 199)], 30)
    assert all(ln["t"] == "label" for _t, ls in got[0] + got[1] for ln in ls)
    assert got[1][0][0] == pytest.approx((100 - 88) / 30.0)                # beat 1's own clock starts at 88


# ── the warp ──────────────────────────────────────────────────────────────────────────────────────────────────
FPS = 30
SEAM = 12


def _rec(text, appear, spoken):
    return {"text": text, "said": text, "appear": appear, "spoken": spoken, "lag": round(appear - spoken, 3)}


def test_nothing_to_align_is_the_identity():
    assert sq.derive_warp([_rec("a", 3.0, 3.1), _rec("b", 6.0, 6.2)], 300, FPS, SEAM)[0] == []
    assert sq.derive_warp([], 300, FPS, SEAM)[0] == []


def test_a_late_entrance_is_moved_onto_its_word():
    recs = [_rec("label", 6.0, 4.0)]
    knots, _ = sq.derive_warp(recs, 360, FPS, SEAM)
    assert knots
    landed = sq.unwarp_frame(6.0 * FPS, knots) / FPS
    assert landed == pytest.approx(4.0 - sq.LEAD_S, abs=0.05)


def test_an_entrance_too_late_to_reach_is_moved_as_far_as_the_slope_allows():
    # 8 s of register before 3.9 s of film would need 3x speed: it goes at SLOPE_MAX, and lands later than asked
    recs = [_rec("label", 8.0, 4.0)]
    knots, _ = sq.derive_warp(recs, 360, FPS, SEAM)
    landed = sq.unwarp_frame(8.0 * FPS, knots) / FPS
    open_s = (sq._pad(360, SEAM) + sq.OPENING_S * FPS) / FPS
    assert landed == pytest.approx(open_s + (8.0 - open_s) / sq.SLOPE_MAX, abs=0.02)
    assert 4.0 < landed < 8.0


def test_every_segment_stays_inside_the_slope_limits_and_the_holds_are_untouched():
    recs = [_rec("a", 11.0, 2.0), _rec("b", 12.0, 3.0), _rec("c", 13.0, 12.5)]
    D = 420
    knots, _ = sq.derive_warp(recs, D, FPS, SEAM)
    assert knots and sq.check_knots(knots, D) == []
    pad = sq._pad(D, SEAM)
    assert knots[0] == [pad, pad] and knots[-1] == [D - 1 - pad, D - 1 - pad]
    for f in list(range(0, pad + 1)) + list(range(D - 1 - pad, D)):
        assert sq.warp_frame(f, knots) == f


def test_the_opening_composition_is_never_stretched():
    recs = [_rec("title", 0.5, 9.0), _rec("late", 9.0, 5.0)]
    knots, _ = sq.derive_warp(recs, 360, FPS, SEAM)
    open_f = sq._pad(360, SEAM) + sq.OPENING_S * FPS
    for f in range(0, int(open_f) + 1):
        assert sq.warp_frame(f, knots) == pytest.approx(f)


def test_the_chosen_warp_is_never_worse_than_none():
    import random
    rng = random.Random(7)
    for _ in range(60):
        recs = [_rec("x%d" % i, rng.uniform(0, 14), rng.uniform(0, 14)) for i in range(rng.randint(1, 7))]
        knots, _ = sq.derive_warp(recs, 450, FPS, SEAM)
        assert sq.warp_cost(recs, knots, FPS) <= sq.warp_cost(recs, [], FPS) + 1e-9
        if knots:
            assert sq.check_knots(knots, 450) == []


def test_unwarp_inverts_warp():
    knots = [[12, 12], [57, 57], [140, 280], [330, 330]]
    for f in (20, 60, 100, 139, 200, 329):
        assert sq.unwarp_frame(sq.warp_frame(f, knots), knots) == pytest.approx(f)


def test_an_authored_warp_outside_the_limits_is_refused_not_clamped():
    with pytest.raises(RuntimeError):
        sq.authored_warp([[1.0, 8.0]], 300, SEAM)              # 8 s of register in 1 s of film
    knots = sq.authored_warp([[4.0, 6.0]], 300, SEAM)
    assert knots[1] == [120.0, 180.0]


def test_the_sync_setting_is_read_and_a_bad_one_refused():
    assert sq._sync_setting({}, {"sync": "off"}) == "off"
    assert sq._sync_setting({"sync": "off"}, {}) == "off"
    assert sq._sync_setting({}, {"sync": {"anchors": [[1, 2]]}}) == [[1, 2]]
    assert sq._sync_setting({}, {}) is None
    with pytest.raises(RuntimeError):
        sq._sync_setting({}, {"sync": "sometimes"})


def test_registers_on_the_voice_or_a_recording_are_exempt():
    assert sq.register_exempt("VoiceSignal") and sq.register_exempt("DeviceDemo")
    assert sq.register_exempt("ObjectStage") is None


def test_a_beat_timed_by_cue_props_is_its_authors():
    assert sq.has_cue_props({"at": {"cue": "开始"}})
    assert sq.has_cue_props({"steps": [{"at": {"cue": "开始"}}]})
    assert not sq.has_cue_props({"title": "x"})


def test_the_warp_is_not_part_of_its_own_key():
    # a scene that already CARRIES its warp must key exactly as the un-warped scene it was derived from —
    # otherwise attaching a warp makes it stale, the render re-derives and drops it (it shipped unwarped once)
    sc = {"shot": "ObjectStage", "props": {"a": 1}, "durF": 300}
    k0 = sq.warp_key(sc, {"dna": "x"}, [{"w": "a", "t": 0}], "code")
    k1 = sq.warp_key(dict(sc, warp=[[12, 12], [100, 150], [287, 287]]), {"dna": "x"}, [{"w": "a", "t": 0}], "code")
    assert k0 == k1
    assert sq.warp_key(dict(sc, durF=301), {"dna": "x"}, [{"w": "a", "t": 0}], "code") != k0


def test_attaching_twice_keeps_the_warp(tmp_path):
    import render_remotion as rr
    board = {"meta": {"renderer": "remotion", "fps": 30},
             "slides": [{"index": 1, "shot": "ObjectStage", "shot_props": {}, "duration": 10.0,
                         "audio": "audio/01.mp3", "narration": "一二三"}]}
    os.makedirs(tmp_path / "audio")
    (tmp_path / "audio" / "01.mp3").write_bytes(b"")
    props, slides = rr.film_props(str(tmp_path), board)
    import remotion_segments as rs
    sc = props["scenes"][0]
    key = sq.warp_key(sc, sq._film_rest(props), sq.words_for(str(tmp_path), slides[0]), rs.code_hash(str(tmp_path)))
    warp = [[12, 12], [57, 57], [100, 150], [287, 287]]
    (tmp_path / sq.SIDECAR).write_text(json.dumps({"beats": {"1": {"key": key, "warp": warp, "notes": []}}}))
    props, slides = rr.film_props(str(tmp_path), board)
    assert props["scenes"][0].get("warp") == warp
    plan = sq.attach_warps(str(tmp_path), board, props, slides)      # a second attach, as the render does
    assert plan[0][0] == "derived" and props["scenes"][0].get("warp") == warp


def test_film_wraps_the_register_and_not_the_voice():
    src = open(os.path.join(_ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    m = re.search(r"<BeatClock warp=\{sc\.warp\}>(.*?)</BeatClock>", src, re.S)
    assert m and "<C " in m.group(1) and "Audio" not in m.group(1)
    assert re.search(r"<Audio src=\{staticFile\(sc\.mp3\)\} />", src)
    # the runtime map and the python one are the same map (it lives in runtime/cue, which Film imports)
    cue = open(os.path.join(_ROOT, "remotion", "src", "runtime", "cue.ts"), encoding="utf-8").read()
    assert "if (!warp || warp.length < 2 || f <= warp[0][0] || f >= warp[warp.length - 1][0]) return f;" in cue


# ── the census, on a real Film ────────────────────────────────────────────────────────────────────────────────
import _tsprobe  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")


@pytest.fixture(scope="module")
def film_bundle():
    import text_safe_qa as tq
    import workshop as _ws
    work = tempfile.mkdtemp(prefix="sync_test_")
    try:
        yield tq.glide_bundle(os.path.join(work, "bundle"), None, _ws.prepare(None))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _first_readable(frames, beat="0"):
    first = {}
    for f in sorted(frames):
        for ln in frames[f].get("lines") or []:
            if ln.get("b") == beat and sq._readable(ln) and ln["t"] not in first:
                first[ln["t"]] = f
    return first


@needs_toolchain
def test_a_warp_moves_the_registers_entrance_to_the_frame_it_predicts(film_bundle):
    import text_safe_qa as tq
    D = 240

    def film(warp=None):
        sc = {"shot": "OpenQuestions", "props": {}, "durF": D, "caption": ""}
        if warp:
            sc["warp"] = warp
        return {"scenes": [sc], "camera": 0, "cameraBed": False, "reducedMotion": False, "aspect": "16:9",
                "captions": False, "dna": "product", "typeGlide": True}
    raw = tq.glide_run([{"tag": "raw", "id": "Film", "props": film()}], film_bundle)["raw"]
    assert raw["done"] and not raw["error"], raw["error"]
    first = _first_readable(raw["frames"])
    assert first, "the census listed no type for the register (data-beat missing?)"
    # the caption and chrome carry no beat: only the register's own lines are attributed
    text, g = max(first.items(), key=lambda kv: kv[1])
    pad = sq._pad(D, 12)
    assert g > pad + 20, (text, g)
    last = D - 1 - pad                                      # the earliest film frame both segments allow
    lo = max(pad + (g - pad) / sq.SLOPE_MAX, last - (last - g) / sq.SLOPE_MIN)
    assert lo < g - 10, (lo, g)
    target = (lo + g) / 2.0
    warp = [[pad, pad], [round(target, 3), g], [D - 1 - pad, D - 1 - pad]]
    assert sq.check_knots(warp, D) == []
    got = tq.glide_run([{"tag": "w", "id": "Film", "props": film(warp)}], film_bundle)["w"]
    moved = _first_readable(got["frames"])[text]
    assert abs(moved - sq.unwarp_frame(g, warp)) <= 1.0, (text, g, moved, sq.unwarp_frame(g, warp))
    # every frame inside the held edges is the register's own frame: identical census there
    for f in list(range(0, pad + 1)) + list(range(D - 1 - pad, D)):
        strip = lambda r: sorted((ln["k"], ln["t"], ln["o"], ln["y"]) for ln in r.get("lines") or [])
        assert strip(raw["frames"][f]) == strip(got["frames"][f]), f


def test_a_census_that_fails_renders_unwarped_and_says_so(tmp_path, monkeypatch):
    import render_remotion as rr
    import text_safe_qa as tq
    board = {"meta": {"renderer": "remotion", "fps": 30},
             "slides": [{"index": 1, "shot": "ObjectStage", "shot_props": {}, "duration": 10.0,
                         "audio": "audio/01.mp3", "narration": "一二三"}]}
    os.makedirs(tmp_path / "audio")
    (tmp_path / "audio" / "01.mp3").write_bytes(b"")
    props, slides = rr.film_props(str(tmp_path), board)

    def boom(*a, **k):
        raise RuntimeError("the census bundle failed: probe")
    monkeypatch.setattr(tq, "scan_film_sync", boom)
    said = []
    plan = sq.derive_warps(str(tmp_path), board, props, slides, log=said.append)
    assert plan[0][0] == "needed" and "warp" not in props["scenes"][0]
    assert said and "could not measure" in said[0] and "probe" in said[0]
