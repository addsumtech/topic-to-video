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
    assert len(r) == 3 and r == sorted(r) and all(0 < t < W[-1]["t"] + 1 for t in r)

def test_monotonic_nudge_on_collision():
    w = [{"w": "alpha beta", "t": 1.0}]
    r = cues.resolve_cues(w, ["alpha", "beta"])   # both match the same cue
    assert r[0] == 1.0 and r[1] > r[0]            # second nudged forward

def test_length_and_floats():
    r = cues.resolve_cues(W, ["come", "leshan"])
    assert len(r) == 2 and all(isinstance(x, float) for x in r)

def test_empty():
    assert cues.resolve_cues(W, []) == [] and cues.resolve_cues([], ["x"])  # no crash
