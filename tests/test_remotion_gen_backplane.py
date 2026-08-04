"""Generated-backplane discipline (the Codex/`atmosphere` depth plane) — director + guardrail lints.

A cinematic beat may put a GENERATED image on a FAR depth plane where CODE can't draw the texture, tagged
`treatment:"atmosphere"`. That is atmosphere ONLY: validate enforces three bright lines on such a plane —
it must be a BACKPLANE (behind the focal/text plane), carry NO text/data (gen glyphs garble), and never
stand in for a REAL named subject (that's `documentary`). And `imagegen._image_slots` must actually FILL
such a plane's `src` (else the director instruction is a dead pointer). These lock both halves."""
import os
import validate as v
import imagegen


# ── the enabler: imagegen fills a depth-plane / stage-element `src`, not just the scene image ──────────
def test_image_slots_yields_scene_layer_and_stage_element():
    data = {"slides": [
        {"index": 1, "image_prompt": "a rocket", "image_tag": "cover"},                 # scene image
        {"index": 2, "layers": [                                                         # cinematic depth plane
            {"kind": "image", "image_prompt": "volumetric haze", "treatment": "atmosphere"},
            {"kind": "panel", "title": "Focus"},                                         # code plane — no prompt
        ]},
        {"index": 3, "props": {"stage": {"elements": [                                    # shot-stage image element
            {"id": "bg", "kind": "image", "image_prompt": "wet asphalt texture"},
            {"id": "hero", "kind": "card", "html": "pages/hero.html"},
        ]}}},
    ]}
    slots = list(imagegen._image_slots(data))
    dests = {label: dest for _owner, dest, label, _tag in slots}
    assert any(d == "image" for d in dests.values()), "scene image slot missing"
    assert any(d == "src" for d in dests.values()), "depth-plane / element src slot missing"
    # exactly the three UNFILLED prompts, nothing from the code-only planes
    assert len(slots) == 3, [l for _o, _d, l, _t in slots]


def test_image_slots_skips_already_filled():
    data = {"slides": [
        {"index": 1, "image_prompt": "a rocket", "image": ".assets/x.png"},              # already has image
        {"index": 2, "layers": [{"kind": "image", "image_prompt": "haze", "src": ".assets/y.png"}]},  # has src
        {"index": 3, "layers": [{"kind": "panel", "title": "no prompt"}]},               # no prompt at all
    ]}
    assert list(imagegen._image_slots(data)) == []


def test_image_slots_default_tag_is_backplane_for_planes():
    data = {"slides": [{"index": 1, "layers": [{"kind": "image", "image_prompt": "mist"}]}]}
    (_owner, dest, _label, tag), = imagegen._image_slots(data)
    assert dest == "src" and tag == "backplane"


# ── guardrail lints on a gen (`atmosphere`) depth plane ───────────────────────────────────────────────
def _run(out_dir, layers):
    errs, warns = [], []
    v._cinematic_fields({"type": "cinematic", "layers": layers}, {"fps": 30}, out_dir, "s1", errs, warns)
    return errs, warns


def _png(tmp_path, name="bg.png"):
    p = tmp_path / name
    p.write_bytes(b"\x89PNG\r\n\x1a\n")  # only existence matters to _exists
    return name


def test_gen_image_on_foreground_parallax_errors(tmp_path):
    src = _png(tmp_path)
    errs, _ = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "parallax": 1.2, "image_prompt": "haze"},
    ])
    assert any("GENERATED image at parallax" in e for e in errs), errs


def test_gen_image_backplane_parallax_is_clean(tmp_path):
    src = _png(tmp_path)
    errs, warns = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "parallax": 0.6, "blur": 8,
         "image_prompt": "soft volumetric haze, painterly light"},
        {"kind": "panel", "title": "The point", "parallax": 1.0},
    ])
    assert not any("GENERATED" in e for e in errs), errs
    assert not any("GENERATED image with no explicit depth" in w for w in warns), warns


def test_gen_image_in_front_of_text_plane_z_errors(tmp_path):
    src = _png(tmp_path)
    errs, _ = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "z": 0, "image_prompt": "terrain"},
        {"kind": "panel", "title": "Focus", "z": -200},   # focal text plane sits deeper than the gen plane
    ])
    assert any("in front of the text plane" in e for e in errs), errs


def test_gen_image_behind_text_plane_z_is_clean(tmp_path):
    src = _png(tmp_path)
    errs, _ = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "z": -1200, "blur": 10, "image_prompt": "terrain"},
        {"kind": "panel", "title": "Focus", "z": -200},
    ])
    assert not any("GENERATED" in e for e in errs), errs


def test_gen_image_carrying_text_errors(tmp_path):
    src = _png(tmp_path)
    errs, _ = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "parallax": 0.6,
         "title": "This should be code", "image_prompt": "haze"},
    ])
    assert any("GENERATED image carrying TEXT" in e for e in errs), errs


def test_gen_image_with_doc_query_warns(tmp_path):
    src = _png(tmp_path)
    _errs, warns = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "parallax": 0.6,
         "doc_query": "Golden Gate Bridge", "image_prompt": "haze"},
    ])
    assert any("names a real subject" in w for w in warns), warns


def test_gen_prompt_asking_for_text_warns(tmp_path):
    src = _png(tmp_path)
    _errs, warns = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "src": src, "parallax": 0.6,
         "image_prompt": "a dashboard with charts and numbers"},
    ])
    assert any("gen image_prompt asks for" in w for w in warns), warns


def test_layer_image_prompt_without_src_errors(tmp_path):
    # authored a gen backplane but never ran imagegen — clearer than 'src not found'
    errs, _ = _run(str(tmp_path), [
        {"kind": "image", "treatment": "atmosphere", "parallax": 0.6, "image_prompt": "haze"},
    ])
    assert any("run imagegen.py first" in e for e in errs), errs


def test_non_gen_image_foreground_is_unaffected(tmp_path):
    # a NON-atmosphere image (a real/documentary plane, or an untagged one) may be foreground/focal —
    # the guardrails fire ONLY on treatment:"atmosphere".
    src = _png(tmp_path)
    errs, _ = _run(str(tmp_path), [
        {"kind": "image", "src": src, "parallax": 1.2, "title": "real product shot"},
    ])
    assert not any("GENERATED" in e for e in errs), errs


# ── the SAME guardrails must generalise to the shot-based `stage.elements` path (the preferred tier) ────
def _run_stage(elements):
    errs, warns = [], []
    scene = {"type": "cinematic", "stage": {"elements": elements},
             "shots": [{"type": "HERO", "target": elements[0]["id"]}]}
    v._cinematic_fields(scene, {"fps": 30}, "/tmp", "s1", errs, warns)
    return errs, warns


def test_stage_gen_image_in_front_of_focal_errors():
    # a gen atmosphere image element sitting at/in front of the focal card's z is guarded, like a layer.
    errs, _ = _run_stage([
        {"id": "hero", "kind": "card", "html": "pages/h.html", "position": [0, 0, -200]},
        {"id": "bg", "kind": "image", "treatment": "atmosphere", "position": [0, 0, 0],
         "image_prompt": "wet asphalt texture"},
    ])
    assert any("stage element 'bg'" in e and "in front of the text plane" in e for e in errs), errs


def test_stage_gen_image_behind_focal_is_clean():
    errs, _ = _run_stage([
        {"id": "hero", "kind": "card", "html": "pages/h.html", "position": [0, 0, -200]},
        {"id": "bg", "kind": "image", "treatment": "atmosphere", "position": [0, 0, -1400],
         "blur": 10, "image_prompt": "soft volumetric haze"},
    ])
    assert not any("GENERATED" in e for e in errs), errs


def test_stage_gen_image_with_text_and_doc_query_flagged():
    errs, warns = _run_stage([
        {"id": "hero", "kind": "card", "html": "pages/h.html", "position": [0, 0, -200]},
        {"id": "bg", "kind": "image", "treatment": "atmosphere", "position": [0, 0, -1400],
         "heroText": "should be code", "doc_query": "Eiffel Tower", "image_prompt": "haze"},
    ])
    assert any("stage element 'bg'" in e and "carrying TEXT" in e for e in errs), errs
    assert any("stage element 'bg'" in w and "names a real subject" in w for w in warns), warns
