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
    (d / "film.html").write_text("<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0;width:1920px;height:1080px'>%s"
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


# ── words cut by the frame's edge ──────────────────────────────────────────────────────────────────────────────
_SHOT = "<div style='position:absolute;inset:0;overflow:hidden'>%s</div>"   # a shot's own frame-sized clip, as films build it


@needs_chrome
def test_a_line_held_across_the_frames_edge_is_cut(tmp_path, capsys):
    # the topic-to-video launch film: a camera following typing left the prompt line running off the right edge
    _film(tmp_path, _SHOT % "<p style='position:absolute;left:1500px;top:400px;margin:0;font:40px monospace;white-space:pre'>"
                            "Use the topic-to-video skill to make a launch film</p>")
    assert po.main([str(tmp_path)]) == 1
    assert "EDGE-CUT" in capsys.readouterr().out


@needs_chrome
def test_a_deliberate_bleed_a_rule_and_a_line_cut_inside_the_frame_are_not_edge_cuts(tmp_path):
    _film(tmp_path, _SHOT % (
        "<h1 data-bleed-ok style='position:absolute;left:1200px;top:100px;margin:0;font:200px sans-serif;white-space:pre'>BIG TYPE</h1>"
        "<p style='position:absolute;left:1700px;top:500px;margin:0;font:40px monospace;white-space:pre'>────────────────────</p>"
        "<div style='position:absolute;left:200px;top:700px;width:300px;height:80px;overflow:hidden'>"
        "<p style='margin:0;font:40px monospace;white-space:pre'>a line its own box cuts, well inside the frame</p></div>"
        "<p style='position:absolute;left:1700px;top:900px;margin:0;font:12px sans-serif;white-space:pre'>small texture type runs on and on</p>"))
    assert po.main([str(tmp_path)]) == 0


@needs_chrome
def test_a_line_passing_the_edge_in_a_slide_is_not_held_there(tmp_path):
    # in view for one sample, gone the next: a push or a slide, not a cut
    _film(tmp_path, _SHOT % "<p id='s' style='position:absolute;top:400px;margin:0;font:40px monospace;white-space:pre'>sliding through</p>",
          seek="window.seek=function(t){document.getElementById('s').style.left=(1700+t*4000)+'px';};")
    assert po.main([str(tmp_path)]) == 0
