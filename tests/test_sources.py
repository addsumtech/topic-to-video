

# ── a number's separators are the number (audit 2026-11-15, step 8): the matcher stripped them with the other
# punctuation, so a cited '3.5' supported '售价35元' and the anti-fabrication gate passed an invented figure
def test_a_decimal_point_or_a_range_dash_is_kept_between_digits():
    import sources as s
    for anchor, page, want in (("3.5", "售价35元", False), ("2-3", "23天", False), ("35", "1350 元", False),
                               ("28,800", "每小时28800拍", True), ("28800", "28,800 拍", True),
                               ("3.5 kg", "重 3.5kg", True), ("2–3", "2-3 天", True),
                               ("Version 1 (21", "Version 1 (21 × 21 modules)", True)):
        assert s._contains(s._norm(page), s._norm(anchor)) is want, (anchor, page)


def test_a_range_is_given_by_both_its_ends():
    import sources as s
    assert s.supports_number(s._norm("Above 1 or 2 kHz, every headset"), "1-2")
    assert not s.supports_number(s._norm("Above 1 kHz"), "1-2")
    assert s.number_groups("售价 3.5 元，2–3 天，28,800 拍") == ["3.5", "2-3", "28800"]
