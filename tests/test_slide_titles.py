"""A film is not a slide deck: a header title on every beat reads as one (the anc film, 2026-11-05 — the user:
"你做的是视频，不是ppt，没有必要在头部引入一个标题"). validate warns when most designed beats set one; type
registers (family C), whose words ARE the picture, are exempt. New shots scaffold with no title."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate as v  # noqa: E402
import workshop as ws  # noqa: E402


def _beats(n_titled, n_plain, shot="WsShot"):
    out = [{"index": i + 1, "shot": shot, "shot_props": {"title": "Claim %d" % i}} for i in range(n_titled)]
    out += [{"index": n_titled + i + 1, "shot": shot, "shot_props": {"label": "x"}} for i in range(n_plain)]
    return out


def test_most_beats_with_a_header_title_warns_like_a_deck():
    w = v._slide_titles({"renderer": "remotion"}, _beats(8, 2))
    assert len(w) == 1 and "8 of 10" in w[0] and "slide" in w[0]


def test_a_few_titles_and_type_registers_do_not_warn():
    assert v._slide_titles({"renderer": "remotion"}, _beats(2, 8)) == []
    # a kinetic-type register's title is the picture itself
    assert v._slide_titles({"renderer": "remotion"}, _beats(8, 2, shot="CinematicTitle")) == []


def test_the_shot_scaffold_has_no_header_title(tmp_path):
    out = str(tmp_path)
    open(os.path.join(out, "storyboard.json"), "w").write('{"meta": {"renderer": "remotion"}, "slides": []}')
    src = open(ws.scaffold(out, "shot", "WsFresh", "a fresh scaffold")).read()
    assert "title" not in src.split("export const WsFresh")[1]
    assert "contentTop(W, H, false)" in src
