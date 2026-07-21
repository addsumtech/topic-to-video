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


def test_one_thing_filename_and_abbrev_dots_not_sentence_ends():
    # a filename dot (SKILL.md, index.html) or an abbreviation (e.g.) is NOT a sentence end — the old
    # digit-only guard blocked a legitimate one-sentence takeaway that names a file
    r = bq.evaluate(_brief(the_one_thing="Use SKILL.md and e.g. index.html to turn slides into video."))
    assert not any(">1 sentence" in e for e in r["errors"]), r["errors"]
    # a REAL two-sentence takeaway still errors
    r2 = bq.evaluate(_brief(the_one_thing="Cache it. Also index it."))
    assert any(">1 sentence" in e for e in r2["errors"])


# ---- source capture: make a citation checkable instead of decorative ----------------------------
# The one place a WRONG INPUT yields a fully-green output: the gates check the brief's internal
# consistency, the plans inherit it, and every beat carries the error. A content critic reviewing a
# real deck said it outright — it could audit brief.json as an artifact but could not re-verify its
# web-sourced figures, because nothing in the workdir preserved what was read.

def _srcbrief(tmp_path, evidence, coverage=None):
    import json
    d = {"thesis": "X 把 A 变成 B。", "mechanism": "因为 P，所以 Q；因此 R。",
         "why_it_matters": "省下重复劳动。", "the_one_thing": "一句话。",
         "source_health": {"status": "coherent", "conflicts": []}, "evidence": evidence}
    if coverage is not None:
        d["coverage"] = coverage
    json.dump(d, open(str(tmp_path / "brief.json"), "w"), ensure_ascii=False)
    return d

def test_source_ref_anchor_must_exist_in_the_captured_text(tmp_path):
    import sources
    sources.add(str(tmp_path), "doc", "官方说：交付可验收的结果。", "https://example/doc", "web")
    _srcbrief(tmp_path, [{"claim": "编造的数字", "source_ref": "doc#准确率 98%"}])
    r = bq.check(str(tmp_path))
    assert r["ok"] is False
    assert any("anchor not found" in e for e in r["errors"])

def test_source_ref_resolves_when_the_quote_is_real(tmp_path):
    import sources
    sources.add(str(tmp_path), "doc", "官方说：交付可验收的结果。", "https://example/doc", "web")
    _srcbrief(tmp_path, [{"claim": "官方强调交付", "source_ref": "doc#交付可验收的结果"}],
           coverage={"read_in_full": ["doc"], "sampled": [], "skipped": []})
    r = bq.check(str(tmp_path))
    assert r["ok"] is True and not any("does not resolve" in e for e in r["errors"])

def test_unknown_source_id_is_an_error(tmp_path):
    import sources
    sources.add(str(tmp_path), "doc", "任意文本。", "https://example/doc", "web")
    _srcbrief(tmp_path, [{"claim": "引用了没落盘的来源", "source_ref": "ghost#随便"}])
    r = bq.check(str(tmp_path))
    assert r["ok"] is False and any("unknown source id" in e for e in r["errors"])

def test_ref_checking_is_skipped_when_nothing_was_captured(tmp_path):
    # no sources/ dir -> advisory only; a deck grounded on material the author read directly
    # must not be blocked by a mechanism it never opted into
    _srcbrief(tmp_path, [{"claim": "某说法", "source_ref": "自由文本引用"}],
           coverage={"read_in_full": ["手边的论文"], "sampled": [], "skipped": []})
    r = bq.check(str(tmp_path))
    assert r["ok"] is True

def test_missing_coverage_warns(tmp_path):
    _srcbrief(tmp_path, [{"claim": "c", "source_ref": "r"}])
    r = bq.check(str(tmp_path))
    assert any("coverage" in w for w in r["warnings"])

def test_anchor_matching_ignores_punctuation_and_whitespace(tmp_path):
    import sources
    sources.add(str(tmp_path), "doc", "交付、可验收的  结果", "https://example/doc", "web")
    _srcbrief(tmp_path, [{"claim": "同一句话，标点不同", "source_ref": "doc#交付可验收的结果"}],
           coverage={"read_in_full": ["doc"]})
    assert bq.check(str(tmp_path))["ok"] is True

def test_coverage_must_be_an_object_not_a_free_form_note(tmp_path):
    # a string/list/number passed the first version silently: the field existed but nothing
    # downstream could tell what was left unopened
    for bad in (["a"], "读了全部", 0):
        _srcbrief(tmp_path, [{"claim": "c", "source_ref": "r"}], coverage=bad)
        assert any("coverage" in w for w in bq.check(str(tmp_path))["warnings"]), bad

def test_evaluate_is_backward_compatible_without_out_dir():
    # older callers pass only the parsed brief; ref-resolution must degrade, not raise
    d = {"thesis": "X 把 A 变成 B。", "mechanism": "因为 P 所以 Q，因此 R。",
         "why_it_matters": "省。", "the_one_thing": "一句话。",
         "source_health": {"status": "coherent", "conflicts": []},
         "evidence": [{"claim": "c", "source_ref": "anything"}]}
    assert bq.evaluate(d)["ok"] is True

def test_malformed_sources_index_degrades_instead_of_raising(tmp_path):
    import os
    os.makedirs(str(tmp_path / "sources"), exist_ok=True)
    (tmp_path / "sources" / "index.json").write_text("{ not json")
    _srcbrief(tmp_path, [{"claim": "c", "source_ref": "doc#x"}], coverage={"read_in_full": ["d"]})
    assert bq.check(str(tmp_path))["ok"] is True

def test_evidence_entries_that_are_not_objects_do_not_raise(tmp_path):
    _srcbrief(tmp_path, ["a string", 42, None, {"claim": "c"}], coverage={"read_in_full": ["d"]})
    bq.check(str(tmp_path))     # must not raise


# ---- evidence HARDNESS: resolving proves a quote EXISTS, not that it is TRUE --------------------
# The capture layer above stops fabrication. It says nothing about whether the source was worth
# believing. The real case that motivated this: every third-party guide said "5000 credits on
# signup"; the official page said 500/month. Both anchors would have resolved. Only the tier
# separates "the thing itself" from "someone's write-up of the thing".

def test_a_claim_with_no_primary_source_warns(tmp_path):
    import sources
    sources.add(str(tmp_path), "guide", "注册后即可领取 5000 积分。", "https://blog/x", "web",
                tier="community")
    _srcbrief(tmp_path, [{"claim": "注册即送 5000 积分", "source_ref": "guide#领取 5000 积分"}],
              coverage={"read_in_full": ["guide"]})
    r = bq.check(str(tmp_path))
    assert r["ok"] is True, "hardness is advisory — it must not block a legitimate deck"
    assert any("no PRIMARY source" in w for w in r["warnings"]), r["warnings"]

def test_a_primary_source_does_not_warn(tmp_path):
    import sources
    sources.add(str(tmp_path), "off", "免费版每月发放 500 积分。", "https://official/pricing", "web",
                tier="primary", as_of="2026-07-21")
    _srcbrief(tmp_path, [{"claim": "免费版每月 500 积分", "source_ref": "off#每月发放 500 积分"}],
              coverage={"read_in_full": ["off"]})
    assert not bq.check(str(tmp_path))["warnings"]

def test_user_supplied_material_counts_as_hard_evidence(tmp_path):
    # `self` = the user handed it over. Demanding an external primary source for the user's own
    # deck/notes would fire on every material-driven run.
    import sources
    sources.add(str(tmp_path), "deck", "我们的目标是把周报自动化。", "./notes.md", "notes", tier="self")
    _srcbrief(tmp_path, [{"claim": "目标是把周报自动化", "source_ref": "deck#把周报自动化"}],
              coverage={"read_in_full": ["deck"]})
    assert not any("PRIMARY" in w or "corroboration" in w
                   for w in bq.check(str(tmp_path))["warnings"])

def test_source_ref_may_be_a_LIST_and_cross_sourcing_clears_the_warning(tmp_path):
    import sources
    sources.add(str(tmp_path), "off", "三端同步上线。", "https://official/news", "web",
                tier="primary", as_of="2026-07-18")
    sources.add(str(tmp_path), "news", "三端同步上线。", "https://press/x", "web", tier="secondary")
    _srcbrief(tmp_path, [{"claim": "三端同步上线",
                          "source_ref": ["off#三端同步上线", "news#三端同步上线"]}],
              coverage={"read_in_full": ["off"]})
    r = bq.check(str(tmp_path))
    assert r["ok"] is True and not r["warnings"], r["warnings"]

def test_every_ref_in_a_LIST_is_still_resolved(tmp_path):
    # the list form must not become a way to smuggle an unchecked ref past the anchor gate
    import sources
    sources.add(str(tmp_path), "off", "真实存在的句子。", "https://official/x", "web", tier="primary")
    _srcbrief(tmp_path, [{"claim": "c", "source_ref": ["off#真实存在的句子", "off#从未写过的句子"]}],
              coverage={"read_in_full": ["off"]})
    r = bq.check(str(tmp_path))
    assert r["ok"] is False and any("anchor not found" in e for e in r["errors"])

def test_a_lone_secondary_source_warns_about_corroboration(tmp_path):
    import sources
    sources.add(str(tmp_path), "news", "该产品已服务超过一万家企业。", "https://press/x", "web",
                tier="secondary")
    _srcbrief(tmp_path, [{"claim": "服务超过一万家企业", "source_ref": "news#超过一万家企业"}],
              coverage={"read_in_full": ["news"]})
    assert any("no PRIMARY" in w or "corroboration" in w
               for w in bq.check(str(tmp_path))["warnings"])

def test_a_time_sensitive_claim_without_as_of_warns(tmp_path):
    # a page FETCHED today can itself be stale — one run's pricing page still read
    # "effective July 1" three weeks after July 1
    import sources
    sources.add(str(tmp_path), "off", "专业版每月 99 元。", "https://official/pricing", "web",
                tier="primary", fetched="2026-07-21")
    _srcbrief(tmp_path, [{"claim": "专业版目前每月 99 元", "source_ref": "off#每月 99 元"}],
              coverage={"read_in_full": ["off"]})
    r = bq.check(str(tmp_path))
    assert r["ok"] is True
    assert any("as_of" in w for w in r["warnings"]), r["warnings"]

def test_as_of_silences_the_staleness_warning(tmp_path):
    import sources
    sources.add(str(tmp_path), "off", "专业版每月 99 元。", "https://official/pricing", "web",
                tier="primary", as_of="2026-07-21")
    _srcbrief(tmp_path, [{"claim": "专业版目前每月 99 元", "source_ref": "off#每月 99 元"}],
              coverage={"read_in_full": ["off"]})
    assert not any("as_of" in w for w in bq.check(str(tmp_path))["warnings"])

def test_a_mechanism_claim_is_not_treated_as_time_sensitive(tmp_path):
    # the check must stay quiet on claims that do not go stale, or it becomes noise the
    # author learns to scroll past
    import sources
    sources.add(str(tmp_path), "off", "它在本机沙盒里执行，只能访问你授权的文件夹。",
                "https://official/overview", "web", tier="primary")
    _srcbrief(tmp_path, [{"claim": "它只能访问你授权的文件夹", "source_ref": "off#只能访问你授权的文件夹"}],
              coverage={"read_in_full": ["off"]})
    assert not bq.check(str(tmp_path))["warnings"]

def test_an_unresolvable_ref_does_not_also_produce_hardness_noise(tmp_path):
    # a broken citation is ONE problem; piling three warnings on top buries the error
    import sources
    sources.add(str(tmp_path), "off", "任意文本。", "https://official/x", "web", tier="primary")
    _srcbrief(tmp_path, [{"claim": "c", "source_ref": "ghost#x"}], coverage={"read_in_full": ["off"]})
    r = bq.check(str(tmp_path))
    assert any("unknown source id" in e for e in r["errors"])
    assert not any("PRIMARY" in w or "corroboration" in w or "as_of" in w for w in r["warnings"])

def test_an_unknown_tier_is_rejected_at_capture_time(tmp_path):
    # a typo ("offical", "docs") must not silently become an unlabelled source that then
    # dodges the no-primary warning
    import sources, pytest
    with pytest.raises(ValueError):
        sources.add(str(tmp_path), "x", "文本", "https://o/x", "web", tier="offical")

def test_an_unlabelled_source_is_not_assumed_primary(tmp_path):
    import sources
    sources.add(str(tmp_path), "x", "某个说法。", "https://o/x", "web")     # no tier passed
    _srcbrief(tmp_path, [{"claim": "某个说法", "source_ref": "x#某个说法"}],
              coverage={"read_in_full": ["x"]})
    assert any("no PRIMARY source" in w for w in bq.check(str(tmp_path))["warnings"])
