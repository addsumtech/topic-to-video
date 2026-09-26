"""Which tier, for what — the recommendation follows the PURPOSE first and the TOPIC second.

The tier question used to be asked as a choice between three looks, with nothing tying it to what the video
is for. These pin the rule on both sides: what each purpose gets, what the topic decides when the purpose
does not, what degrades when a tier cannot run, and — the one that shipped broken first — that the note
reaches a REMOTION board at all.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import tier_advice as ta          # noqa: E402


# ── what each purpose gets ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("purpose,tier", [
    ("teach", "html"), ("howto", "html"), ("research", "html"),
    ("launch", "remotion"), ("promo", "remotion"),
])
def test_a_purpose_that_decides_the_tier_on_its_own(purpose, tier):
    assert ta.recommend(purpose)["tier"] == tier


def test_the_table_and_the_function_agree_for_every_purpose():
    """A purpose added to the table later must not be answered by a different rule in the function."""
    for p, want in ta.PURPOSE_TIER.items():
        got = ta.recommend(p, data_dense=True)["tier"]
        assert got == (want or "html"), (p, want, got)


@pytest.mark.parametrize("purpose", ["pitch", "overview"])
def test_when_the_purpose_does_not_decide_the_topic_does(purpose):
    """Evidence-heavy material needs the layout to follow the content; a story needs the shot language. And
    an UNASSESSED topic says so in its basis instead of pretending it was measured."""
    assert ta.recommend(purpose, data_dense=True)["tier"] == "html"
    assert ta.recommend(purpose, data_dense=False)["tier"] == "remotion"
    r = ta.recommend(purpose)
    assert r["tier"] == "html" and "topic-unassessed" in r["basis"], r


# ── the interview's own spellings ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("label,key", [
    ("Teach / explain", "teach"), ("How-to / walkthrough", "howto"), ("Research briefing", "research"),
    ("Overview/intro", "overview"), ("Pitch/persuade", "pitch"), ("Launch/announcement", "launch"),
    ("Promo/hype", "promo"), ("操作演示", "howto"), ("讲解", "teach"), ("发布会", "launch"),
])
def test_every_menu_label_resolves(label, key):
    assert ta.canonical_purpose(label) == key


def test_an_ambiguous_label_is_not_resolved_by_list_order():
    """"product demo launch" holds a how-to alias AND a launch alias. First-match would answer a question the
    user did not answer; it must come back unknown, and the advice must say the purpose was unknown."""
    assert ta.canonical_purpose("product demo launch") is None
    assert ta.recommend("product demo launch")["basis"] == "purpose:unknown"


# ── what degrades when a tier cannot run ───────────────────────────────────────────────────────────────
def test_a_deck_the_user_wants_voiced_as_it_is_gets_its_own_slides():
    r = ta.recommend("teach", has_deck=True, keep_deck=True)
    assert r["tier"] == "slides" and r["basis"] == "keep-deck", r


def test_keep_deck_without_a_deck_is_not_the_slides_tier():
    """There is nothing to keep. The flag alone must not route to a tier with no frames to render."""
    assert ta.recommend("teach", has_deck=False, keep_deck=True)["tier"] == "html"


def test_no_chrome_never_recommends_a_page_tier_that_cannot_render():
    assert ta.recommend("teach", has_deck=True, chrome_ok=False)["tier"] == "slides"
    r = ta.recommend("teach", has_deck=False, chrome_ok=False)
    assert r["basis"] == "no-chrome", r


def test_a_launch_on_a_machine_without_remotion_says_why_it_fell_back():
    r = ta.recommend("launch", remotion_ok=False)
    assert r["tier"] == "html" and "remotion-missing" in r["basis"], r


# ── the note, both directions ──────────────────────────────────────────────────────────────────────────
def _board(renderer, purpose, typ):
    return {"meta": {"language": "zh", "renderer": renderer, "purpose": purpose},
            "slides": [{"index": i + 1, "type": typ} for i in range(3)]}


@pytest.mark.parametrize("renderer,purpose,typ,fires", [
    ("remotion", "howto", "slide", True),       # an explainer that cannot reveal on the spoken word
    ("remotion", "research", "slide", True),
    ("local", "launch", "html", True),          # a launch without the shot language
    ("local", "promo", "slide", True),          # ...or voiced straight off the deck
    ("remotion", "launch", "slide", False),     # fits
    ("local", "teach", "html", False),          # fits
    ("local", "pitch", "html", False),          # the topic decides pitch; the note does not second-guess it
])
def test_the_note_fires_exactly_when_the_tier_fights_the_purpose(renderer, purpose, typ, fires):
    note = ta.mismatch(_board(renderer, purpose, typ))
    assert bool(note) is fires, (renderer, purpose, note)


def test_no_recorded_purpose_means_no_note():
    """A board from before `meta.purpose` existed must not be lectured about a purpose it never stated."""
    b = _board("remotion", None, "slide")
    del b["meta"]["purpose"]
    assert ta.mismatch(b) is None


# ── and it reaches a REMOTION board, which is the case it first could not see ──────────────────────────
def test_validate_surfaces_the_note_on_a_remotion_board():
    """THE REGRESSION. The check was first written at the end of `validate.evaluate`, and a remotion board
    returns early from that function — so the costliest mismatch, a how-to on the cinematic tier, was the
    one case it could never report. It now runs before the tier split; this holds it there."""
    import validate as v
    board = {"meta": {"language": "zh", "renderer": "remotion", "purpose": "howto"},
             "slides": [{"index": 1, "type": "slide", "image": "frames/01.png", "shot": "TermTable",
                         "narration": "一句话。", "duration": 4.0}]}
    r = v.evaluate(board, _HERE)
    notes = [w for w in r["warnings"] if w.startswith("tier:")]
    assert notes, ("a how-to on the cinematic tier produced no tier note — the check is behind the remotion "
                   "early return again. Warnings: %r" % r["warnings"][:6])


# ── the topic measure ──────────────────────────────────────────────────────────────────────────────────
def test_data_density_reads_the_material_and_declines_on_too_little():
    assert ta.data_density(["营收 12%", "成本下降 3.4 倍", "2025 年 165 次", "毛利 41%"]) is True
    assert ta.data_density(["这是一个关于信任的故事", "她最后选择了离开", "我们都记得那个夏天"]) is False
    assert ta.data_density(["只有", "两句"]) is None


# ── the 原样配音 tier must not be told to redesign itself ──────────────────────────────────────────────
def _warnings_for(slides):
    import validate as v
    return v.evaluate({"meta": {"language": "zh", "captions": False}, "slides": slides}, _HERE)["warnings"]


def test_a_deck_voiced_as_it_is_is_not_told_to_vary_its_visual_type():
    """Found by rendering the tier end to end the first time it existed: every scene is the user's own slide
    BY DESIGN, and "3+ consecutive 'slide' scenes — vary the visual type (anti-slop)" told them to redesign
    the deck they had asked to keep. A slide's variety lives in its picture, which the board cannot see —
    the same reason the rule already exempted html and cinematic scenes."""
    slides = [{"index": i + 1, "type": "slide", "image": "x.png", "narration": "一句话。"} for i in range(4)]
    assert not [w for w in _warnings_for(slides) if "consecutive 'slide'" in w]


def test_the_anti_slop_rule_still_fires_where_it_applies():
    """The other side: three identical PROGRAMMATIC scenes are exactly what the rule exists for, and
    exempting slides must not have quietly exempted everything."""
    slides = [{"index": i + 1, "type": "keypoints",
               "props": {"points": [{"label": "第一点"}, {"label": "第二点"}]}, "narration": "一句。"}
              for i in range(3)]
    ws = _warnings_for(slides)
    assert [w for w in ws if "consecutive 'keypoints'" in w], ws


def test_a_long_slide_gets_advice_the_user_can_act_on(tmp_path):
    """A user's own slide cannot be split into shorter beats; its narration can be trimmed. Same threshold,
    the actionable move. The files must EXIST: the hold branch sits behind the missing-audio error, and a
    first draft of this test used paths that did not exist and so never reached the branch it names."""
    import validate as v
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"\0")
    (tmp_path / "x.png").write_bytes(b"\0")
    long_slide = [{"index": 1, "type": "slide", "image": "x.png", "narration": "一句话。", "duration": 12.0,
                   "audio": "audio/01.mp3"}]
    ws = v.evaluate({"meta": {"language": "zh", "captions": False}, "slides": long_slide},
                    str(tmp_path))["warnings"]
    hold = [w for w in ws if "12.0s" in w]
    assert hold and "trim the narration" in hold[0] and "can't be split" in hold[0], ws
