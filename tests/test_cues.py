import cues

W = [{"w": "come", "t": 0.3}, {"w": "to", "t": 0.6}, {"w": "dujiangyan", "t": 2.0},
     {"w": "an irrigation system", "t": 3.1}, {"w": "leshan", "t": 6.0}, {"w": "buddha", "t": 6.4}]

def test_matches_in_order():
    assert cues.resolve_cues(W, ["Dujiangyan", "Leshan"]) == [2.0, 6.0]

def test_explicit_phrase_over_label():
    # anchor phrase "irrigation" matches the grouped cue, not the label "Dujiangyan"
    assert cues.resolve_cues(W, ["irrigation", "Leshan"]) == [3.1, 6.0]

def test_missing_anchor_interpolated_between_neighbors():
    r = cues.resolve_cues(W, ["Dujiangyan", "Mahjong", "Leshan"])  # middle not present
    assert r[0] == 2.0 and r[2] == 6.0
    assert 2.0 < r[1] < 6.0                # interpolated midpoint, monotonic

def test_no_match_even_spread():
    r = cues.resolve_cues(W, ["zzz", "qqq", "www"])
    assert len(r) == 3 and all(r[i] < r[i+1] for i in range(len(r)-1)) and all(0 < t < W[-1]["t"] + 1 for t in r)

def test_monotonic_nudge_on_collision():
    w = [{"w": "alpha beta", "t": 1.0}]
    r = cues.resolve_cues(w, ["alpha", "beta"])   # both match the same cue
    assert r[0] == 1.0 and r[1] > r[0]            # second nudged forward

def test_length_and_floats():
    r = cues.resolve_cues(W, ["come", "leshan"])
    assert len(r) == 2 and all(isinstance(x, float) for x in r)

def test_empty():
    assert cues.resolve_cues(W, []) == []
    r = cues.resolve_cues([], ["x"])
    assert len(r) == 1 and isinstance(r[0], float)

def test_zero_time_words_still_monotonic():
    r = cues.resolve_cues([{"w": "x", "t": 0.0}], ["zzz", "qqq"])
    assert len(r) == 2 and r[1] > r[0] and all(isinstance(x, float) for x in r)

def test_multiword_anchor_skips_stopwords():
    w = [{"w": "come", "t": 0.3}, {"w": "an irrigation system", "t": 3.1}, {"w": "leshan", "t": 6.0}]
    assert cues.resolve_cues(w, ["an irrigation system", "leshan"]) == [3.1, 6.0]


def test_estimate_from_text_tracks_char_position():
    # anchors at ~0% and ~50% of a 10s scene -> ~0s and ~5s (uniform-rate assumption)
    narr = "甲一二三四五六七八九"     # 甲 at index 0; each char ~10% of length
    t = cues.estimate_cues_from_text(["甲", "六"], narr, 10.0)
    assert len(t) == 2 and t[0] < 1.0 and 5.0 <= t[1] <= 7.0, t

def test_estimate_from_text_monotonic_and_length():
    narr = "先讲很多铺垫内容然后提到甲随后提到乙最后收尾。"
    t = cues.estimate_cues_from_text(["甲", "乙"], narr, 12.0)
    assert len(t) == 2 and t[0] < t[1]         # spoken order preserved, ascending
    assert all(0 <= x <= 12.0 for x in t)

def test_estimate_from_text_unmatched_interpolates():
    # a missing middle anchor is interpolated between its resolved neighbours (never crashes)
    t = cues.estimate_cues_from_text(["甲", "缺", "乙"], "甲……乙", 6.0)
    assert len(t) == 3 and t[0] <= t[1] <= t[2]


def test_anchor_pos_case_insensitive():
    assert cues._anchor_pos("we really use AI here", "ai") >= 0     # 'ai' matches 'AI'
    assert cues._anchor_pos("MRI reconstruction", "mri") == 0

def test_anchor_pos_whole_word_latin_not_midword():
    assert cues._anchor_pos("we start today", "art") == -1         # NOT inside 'start'
    assert cues._anchor_pos("modern art show", "art") == 7         # standalone word

def test_anchor_pos_cjk_plain_substring():
    assert cues._anchor_pos("公式是真概念现算", "概念") == 4          # CJK: substring, no word gaps

def test_estimate_latin_ignores_midword_and_case():
    # 'AI' is spoken late; must NOT resolve to the 'ai' inside 'brain' near the start
    t = cues.estimate_cues_from_text(["AI"], "the brain is not it, the real ai here is AI.", 10.0)
    assert t[0] > 5.0, t
