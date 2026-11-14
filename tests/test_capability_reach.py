"""capability_reach — the skill's built capabilities a film uses, and the ones it leaves unused without a reason.

The user, 2026-11-14: "做了这么多优化，都展示出来呀 ... 你优化完了得学会用呀". A rebuilt film used almost none of the
skill's new light, material and optics work; nothing said so."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import capability_reach as cr  # noqa: E402


def _film(tmp_path, shot_src, slides, meta=None):
    d = tmp_path / "workshop" / "shots"
    d.mkdir(parents=True)
    (d / "MyShot.tsx").write_text(shot_src)
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": dict({"renderer": "remotion"}, **(meta or {})), "slides": slides}))
    return str(tmp_path)


def test_a_flat_narrated_film_names_what_it_leaves_unused(tmp_path):
    film = _film(tmp_path, "export const MyShot = () => <div style={{background: BG}} />;", [{"shot": "MyShot"}])
    fams, used, waivers = cr.reach(film)
    miss = cr.unused_lines(fams, used, waivers)
    assert {m.split()[0] for m in miss} == set(cr.NARRATED)


def test_light_material_optics_seen_in_the_shot_and_its_kit_and_a_reason_waives(tmp_path):
    src = ("import {LitStage} from '@runtime/craftStage';\nimport {kit} from './myKit';\n"
           "export const MyShot = () => <LitStage ground={BG} />;")
    film = _film(tmp_path, src, [{"shot": "MyShot", "optic": "sweep", "camera": {"move": "push"}}],
                 meta={"capability_waivers": {"time": "no impact in this film", "seams": "one continuous take"}})
    (tmp_path / "workshop" / "shots" / "myKit.ts").write_text("// @material: each part answers the key light\n")
    fams, used, waivers = cr.reach(film)
    assert used["light"] and used["material"] and used["optics"] and used["camera"]
    assert cr.unused_lines(fams, used, waivers) == []


def test_a_promo_with_one_layout_and_no_world_is_told(tmp_path):
    lab = {"kind": "object", "items": [{"acts": [{"kind": "ring"}]}], "label": {"text": "x", "side": "left"}}
    spec = {"shots": [lab] * 4 + [{"kind": "outro"}]}
    fams, used, waivers = cr.promo(spec)
    names = {m.split()[0] for m in cr.unused_lines(fams, used, waivers)}
    assert {"composition", "outro", "breadth", "links"} <= names and "staging" not in names and "acts" not in names


def test_a_page_film_is_read_in_its_own_vocabulary(tmp_path):
    """The QR film (HTML tier: cue-timed pages, marked seams) read 0 of 6 against the Remotion families. A page film is
    read for seams, cues, light, motion and emphasis."""
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "scene_01.html").write_text('<div data-cue-index="1" data-cue="corner" style="animation: rise 1s">x</div>')
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"renderer": "local", "transition_style": "fadethrough"},
                                                         "slides": [{"type": "html", "transition": "in"}]}))
    fams, used, _ = cr.reach(str(tmp_path))
    assert fams is cr.PAGES
    assert used["seams"] and used["cues"] and used["motion"] and used["emphasis"] and not used["light"]
