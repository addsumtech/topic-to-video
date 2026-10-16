"""scripts/pace.py — the one spoken-length model. Pinned on the GPS test film, whose plan said 69 s, whose script
estimate said 85-92 s, and whose first draft was headed for ~100 s past every gate: the per-beat pause a film adds
(~1.2 s) was the term nobody counted."""
import json
import os

import pace


def _board(lines, target=70, lang="zh", speed=1.0, renderer="remotion", durations=None):
    slides = [{"index": i + 1, "narration": t} for i, t in enumerate(lines)]
    for s, d in zip(slides, durations or []):
        s["duration"] = d
    return {"meta": {"language": lang, "tts_speed": speed, "target_seconds": target, "renderer": renderer},
            "slides": slides}


GPS_FINAL = ["手机里的 GPS 只听不说，却知道你在哪。", "看到闪电，等得越久，雷就越远。",
             "卫星也有「闪电」。它不停广播：我在哪、几点发的。", "从发出，到手机用自己的钟记下到达，就是飞了多久。",
             "光速，卫星再快也不变。", "乘上光速，得出一个距离：你就在这个球面上。",
             "假如手机的钟和卫星一样准，三个球面通常只剩两个交点。", "但手机的钟比不上原子钟，偏了多少又是个未知数。",
             "所以要第四颗卫星：四个距离，解出手机钟差和三个坐标。", "差 3 纳秒，位置就差约 1 米。",
             "所以卫星用原子钟，地面站定期校准，彼此只差几纳秒。",
             "可是相对论让卫星钟走快。离地球远，每天快 45.8；飞得更快，慢 7.2；净快约 38 微秒，上万纳秒。",
             "发射前把卫星钟调慢一点，上天后正好走得一样快。", "开阔天空下定位通常在 4.9 米内，但靠近楼房会变差。",
             "GPS 量的不是位置，是时间。"]


def test_the_gps_film_is_predicted_within_a_few_percent_before_any_voice_is_made():
    f = pace.film(_board(GPS_FINAL, target=80, speed=1.06))
    assert not f["measured"] and f["calibrated"]
    assert abs(f["total"] - 77.1) / 77.1 < 0.05, f["total"]          # the rendered film measured 77.1 s


def test_a_beat_carries_the_pause_after_it_and_a_short_beat_holds_little():
    assert pace.beat_seconds("") >= 1.2, "an empty line still costs the pause after the beat"
    assert pace.budget_chars(4, "zh") <= 14, "a 4 s beat is not ~20 characters once the pause is counted"
    assert pace.beat_seconds("一二三四五六七八九十", speed=1.2) < pace.beat_seconds("一二三四五六七八九十")


def test_an_overrun_is_named_before_tts_and_a_measured_film_is_read_not_guessed():
    long_lines = [l + "，" + l for l in GPS_FINAL]
    w = pace.overrun_warning(_board(long_lines, target=70))
    assert w and "predicted" in w and "beat" in w, w
    assert pace.overrun_warning(_board(GPS_FINAL, target=80, speed=1.06)) is None
    measured = _board(["很短。"] * 3, target=60, durations=[20.0, 20.0, 20.0])
    f = pace.film(measured)
    assert f["measured"] and abs(f["total"] - (60 - f["seams"])) < 1e-6, f      # the cuts overlap on remotion


def test_an_uncalibrated_language_says_so():
    f = pace.film(_board(["How a phone finds itself without ever transmitting."] * 4, target=20, lang="en"))
    assert not f["calibrated"]
    w = pace.overrun_warning(_board(["word " * 40] * 4, target=10, lang="en"))
    assert w and "UNCALIBRATED" in w, w


def test_validate_warns_on_the_length_before_tts_on_the_remotion_tier(tmp_path):
    import validate as v
    b = _board([l + "，" + l for l in GPS_FINAL], target=70)
    for s in b["slides"]:
        s["shot"] = "CinematicTitle"
    r = v.evaluate(b, str(tmp_path), pre_tts=True)
    assert any(w.startswith("length:") for w in r["warnings"]), [w for w in r["warnings"]][:5]


def test_a_remotion_films_narration_is_linted_for_ai_tells_too(tmp_path):
    # the lint sat below the remotion tier's early return, so the one thing both tiers share was never read there
    import validate as v
    b = _board(["让我们一起来看看，手机怎么知道你在哪。"] + GPS_FINAL[1:3], target=15)
    for s in b["slides"]:
        s["shot"] = "CinematicTitle"
    r = v.evaluate(b, str(tmp_path), pre_tts=True)
    assert any("narration AI-tell" in w and "让我们一起" in w for w in r["warnings"]), r["warnings"][:6]
