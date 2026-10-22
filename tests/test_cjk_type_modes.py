"""cjk_type_qa on registers the fixture used to misread: one with several modes (each draws its own copy), one whose
part of the copy must be found inside another, and one whose types live in a kit beside it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import cjk_type_qa as c  # noqa: E402


def test_a_mode_union_is_read_as_the_modes_to_sweep():
    assert c.register_modes("RangeSpheres") == ["bias", "two"]
    assert c.register_modes("CardFlip3D") == []          # no mode prop: swept once, as before


def test_a_part_found_inside_a_whole_is_fed_a_piece_of_it():
    props = {"reply": "它自己拆解任务、调用工具、改动文件", "ring": "毫不相干的一句话", "title": "标题"}
    c._couple_contained(props, "const ringed = ring && reply.includes(ring) ? ring : null;")
    assert props["ring"] and props["ring"] in props["reply"]
    assert props["title"] == "标题"                        # untouched: nothing couples it


def test_no_coupling_is_invented_without_an_includes_in_the_source():
    props = {"reply": "一段回答", "ring": "另一句"}
    c._couple_contained(props, "const x = reply.length + ring.length;")
    assert props["ring"] == "另一句"


def test_types_declared_in_an_imported_kit_are_read_with_the_register(tmp_path, monkeypatch):
    kits = tmp_path / "src" / "kits"
    kits.mkdir(parents=True)
    (kits / "PaneKit.tsx").write_text("export type Spot = 'tl' | 'tr' | 'none';\n", encoding="utf-8")
    monkeypatch.setattr(c, "_REMOTION", str(tmp_path))
    src = "import {Spot} from '../kits/PaneKit';\nexport const X: React.FC<{at?: Spot}> = () => null;\n"
    full = c._with_kits(src)
    assert "export type Spot" in full and full.startswith(src)
    assert c._literal_alias_member("Spot", full) == "tl"
    # a register that imports no kit is read as it was
    assert c._with_kits("export const Y = 1;\n") == "export const Y = 1;\n"


def test_a_rows_chance_is_a_share_of_one_whole():
    rows = [c._synth_field("p", "number", "", i, i, 0) for i in range(10)]
    assert all(0 < v <= 12 for v in rows) and sum(rows) < 100, rows
    assert c._synth_field("count", "number", "", 0, 0, 0) != c._synth_field("p", "number", "", 0, 0, 0)


def test_a_list_is_capped_at_the_limit_the_register_itself_throws_at():
    src = ("const trees = rows<Tree>(treesIn ?? [], 'trees', 'X');\n"
           "if (trees.length > 2) throw new Error('one or two');\n"
           "if (rolls.length >= 4) throw new Error('three at most');\n")
    props = {"trees": [1, 2, 3], "rolls": [1, 2, 3, 4, 5], "items": [1, 2, 3]}
    c._cap_rows(props, src)
    assert props == {"trees": [1, 2], "rolls": [1, 2, 3], "items": [1, 2, 3]}
