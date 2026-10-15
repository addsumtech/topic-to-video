"""scripts/cue_pages.py — proposes data-cue / data-cue-index for an HTML page's revealable text from the narration.
Pinned on a small fixture page and a synthetic words.json (no tts, no Chrome)."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))
import cue_pages as cp  # noqa: E402
import sync_qa as sq  # noqa: E402

NARR = "Alpha engines run hot. Bravo batteries last long. Charlie chargers are cheap."
WORDS = [{"w": w, "t": round(0.5 * i, 2)} for i, w in enumerate(NARR.replace(".", "").split())]
DUR = 8.0


def _plan(page, **kw):
    spoken, _ = sq.spoken_units(NARR, WORDS, DUR)
    return cp.plan_page(page, spoken, WORDS, narration=NARR, **kw)


def _page(*rows):
    return "<html><body><div class='stage'>" + "".join(rows) + "</div></body></html>"


def test_indices_follow_spoken_order_not_document_order():
    page = _page('<div class="reveal-up">Charlie chargers are cheap</div>',
                 '<div class="reveal-up">Alpha engines run hot</div>',
                 '<div class="reveal-up">Bravo batteries last long</div>')
    ins, _un, _ren, els, _d = _plan(page)
    out = cp.apply(page, ins, {}, els)
    by_text = {i["el"]["text"][0]: i["index"] for i in ins}
    assert by_text == {"Alpha engines run hot": 0, "Bravo batteries last long": 1, "Charlie chargers are cheap": 2}
    assert out.index('data-cue-index="2"') < out.index('data-cue-index="0"')      # document order is untouched


def test_an_existing_anchor_is_kept_and_new_ones_slot_around_it():
    page = _page('<div class="reveal-up" data-cue="Bravo" data-cue-index="0">Bravo batteries last long</div>',
                 '<div class="reveal-up">Alpha engines run hot</div>',
                 '<div class="reveal-up">Charlie chargers are cheap</div>')
    ins, _un, ren, els, disputed = _plan(page)
    out = cp.apply(page, ins, ren, els)
    assert 'data-cue="Bravo"' in out and disputed == []        # the author's phrase survives untouched
    assert ren == {0: 1}                                        # Alpha spoke first: Bravo's INDEX shifts, not its phrase
    assert out.count("data-cue=") == 3
    assert 'data-cue="Bravo" data-cue-index="1"' in out


def test_an_unmatched_element_is_reported_and_not_cued():
    page = _page('<div class="reveal-up">Alpha engines run hot</div>',
                 '<div class="reveal-up">Zulu never spoken anywhere</div>')
    ins, un, _ren, els, _d = _plan(page)
    out = cp.apply(page, ins, {}, els)
    assert [i["phrase"] for i in ins] == ["Alpha engines run hot"]
    assert any("Zulu" in t for t, _w in un)
    assert out.count("data-cue-index") == 1 and "Zulu never spoken anywhere</div>" in out
    assert 'class="reveal-up">Zulu' in out                     # the unmatched element's tag is byte-identical


def test_a_late_hand_written_anchor_is_reported_and_only_moved_with_retarget():
    page = _page('<div class="reveal-up" data-cue="Charlie" data-cue-index="0">Alpha engines run hot</div>')
    ins, _un, _ren, _els, disputed = _plan(page)
    assert ins == [] and len(disputed) == 1 and disputed[0][1] == "Charlie"
    ins, _un, ren, els, _d = _plan(page, retarget=True)
    out = cp.apply(page, ins, ren, els)
    assert 'data-cue="Charlie"' not in out and 'data-cue="Alpha' in out


def test_running_it_twice_changes_nothing():
    page = _page('<div class="reveal-up">Alpha engines run hot</div>', '<div class="reveal-up">Bravo batteries last long</div>')
    ins, _un, ren, els, _d = _plan(page)
    once = cp.apply(page, ins, ren, els)
    ins2, _u2, _r2, _e2, _d2 = _plan(once)
    assert ins2 == []


def test_an_element_whose_lines_are_spoken_far_apart_is_split_not_anchored():
    # the skill's own jev-html: a card held the label "JEV" (said at 0.1 s) and its claim (said at 5.3 s); anchoring at
    # the earliest line showed the claim five seconds early. Past LAG_ERROR + EARLY_WARN apart no single reveal can land
    # both, so the tool says SPLIT — for a new element and for a hand-written anchor, with or without --retarget
    narr = "Alpha opens the film. Then a pause. Then more words follow here. Charlie closes it."
    words = [{"w": w, "t": float(i)} for i, w in enumerate(narr.replace(".", "").split())]
    spoken, _ = sq.spoken_units(narr, words, 16.0)
    card = '<div class="reveal-up"%s><span>Alpha opens the film</span><span>Charlie closes it</span></div>'
    ins, un, _ren, _els, _d = cp.plan_page(_page(card % ""), spoken, words, narration=narr)
    assert ins == [] and any("split it" in why and "Alpha" in why for _t, why in un), un
    page = _page(card % ' data-cue="Charlie" data-cue-index="0"')
    for retarget in (False, True):
        ins, _un, _ren, els, disputed = cp.plan_page(page, spoken, words, retarget=retarget, narration=narr)
        assert ins == [] and len(disputed) == 1, (retarget, disputed)
        assert disputed[0][3] is None and "split it" in disputed[0][4], disputed
        assert cp.apply(page, ins, _ren, els).count('data-cue="Charlie"') == 1, "the author's anchor is untouched"
    # lines spoken close together still get one anchor, as before
    near = _page('<div class="reveal-up"><span>Alpha opens the film</span><span>Then a pause</span></div>')
    ins, _un, _ren, _els, _d = cp.plan_page(near, spoken, words, narration=narr)
    assert len(ins) == 1, ins
