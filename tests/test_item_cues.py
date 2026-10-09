"""Per-element cues — an item a register lists reads when the voice names it, where the beat's time warp cannot
reorder (runtime/cue.ts, scripts/sync_qa.py `item_cues` / `attach_cues`, Film.tsx CueContext).

Pinned without a browser: which prop paths are items, which word each lands on, which beats get cues (a register
that imports runtime/cue, never under `sync: "off"` or authored anchors), how the warp treats a cued element, and
that a film's own register is read through its `@runtime/` imports. With the toolchain, on a real Film: every
register that adopted the hook puts each cued item on its cue, never later than its own slot, and keeps it there
under a warp.
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

# the library registers that read cues — each one produced a late ERROR the warp could not reach on a delivered film
ADOPTED = ("OpenQuestions", "TechnicalPlate", "ObjectStage", "PhotoPlate", "KSpaceToPicture")


def _words(text, t_per_char=0.2):
    words, t = [], 0.0
    for m in re.finditer(r"[A-Za-z0-9.]+|\S", text):
        words.append({"w": m.group(0), "t": round(t, 3)})
        t += t_per_char
    return words, t


def _spoken(text, t_per_char=0.2):
    words, t = _words(text, t_per_char)
    units, src = sq.spoken_units(text, words, duration=t + 1)
    assert src == "words"
    return units


def test_item_texts_are_the_prop_paths_a_register_keys_by():
    props = {"caption": "the river", "kicker": "  ", "count": 3, "questions": ["why?", ""],
             "labels": [{"text": "a part", "x": 0.1}, {"x": 0.2}], "parts": [{"n": 1, "label": "the pan"}],
             "marks": [{"label": "bank", "x": 0.5}], "object": {"id": "X", "props": {"title": "nested"}}}
    assert sq.item_texts(props) == [("caption", "the river"), ("questions.0", "why?"), ("labels.0", "a part"),
                                    ("parts.0", "the pan"), ("marks.0", "bank")]


def test_an_item_is_cued_a_breath_before_its_word_and_an_unsaid_one_is_not():
    narr = "外界只能先把问题留着。但它的架构官方至今没公开。"
    spoken = _spoken(narr)
    cues = sq.item_cues({"footer": "外界，只能先把问题留着", "questions": ["它的架构，官方至今没公开", "完全无关的一句话"]},
                        spoken)
    assert set(cues) == {"footer", "questions.0"}
    said_q = narr.index("它的架构") * 0.2
    assert cues["questions.0"] == pytest.approx(said_q - sq.LEAD_S, abs=0.01)
    assert cues["footer"] == 0.0                         # its word is the first one: never a negative second


def _board(shot, props, sync=None, meta_sync=None):
    sl = {"index": 1, "shot": shot, "shot_props": props, "duration": 10.0, "audio": "audio/01.mp3",
          "narration": "外界只能先把问题留着。但它的架构官方至今没公开。"}
    if sync is not None:
        sl["sync"] = sync
    meta = {"renderer": "remotion", "fps": 30}
    if meta_sync is not None:
        meta["sync"] = meta_sync
    return {"meta": meta, "slides": [sl]}


def _props_for(tmp_path, board):
    import render_remotion as rr
    os.makedirs(tmp_path / "audio", exist_ok=True)
    (tmp_path / "audio" / "01.mp3").write_bytes(b"")
    words, _t = _words(board["slides"][0]["narration"])
    (tmp_path / "audio" / "01.words.json").write_text(json.dumps(words, ensure_ascii=False))
    props, _slides = rr.film_props(str(tmp_path), board)
    return props["scenes"][0]


def test_cues_reach_only_a_register_that_reads_them_and_only_while_the_board_leaves_the_clock_alone(tmp_path):
    oq = {"questions": ["它的架构，官方至今没公开"], "footer": "外界，只能先把问题留着"}
    sc = _props_for(tmp_path, _board("OpenQuestions", oq))
    assert set(sc.get("cues") or {}) == {"questions.0", "footer"}
    # a register that does not import runtime/cue keeps its props and its scene exactly as before
    assert "cues" not in _props_for(tmp_path, _board("CinematicTitle", {"title": "外界只能先把问题留着"}))
    # the author's own clock wins: sync off (beat or film) and authored anchors take no cues
    assert "cues" not in _props_for(tmp_path, _board("OpenQuestions", oq, sync="off"))
    assert "cues" not in _props_for(tmp_path, _board("OpenQuestions", oq, meta_sync="off"))
    assert "cues" not in _props_for(tmp_path, _board("OpenQuestions", oq, sync={"anchors": [[3.0, 4.0]]}))


def test_every_adopted_register_imports_the_hook():
    for name in ADOPTED:
        assert sq.register_takes_cues(name), name


def test_a_cued_element_is_neither_an_anchor_nor_moved_by_the_warp():
    fps = 30
    pinned = {"text": "footer", "spoken": 3.0, "appear": 2.95, "lag": -0.05, "cap": 2.9}
    loose = {"text": "loose", "spoken": 8.1, "appear": 6.5, "lag": -1.6, "cap": 8.0}   # its own slot is earlier
    plain = {"text": "plain", "spoken": 6.0, "appear": 9.0, "lag": 3.0}
    assert sq.pinned(pinned) and not sq.pinned(loose) and not sq.pinned(plain)
    knots = [[12, 12], [57, 57], [150, 270], [287, 287]]          # pulls register 270 to film 150 (5.0 s)
    assert sq.moved_appear(pinned, knots, fps) == 2.95            # on its cue whatever the warp does
    assert sq.moved_appear(plain, knots, fps) == pytest.approx(5.0, abs=0.01)
    slow = [[12, 12], [57, 57], [282, 200], [287, 287]]           # slows the register: 6.5 s would land at 9.4 s...
    assert sq.unwarp_frame(6.5 * fps, slow) / fps > 9.0
    assert sq.moved_appear(loose, slow, fps) == 8.0               # ...but a cued item never reads after its cue
    # the derivation never anchors on the pinned element: a beat whose only late item is on its cue needs no warp
    warp, _notes = sq.derive_warp([pinned, dict(pinned, text="other", appear=4.0, spoken=4.0, cap=3.9)], 300, fps, 12)
    assert warp == []


def test_a_census_line_is_capped_by_the_item_that_drew_it():
    scene = {"props": {"questions": ["它的架构，官方至今没公开"], "footer": "外界"}, "cues": {"questions.0": 0.5}}
    recs = [{"text": "它的架构，官方至今", "appear": 0.6}, {"text": "外界", "appear": 7.0}, {"text": "无关", "appear": 1}]
    out = sq.cap_records(recs, scene)
    assert out[0]["cap"] == 0.5                       # a wrapped item is measured line by line
    assert "cap" not in out[1] and "cap" not in out[2]   # an item the scene does not cue carries none


def _workshop_shot(tmp_path, name, imports):
    d = tmp_path / "workshop" / "shots"
    d.mkdir(parents=True, exist_ok=True)
    (d / (name + ".tsx")).write_text("import React from 'react';\n" + imports + "\nexport const %s = () => null;\n" % name)


def test_a_films_own_register_is_read_through_its_runtime_aliases(tmp_path):
    # a workshop register imports `@runtime/...`; a relative-only walk never followed it, so a film's own
    # register on the voice was warped off it, and one adopting the hook was never given cues
    _workshop_shot(tmp_path, "VoiceThing", "import {useVoice} from '@runtime/voice';")
    _workshop_shot(tmp_path, "CuedThing", "import {\n  useCues,\n} from '@runtime/cue';")
    _workshop_shot(tmp_path, "PlainThing", "import {useT} from '@runtime/motion';")
    assert sq.register_exempt("VoiceThing", str(tmp_path))
    assert sq.register_takes_cues("CuedThing", str(tmp_path))
    assert not sq.register_takes_cues("PlainThing", str(tmp_path))
    assert sq.register_exempt("PlainThing", str(tmp_path)) is None


def test_a_new_workshop_register_reads_cues_from_its_first_draft(tmp_path):
    import workshop as ws
    ws.scaffold(str(tmp_path), "shot", "FreshShot", "a test shot")
    assert sq.register_takes_cues("FreshShot", str(tmp_path))
    assert "cue.win('title'" in (tmp_path / "workshop" / "shots" / "FreshShot.tsx").read_text()


def test_the_film_and_the_hook_share_one_warp_map():
    film = open(os.path.join(_ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()
    cue = open(os.path.join(_ROOT, "remotion", "src", "runtime", "cue.ts"), encoding="utf-8").read()
    assert "import {CueContext, warpFrame} from './runtime/cue';" in film
    assert "export const warpFrame" not in film                     # one definition, not two that can drift
    assert "if (!warp || warp.length < 2 || f <= warp[0][0] || f >= warp[warp.length - 1][0]) return f;" in cue
    m = re.search(r"<CueContext\.Provider value=\{sc\.cues \? \{at: sc\.cues, warp: sc\.warp \?\? null\} : null\}>"
                  r"\s*<BeatClock warp=\{sc\.warp\}>", film)
    assert m, "the cues must reach the register with the SAME warp BeatClock applies"


# ── on a real Film ────────────────────────────────────────────────────────────────────────────────────────────
import _tsprobe  # noqa: E402

needs_toolchain = pytest.mark.skipif(not _tsprobe.available(), reason="needs the remotion toolchain")
D = 300                     # 10 s beats


def _scenes():
    import register_energy as _re
    _re.ensure_fixture()
    ev = _re.evidence_props()
    return [
        ("OpenQuestions", {"questions": ["Who decides first", "What does it cost", "Where does it end"],
                           "footer": "left open for now"}),
        ("TechnicalPlate", {}),
        ("ObjectStage", {"labels": [{"text": "upper hinge", "x": 0.3, "y": 0.3},
                                    {"text": "lower latch", "x": 0.7, "y": 0.7}],
                         "title": "the whole device", "note": "one line under it"}),
        ("PhotoPlate", dict(ev.get("PhotoPlate") or {}, caption="the far bank",
                            marks=[{"label": "the bridge", "x": 0.3, "y": 0.4}])),
        ("KSpaceToPicture", {"kspaceLabel": "k-space", "kspaceNote": "one row per shot", "imageLabel": "image",
                             "imageNote": "sharper as rows fill"}),
    ]


def _film(scenes):
    return {"scenes": scenes, "camera": 0, "cameraBed": False, "reducedMotion": False, "aspect": "16:9",
            "captions": False, "dna": "product", "typeGlide": True}


def _readable(frames, beat):
    """{line text: first readable frame} for one beat's register."""
    first = {}
    for f in sorted(frames):
        for ln in frames[f].get("lines") or []:
            if ln.get("b") == beat and sq._readable(ln) and ln["t"] not in first:
                first[ln["t"]] = f
    return first


def _when(first, text):
    hits = [f for t, f in first.items() if text in t or (len(t) >= 4 and t in text)]
    return min(hits) if hits else None


@pytest.fixture(scope="module")
def census():
    import text_safe_qa as tq
    import workshop as _ws
    regs = _scenes()
    # cue every item early, staggered through the beat's first seconds — one inside the entry hold (0.2 s)
    cued, plain = [], []
    for k, (shot, props) in enumerate(regs):
        items = [key for key, _t in sq.item_texts(props) if key != "src"]   # a file name is never said
        if shot == "TechnicalPlate":
            items = ["parts.0", "parts.1", "object"]              # its demo: two callouts and the object's name
        cues = {key: round(0.2 + 1.1 * i, 3) for i, key in enumerate(items)}
        sc = {"shot": shot, "props": props, "durF": D, "caption": ""}
        plain.append(dict(sc))
        cued.append(dict(sc, cues=cues))
    warped = [dict(sc, warp=[[12, 12], [57, 57], [150, 200], [287, 287]]) for sc in cued]
    work = tempfile.mkdtemp(prefix="cue_test_")
    try:
        bundle = tq.glide_bundle(os.path.join(work, "bundle"), None, _ws.prepare(None))
        res = tq.glide_run([{"tag": "plain", "id": "Film", "props": _film(plain)},
                            {"tag": "cued", "id": "Film", "props": _film(cued)},
                            {"tag": "warped", "id": "Film", "props": _film(warped)}], bundle)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for tag in ("plain", "cued", "warped"):
        assert res[tag]["done"] and not res[tag]["error"], (tag, res[tag]["error"])
    return regs, cued, warped, res


def _beat_frames(res, k):
    """The Film census, re-based on beat k's own clock (Film.tsx overlaps beats by one seam)."""
    import remotion_segments as rs
    segs, _total = rs.timeline([{"durF": D}] * 5, rs.seam_frames())
    a = segs[k][0]
    return {f - a: v for f, v in res["frames"].items() if f >= a}


@needs_toolchain
@pytest.mark.parametrize("k", range(5), ids=[n for n in ADOPTED])
def test_each_adopted_register_puts_a_cued_item_on_its_cue(census, k):
    regs, cued, warped, res = census
    shot, props = regs[k]
    texts = dict(sq.item_texts(props))
    if shot == "TechnicalPlate":
        texts = {"parts.0": "the part that does the work", "parts.1": "the part that steers", "object": "the object"}
    plain = _readable(_beat_frames(res["plain"], k), str(k))
    got = _readable(_beat_frames(res["cued"], k), str(k))
    under_warp = _readable(_beat_frames(res["warped"], k), str(k))
    moved = 0
    for key, cue_s in cued[k]["cues"].items():
        text = texts[key]
        p, g, w = _when(plain, text), _when(got, text), _when(under_warp, text)
        assert p is not None and g is not None and w is not None, (shot, key, text, sorted(got))
        assert g <= p + 1, (shot, key, "a cue never makes an item LATER", p, g)
        cue_f = cue_s * 30
        if p > cue_f + 10:                                  # its own slot is late: the cue must bring it in
            moved += 1
            # reads on its word: no later than a third of a second after it, no earlier than a second before
            # (the floor shortens a window whose word falls inside the entry hold, so even 0.2 s reads by ~0.8 s)
            late_ok = max(cue_f, 12 + 0.3 * 30) + 10
            assert cue_f - 30 <= g <= late_ok, (shot, key, "cue at frame %.0f, reads at %d (slot %d)" % (cue_f, g, p))
            # ...and it is converted through the warp: still on its cue when the register's clock is warped
            assert abs(w - g) <= 3, (shot, key, "warped %d vs unwarped %d" % (w, g))
    assert moved, (shot, "the fixture cued nothing earlier than the register's own slots — it tests nothing")
