"""page_overlap_qa: words and controls that collide on a film page over time are found from the page itself;
an intended stack (data-overlap-ok) and wrapped highlights on neighbouring lines are not collisions."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import _common  # noqa: E402
import page_overlap_qa as po  # noqa: E402

needs_chrome = pytest.mark.skipif(not _common.find_chrome(), reason="Chrome not installed")


def _film(d, body, seek="window.seek=function(t){document.body.dataset.t=t;};"):
    (d / "film.html").write_text("<!doctype html><html><body style='margin:0;width:1920px;height:1080px'>%s"
                                 "<script>%s</script></body></html>" % (body, seek))
    (d / "_plan.json").write_text(json.dumps({"video": "final.mp4", "fps": 30, "frames": 60}))


@needs_chrome
def test_two_buttons_drawn_over_each_other_collide(tmp_path):
    _film(tmp_path, "<button style='position:absolute;left:100px;top:100px;width:220px;height:50px'>Send an email</button>"
                    "<button style='position:absolute;left:250px;top:105px;width:220px;height:50px'>Check a calendar</button>")
    assert po.main([str(tmp_path)]) == 1


@needs_chrome
def test_an_intended_stack_is_exempt(tmp_path):
    _film(tmp_path, "<div data-overlap-ok><button style='position:absolute;left:100px;top:100px;width:220px'>A card</button>"
                    "<button style='position:absolute;left:150px;top:110px;width:220px'>Another card</button></div>")
    assert po.main([str(tmp_path)]) == 0


@needs_chrome
def test_wrapped_highlights_on_neighbouring_lines_do_not_collide(tmp_path):
    _film(tmp_path, "<p style='width:520px;font:40px/1.3 sans-serif'>Make a film about <mark>two whole minutes of</mark> "
                    "work that feels <mark>original and premium every</mark> time.</p>")
    assert po.main([str(tmp_path)]) == 0


@needs_chrome
def test_a_page_without_seek_is_a_usage_error(tmp_path):
    _film(tmp_path, "<p>hi</p>", seek="")
    assert po.main([str(tmp_path)]) == 2


def test_spans_join_consecutive_samples_and_drop_blips():
    hits = [{"t": t / 4, "a": "x", "b": "y"} for t in range(8)] + [{"t": 5.0, "a": "p", "b": "q"}]
    assert po.spans(hits, 0.25) == [("x", "y", 0.0, 2.0)]
