import pedagogy_qa as pq


def _plan(beats, assumed_known=None):
    return {"meta": {"assumed_known": assumed_known or []}, "beats": beats}


def test_concept_used_before_introduced_is_error():
    r = pq.evaluate(_plan([
        {"index": 1, "stage": "hook", "introduces": None, "builds_on": []},
        {"index": 2, "stage": "build", "introduces": "gradient descent", "builds_on": ["loss function"]},
    ]))
    assert not r["ok"] and any("before it is introduced" in e for e in r["errors"])


def test_prerequisite_satisfied_ok():
    r = pq.evaluate(_plan([
        {"index": 1, "stage": "ground", "introduces": "loss function", "builds_on": []},
        {"index": 2, "stage": "build", "introduces": "gradient descent", "builds_on": ["loss function"]},
        {"index": 3, "stage": "why", "introduces": None, "builds_on": ["gradient descent"]},
    ]))
    assert r["ok"] and not r["errors"]


def test_assumed_known_satisfies_dependency():
    r = pq.evaluate(_plan([{"index": 1, "stage": "build", "introduces": "x", "builds_on": ["algebra"]}],
                          assumed_known=["algebra"]))
    assert r["ok"]


def test_introduces_list_warns():
    r = pq.evaluate(_plan([{"index": 1, "stage": "build", "introduces": ["a", "b"], "builds_on": []}]))
    assert any("`introduces` is a list" in w for w in r["warnings"])


def test_no_ground_before_first_build_warns():
    r = pq.evaluate(_plan([
        {"index": 1, "stage": "hook", "introduces": None, "builds_on": []},
        {"index": 2, "stage": "build", "introduces": "x", "builds_on": []},
    ]))
    assert any("no `ground`" in w for w in r["warnings"])


def test_build_without_following_why_warns():
    r = pq.evaluate(_plan([
        {"index": 1, "stage": "ground", "introduces": "a", "builds_on": []},
        {"index": 2, "stage": "build", "introduces": "b", "builds_on": ["a"]},
        {"index": 3, "stage": "build", "introduces": "c", "builds_on": ["b"]},
        {"index": 4, "stage": "build", "introduces": "d", "builds_on": ["c"]},
    ]))
    assert any("followed within one beat by a `why`" in w for w in r["warnings"])


def test_check_noops_without_file(tmp_path):
    r = pq.check(str(tmp_path))
    assert r["ok"] and r.get("skipped")


def test_article_and_hyphen_variants_not_false_flagged():
    # 'the Fourier transform' introduces == 'Fourier transform' builds_on; 'k-space' == 'k space'
    r = pq.evaluate(_plan([
        {"index": 1, "stage": "ground", "introduces": "the Fourier transform", "builds_on": []},
        {"index": 2, "stage": "ground", "introduces": "k-space", "builds_on": []},
        {"index": 3, "stage": "build", "introduces": "reconstruction", "builds_on": ["Fourier transform", "k space"]},
    ]))
    assert r["ok"] and not r["errors"]


def test_a_build_beat_that_lands_its_own_consequence_is_not_flagged():
    # one page that reveals the idea and then its implication scaffolds BETTER than splitting the
    # two across pages — but `stage` is one label and cannot say so. Reading only the tag would
    # flag precisely the beats that teach best.
    plan = {"beats": [
        {"stage": "ground", "introduces": "the window", "builds_on": []},
        {"stage": "build", "introduces": "CLAUDE.md", "builds_on": ["the window"],
         "points": ["it is read every session", "so you stop re-explaining the project"]},
        {"stage": "build", "introduces": "skills", "builds_on": ["CLAUDE.md"],
         "lands_within": True},
        {"stage": "land", "introduces": None, "builds_on": ["skills"]},
    ]}
    r = pq.evaluate(plan)
    assert r["ok"] is True
    assert not any("not followed within one beat" in w for w in r["warnings"]), r["warnings"]


def test_a_build_beat_with_a_single_point_still_needs_a_follow_up():
    # the escape hatch must not become a way to silence the check: one point is not a landing
    plan = {"beats": [
        {"stage": "ground", "introduces": "the window", "builds_on": []},
        {"stage": "build", "introduces": "CLAUDE.md", "builds_on": ["the window"],
         "points": ["it is read every session"]},
        {"stage": "build", "introduces": "skills", "builds_on": ["CLAUDE.md"]},
        {"stage": "build", "introduces": "hooks", "builds_on": ["skills"]},
    ]}
    r = pq.evaluate(plan)
    assert any("not followed within one beat" in w for w in r["warnings"])
