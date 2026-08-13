import json, pytest
import storyboard as sb
import scenes  # dispatch-resolution check

def _minimal():
    return {
        "meta": {"aspect": "16:9", "width": 1920, "height": 1080, "fps": 30,
                 "voice": "say:Samantha", "captions": True},
        "slides": [{"index": 1, "image": "frames/01.png", "narration": "Hello."}],
    }

def test_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    sb.save(_minimal(), str(p))
    got = sb.load(str(p))
    assert got["slides"][0]["narration"] == "Hello."

def test_validate_accepts_minimal():
    sb.validate(_minimal())  # no raise

def test_validate_rejects_missing_image():
    bad = _minimal(); del bad["slides"][0]["image"]
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_validate_rejects_callout_out_of_range():
    bad = _minimal()
    bad["slides"][0]["callouts"] = [{"at": 1.0, "box": [0.4, 0.3, 1.4, 0.5], "style": "highlight"}]
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_validate_intensity_field():
    # named tiers and a raw multiplier are accepted, on meta and per-slide
    for v in ("subtle", "balanced", "bold", "1.3", 0.6):
        ok = _minimal(); ok["meta"]["intensity"] = v; sb.validate(ok)          # no raise
        ok2 = _minimal(); ok2["slides"][0]["intensity"] = v; sb.validate(ok2)  # no raise
    # a typo or a nonsense value errors loudly instead of silently degrading to balanced
    for bad_v in ("bald", -1, True):
        bad = _minimal(); bad["meta"]["intensity"] = bad_v
        with pytest.raises(sb.StoryboardError):
            sb.validate(bad)
        bad2 = _minimal(); bad2["slides"][0]["intensity"] = bad_v
        with pytest.raises(sb.StoryboardError):
            sb.validate(bad2)

def test_new_slide_defaults():
    s = sb.new_slide(2, "frames/02.png")
    assert s["index"] == 2 and s["narration"] == "" and s["callouts"] == []

def test_default_voice_is_auto():
    assert sb.new_storyboard()["meta"]["voice"] == "auto"

def test_new_slide_defaults_type_slide():
    s = sb.new_slide(1, "frames/01.png")
    assert s["type"] == "slide" and s["props"] is None

def test_new_scene_roundtrip(tmp_path):
    sc = sb.new_scene(2, "title", {"title": "Hello"}, narration="Hi.")
    assert sc["type"] == "title" and sc["props"] == {"title": "Hello"} and sc["image"] is None
    p = tmp_path / "s.json"; sb.save({"meta": {}, "slides": [sc]}, str(p))
    assert sb.load(str(p))["slides"][0]["props"]["title"] == "Hello"

def _wrap(scene):
    return {"meta": {"aspect": "16:9"}, "slides": [scene]}

def test_validate_slide_still_requires_image():
    bad = _wrap({"index": 1, "type": "slide", "narration": "x"})  # no image
    with pytest.raises(sb.StoryboardError):
        sb.validate(bad)

def test_validate_unknown_type_rejected():
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap({"index": 1, "type": "hologram", "narration": "x", "props": {}}))

def test_validate_title_ok_and_requires_title_str():
    sb.validate(_wrap(sb.new_scene(1, "title", {"title": "T", "subtitle": "S"}, "n")))
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(sb.new_scene(1, "title", {"subtitle": "S"}, "n")))  # missing title

def test_validate_chart_numbers_only():
    ok = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": 5}]}, "n")
    sb.validate(_wrap(ok))
    bad = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": "five"}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(bad))
    badkind = sb.new_scene(1, "chart", {"kind": "pie", "data": [{"label": "a", "value": 5}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(badkind))
    bad_bool = sb.new_scene(1, "chart", {"kind": "bars", "data": [{"label": "a", "value": True}]}, "n")
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(bad_bool))

def test_validate_new_chart_kinds_accepted():
    # slope/dumbbell/dist/scatter/small_multiples use values/v1v2/x,y — the contract must accept them
    sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "slope", "data": [{"label": "A", "values": [1, 2]}]}, "n")))
    sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "dumbbell", "data": [{"label": "A", "v1": 1, "v2": 2}]}, "n")))
    sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "scatter", "data": [{"x": 1, "y": 2}]}, "n")))
    sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "dist", "data": [{"label": "A", "values": [1, 2, 3]}]}, "n")))
    sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "small_multiples", "data": [{"label": "A", "values": [1, 2]}]}, "n")))

def test_validate_new_chart_kinds_reject_bad_shape():
    with pytest.raises(sb.StoryboardError):   # slope with no values/v1v2
        sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "slope", "data": [{"label": "A", "value": 5}]}, "n")))
    with pytest.raises(sb.StoryboardError):   # scatter with no x/y
        sb.validate(_wrap(sb.new_scene(1, "chart", {"kind": "scatter", "data": [{"label": "A"}]}, "n")))

def test_validate_timeline_requires_events():
    sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": [{"date": "2026", "label": "x"}]}, "n")))
    with pytest.raises(sb.StoryboardError):
        sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": []}, "n")))

def test_validate_timeline_accepts_when_what():
    # the HTML .timeline archetype uses when/what — the programmatic contract must accept them too
    sb.validate(_wrap(sb.new_scene(1, "timeline", {"events": [{"when": "2026", "what": "x"}]}, "n")))

def _ai_slide():
    s = sb.new_slide(1, None); s["image"] = None
    s["image_prompt"] = "a generic rocket"; s["image_tag"] = "broll"; s["fit"] = "cover"
    s["narration"] = "n"
    return s

def test_validate_ai_slide_prompt_no_image_ok():
    sb.validate({"meta": {"image_source": "openai"}, "slides": [_ai_slide()]})

def test_validate_slide_needs_image_or_prompt():
    bad = sb.new_slide(1, None); bad["image"] = None  # no image, no prompt
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {}, "slides": [bad]})

def test_validate_bad_image_enums():
    for field, val in [("image_tag", "weird"), ("fit", "stretch")]:
        s = _ai_slide(); s[field] = val
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {"image_source": "openai"}, "slides": [s]})
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {"image_source": "satellite"}, "slides": [_ai_slide()]})
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {"image_source": "openai", "image_quality": "ultra"}, "slides": [_ai_slide()]})

def test_validate_plain_slide_still_ok():
    sb.validate({"meta": {}, "slides": [sb.new_slide(1, "frames/01.png")]})

def test_validate_keypoints_ok_and_dispatchable():
    d = {"meta": {}, "slides": [sb.new_scene(1, "keypoints",
         {"title": "T", "points": [{"label": "a", "sub": "s"}, {"label": "b"}]}, "n")]}
    sb.validate(d)
    assert callable(getattr(scenes, "render_keypoints"))   # animated dispatch will resolve it

def test_validate_keypoints_bad():
    for bad in [{"points": []}, {"points": [{"sub": "no label"}]}, {"points": [{"label": ""}]},
                {"points": [{"label": "x"}] * 6}]:
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {}, "slides": [sb.new_scene(1, "keypoints", bad, "n")]})

def test_validate_compare_ok_and_dispatchable():
    d = {"meta": {}, "slides": [sb.new_scene(1, "compare",
         {"kind": "split", "parts": [{"label": "A", "value": 3}, {"label": "B", "value": 7}]}, "n")]}
    sb.validate(d)
    assert callable(getattr(scenes, "render_compare"))

def test_validate_compare_bad():
    for bad in [{"kind": "pie", "parts": [{"label": "A", "value": 1}, {"label": "B", "value": 2}]},
                {"kind": "split", "parts": [{"label": "A", "value": 1}]},
                {"kind": "split", "parts": [{"label": "A", "value": 1}, {"label": "B"}]}]:
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {}, "slides": [sb.new_scene(1, "compare", bad, "n")]})

def test_validate_html_ok_and_dispatchable():
    d = {"meta": {}, "slides": [sb.new_scene(1, "html", {"html": "pages/s.html", "anim_seconds": 0.8}, "n")]}
    sb.validate(d)
    assert callable(getattr(scenes, "render_html"))

def test_validate_html_bad():
    for bad in [{}, {"html": ""}, {"html": "   "},
                {"html": "p.html", "anim_seconds": 0}, {"html": "p.html", "anim_seconds": -1}]:
        with pytest.raises(sb.StoryboardError):
            sb.validate({"meta": {}, "slides": [sb.new_scene(1, "html", bad, "n")]})

def test_validate_image_provider_enum():
    sb.validate({"meta": {"image_source": "openai", "image_provider": "codex"}, "slides": [sb.new_slide(1, "f.png")]})
    with pytest.raises(sb.StoryboardError):
        sb.validate({"meta": {"image_source": "openai", "image_provider": "banana"}, "slides": [sb.new_slide(1, "f.png")]})


def test_normalize_transition_flat_and_object():
    assert sb.normalize_transition({"transition": "dip", "transition_seconds": 0.2}) == ("dip", 0.2)
    assert sb.normalize_transition({"transition": {"in": "dip", "out": "dip", "seconds": 0.3}}) == ("dip", 0.3)
    assert sb.normalize_transition({"transition": {"in": "in", "out": "none"}}) == ("in", None)
    assert sb.normalize_transition({"transition": {"out": "out", "seconds": 0.25}}) == ("out", 0.25)
    assert sb.normalize_transition({"transition": "bogus"}) == (None, None)
    assert sb.normalize_transition({}) == (None, None)


def test_cinematic_scene_needs_layers():
    import storyboard as _sb
    data = _sb.new_storyboard({"renderer": "remotion"})
    s = _sb.new_scene(1, "cinematic", {}, narration="x")         # no layers
    data["slides"] = [s]
    with pytest.raises(_sb.StoryboardError):
        _sb.validate(data)

