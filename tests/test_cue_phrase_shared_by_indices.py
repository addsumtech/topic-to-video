"""One spoken phrase on two DIFFERENT cue indices lands the later index on the phrase's NEXT spoken occurrence.

cues.resolve_cues matches the anchors in index order, each searching after the last match, so when index 1 and index 2
both anchor to "modules" and the narration says it once, index 2 finds nothing and is pushed past the last cue; when the
narration says it again later, index 2 waits for that later mention. A QR-code film (2026-11-04) authored two
elements that had to land together on separate indices with one phrase and saw the second reveal seconds late. When
the narration says the phrase at least as often as the indices that share it, each index has its own mention and the
lint stays quiet."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate  # noqa: E402


def _warn(tmp_path, page, narration):
    (tmp_path / "theme.css").write_text(":root{--bg:#111;}")
    (tmp_path / "pages").mkdir(exist_ok=True)
    (tmp_path / "pages" / "scene_01.html").write_text(page)
    warnings = []
    validate._check_html_assets(str(tmp_path), "pages/scene_01.html", False, 1, [], warnings, narration=narration)
    return [w for w in warnings if "same data-cue phrase" in w]


_PAGE = ('<div class="stage"><div class="reveal" data-cue-index="0" data-cue="grid">a</div>'
         '<div class="reveal" data-cue-index="1" data-cue="modules">b</div>'
         '<div class="reveal" data-cue-index="2" data-cue="modules">c</div></div>')


def test_a_phrase_said_once_on_two_indices_warns(tmp_path):
    found = _warn(tmp_path, _PAGE, "The grid holds modules, dark and light.")
    assert len(found) == 1 and "'modules'" in found[0] and "[1, 2]" in found[0]


def test_a_phrase_said_as_often_as_its_indices_is_quiet(tmp_path):
    assert _warn(tmp_path, _PAGE, "The grid holds modules. Then more modules arrive.") == []


def test_cjk_phrase_said_once_warns(tmp_path):
    page = _PAGE.replace('"grid"', '"网格"').replace('"modules"', '"模块"')
    found = _warn(tmp_path, page, "网格里是一个个模块，黑白分明。")
    assert len(found) == 1 and "'模块'" in found[0]
