"""beat_key: a beat's fingerprint changes with what its picture is made of, and ONLY with that — an edit to one shot
must not re-measure a beat on another shot, and nothing a beat renders from may be left out."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import beat_key as bk  # noqa: E402


def _film(tmp_path):
    ws = tmp_path / "workshop" / "shots"
    (ws / "kit").mkdir(parents=True)
    (ws / "kit" / "Kit.tsx").write_text("export const ink = '#000';\n", encoding="utf-8")
    (ws / "A.tsx").write_text("import {ink} from './kit/Kit';\nimport {useT} from '@runtime/motion';\n"
                              "export const A = () => null;\n", encoding="utf-8")
    (ws / "B.tsx").write_text("import {ink} from './kit/Kit';\nexport const B = () => null;\n", encoding="utf-8")
    tool = tmp_path / "tool.py"
    tool.write_text("# v1\n", encoding="utf-8")
    meta = {"design_dna": {"bg": "#fff"}, "aspect": "16:9"}
    return str(tmp_path), meta, str(tool)


def _keys(out, meta, tool):
    return (bk.beat_key(out, {"shot": "A", "shot_props": {"t": "x"}}, meta, tool),
            bk.beat_key(out, {"shot": "B", "shot_props": {"t": "x"}}, meta, tool))


def test_the_closure_follows_relative_imports_and_the_runtime_alias(tmp_path):
    out, _meta, _tool = _film(tmp_path)
    files = bk.code_closure(bk.shot_file(out, "A"))
    names = {os.path.relpath(f, out) for f in files if f.startswith(out)}
    assert names == {os.path.join("workshop", "shots", "A.tsx"), os.path.join("workshop", "shots", "kit", "Kit.tsx")}
    assert any(f.endswith(os.path.join("runtime", "motion.ts")) for f in files)


def test_editing_one_shot_leaves_the_other_beats_key_alone(tmp_path):
    out, meta, tool = _film(tmp_path)
    a0, b0 = _keys(out, meta, tool)
    p = tmp_path / "workshop" / "shots" / "A.tsx"
    p.write_text(p.read_text(encoding="utf-8") + "// changed\n", encoding="utf-8")
    a1, b1 = _keys(out, meta, tool)
    assert a1 != a0 and b1 == b0


def test_a_shared_helper_an_asset_the_props_and_the_instrument_all_change_the_key(tmp_path):
    out, meta, tool = _film(tmp_path)
    a0, b0 = _keys(out, meta, tool)
    (tmp_path / "workshop" / "shots" / "kit" / "Kit.tsx").write_text("export const ink = '#111';\n", encoding="utf-8")
    a1, b1 = _keys(out, meta, tool)
    assert a1 != a0 and b1 != b0                     # both import the kit
    (tmp_path / "workshop" / "logo.png").write_bytes(b"\x89PNG")
    a2, b2 = _keys(out, meta, tool)
    assert a2 != a1 and b2 != b1                     # an asset can be reached by name: every beat sees it
    a3 = bk.beat_key(out, {"shot": "A", "shot_props": {"t": "y"}}, meta, tool)
    assert a3 != a2
    assert bk.beat_key(out, {"shot": "A", "shot_props": {"t": "x"}}, dict(meta, aspect="9:16"), tool) != a2
    open(tool, "a", encoding="utf-8").write("# v2\n")
    assert _keys(out, meta, tool)[0] != a2           # editing the instrument re-measures what it measured


def test_a_beat_with_no_workshop_copy_keys_on_the_library_register(tmp_path):
    out, meta, tool = _film(tmp_path)
    assert bk.shot_file(out, "CardFlip3D").endswith(os.path.join("src", "shots", "CardFlip3D.tsx"))
    assert bk.beat_key(out, {"shot": "CardFlip3D"}, meta, tool) != bk.beat_key(out, {"shot": "QuadSplit"}, meta, tool)


def test_a_film_named_by_a_relative_path_keys_as_the_same_film_named_absolutely(tmp_path):
    out, meta, tool = _film(tmp_path)
    slide = {"shot": "A", "shot_props": {"t": "x"}}
    assert bk.beat_key(os.path.relpath(out), slide, meta, tool) == bk.beat_key(out, slide, meta, tool)
