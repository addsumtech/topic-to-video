"""Long beats split at PLANNING time (scripts/pace.py long_beats, scripts/split_beats.py).

WHY. Measured on 311 beats of 22 of our films (craft_qa): beats of 4-6 s held a frame still past 3 s 9% of the time,
8-10 s 51%, 12 s and over 89-100% — one register, one reveal, then waiting for the voice. The planner's own rhythm says
~3-6 s (~8 for a climax) and nothing enforced it before the voice was made, when a split costs nothing.
"""
import json

import pace
import split_beats as sb


def test_a_split_prefers_a_sentence_end_near_the_middle_to_a_comma_at_it():
    """Measured on bench-aurora: 「…一两百公里的氧发绿光，‖ 最常见；…」 cut a clause from its predicate."""
    text = "颜色看气体和高度：一两百公里的氧发绿光，最常见；更高的氧发红光；氮发蓝光，下缘泛粉。"
    a, b = pace.split_point(text)
    assert a + b == text
    assert a.endswith("；") or a.endswith("："), (a, b)


def test_a_text_without_a_break_is_not_split():
    assert pace.split_point("一句没有任何停顿的话") is None


def test_long_beats_names_every_beat_over_the_limit_with_pieces_under_it():
    long_zh = "相对论让卫星钟走快。离地球远，每天快四十五微秒；飞得更快，每天慢七微秒。净快约三十八微秒，上万纳秒，换成距离就是十公里的误差，所以必须在发射前把钟调慢。"
    board = {"meta": {"language": "zh", "renderer": "remotion"},
             "slides": [{"index": 1, "shot": "A", "narration": "很短的一句。"},
                        {"index": 2, "shot": "B", "narration": long_zh},
                        {"index": 3, "shot": "C", "narration": long_zh, "camera": {"move": "push"}}]}
    rows = pace.long_beats(board, limit=8.0)
    by = {r["index"]: r for r in rows}
    assert 1 not in by and 2 in by
    assert "".join(by[2]["pieces"]) == long_zh
    assert all(pace.beat_seconds(p, "zh") <= 8.0 + 1e-6 for p in by[2]["pieces"]), by[2]
    # an authored push/pull this long is stepped on the voice (render_remotion.LONG_BEAT) — it has its events
    assert by.get(3) is None or pace.beat_seconds(long_zh, "zh") < 10.0


def test_apply_splits_the_beat_and_leaves_the_new_one_for_the_director(tmp_path):
    long_zh = "相对论让卫星钟走快。离地球远，每天快四十五微秒；飞得更快，每天慢七微秒。净快约三十八微秒，上万纳秒，换成距离就是十公里的误差。"
    board = {"meta": {"language": "zh", "renderer": "remotion"},
             "slides": [{"index": 1, "shot": "A", "narration": "开头。", "caption": "开头。"},
                        {"index": 2, "shot": "B", "shot_props": {"x": 1}, "narration": long_zh, "caption": long_zh},
                        {"index": 3, "shot": "C", "narration": "结尾。", "caption": "结尾。"}]}
    (tmp_path / "storyboard.json").write_text(json.dumps(board, ensure_ascii=False))
    n = sb.split(str(tmp_path), beat=2, limit=8.0)
    out = json.load(open(tmp_path / "storyboard.json", encoding="utf-8"))["slides"]
    assert n >= 2 and len(out) == 2 + n
    assert [s["index"] for s in out] == list(range(1, len(out) + 1))
    parts = out[1:1 + n]
    assert "".join(p["narration"] for p in parts) == long_zh
    assert parts[0]["shot"] == "B" and parts[0]["shot_props"] == {"x": 1}
    for p in parts[1:]:
        assert "shot" not in p and p.get("relation") == "continuation" and p.get("split_from") == 2
    assert out[-1]["shot"] == "C"


def test_validate_names_a_long_beat_with_its_split_before_the_voice():
    import validate
    long_zh = "相对论让卫星钟走快。离地球远，每天快四十五微秒；飞得更快，每天慢七微秒。净快约三十八微秒，上万纳秒，换成距离就是十公里的误差。"
    board = {"meta": {"language": "zh", "renderer": "remotion"},
             "slides": [{"index": 1, "shot": "A", "narration": long_zh}]}
    warnings = validate._long_beat_warnings(board)
    assert len(warnings) == 1 and "beat 1" in warnings[0] and "split_beats.py" in warnings[0], warnings
    board["meta"]["renderer"] = "html"
    assert validate._long_beat_warnings(board) == []
