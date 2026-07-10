import brief_qa as bq


def _brief(**over):
    b = {
        "thesis": "Caching cuts p99 latency by 30% via reuse",
        "mechanism": "Because the cache serves the hot path, recompute is avoided and latency therefore drops.",
        "evidence": [{"claim": "30% cut", "source_ref": "Fig 3"}],
        "why_it_matters": "At scale it saves both cost and user-visible lag.",
        "the_one_thing": "Cache the hot path.",
        "misconceptions": ["it is not a rewrite"],
        "source_health": {"status": "coherent", "conflicts": []},
    }
    b.update(over)
    return b


def test_full_brief_ok():
    assert bq.evaluate(_brief())["ok"]


def test_missing_key_is_error():
    b = _brief(); del b["mechanism"]
    r = bq.evaluate(b)
    assert not r["ok"] and any("mechanism" in e for e in r["errors"])


def test_the_one_thing_plural_is_error():
    r = bq.evaluate(_brief(the_one_thing="Cache it. Also index it."))
    assert not r["ok"] and any("the_one_thing" in e for e in r["errors"])


def test_the_one_thing_list_is_error():
    assert not bq.evaluate(_brief(the_one_thing=["a", "b"]))["ok"]


def test_contradictory_without_conflicts_is_error():
    r = bq.evaluate(_brief(source_health={"status": "contradictory", "conflicts": []}))
    assert not r["ok"] and any("contradictory" in e for e in r["errors"])


def test_conflict_without_resolution_is_error():
    r = bq.evaluate(_brief(source_health={"status": "contradictory", "conflicts": [{"what": "x"}]}))
    assert not r["ok"]


def test_verbless_thesis_warns():
    r = bq.evaluate(_brief(thesis="a talk about databases"))
    assert any("topic label" in w for w in r["warnings"])


def test_evidence_without_source_ref_warns():
    r = bq.evaluate(_brief(evidence=[{"claim": "x"}]))
    assert any("source_ref" in w for w in r["warnings"])


def test_check_required_over_60s(tmp_path):
    r = bq.check(str(tmp_path), target_seconds=120)
    assert not r["ok"] and any("missing" in e for e in r["errors"])


def test_check_noops_when_short(tmp_path):
    r = bq.check(str(tmp_path), target_seconds=40)
    assert r["ok"] and r.get("skipped")


def test_the_one_thing_with_decimal_not_flagged():
    # a one-sentence takeaway containing a number ("3.5x", "v1.2") must NOT be read as multiple sentences
    assert bq.evaluate(_brief(the_one_thing="Model X cuts inference cost by 3.5x versus the baseline."))["ok"]
    assert bq.evaluate(_brief(the_one_thing="Upgrade to v1.2 to halve the error rate."))["ok"]


def test_missing_brief_fails_when_over_60s():
    # the >60s gate must fire when the target is known (CLI now reads it from the storyboard meta)
    assert bq.check("/no/such/dir", target_seconds=120)["ok"] is False
    assert bq.check("/no/such/dir", target_seconds=40)["ok"] is True   # short video may skip


def test_non_english_thesis_no_verb_warning():
    # the English verb heuristic must NOT fire on a Chinese thesis (every zh brief warned before)
    b = _brief(thesis="缓存把p99延迟降低了30%")
    assert not any("no recognizable verb" in w for w in bq.evaluate(b)["warnings"])
    # an English topic-label still warns
    assert any("no recognizable verb" in w for w in bq.evaluate(_brief(thesis="about caching and latency"))["warnings"])
