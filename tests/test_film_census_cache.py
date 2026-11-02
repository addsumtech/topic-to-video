"""One Film census per render state, shared by text_safe --glide, text_safe --sync and jitter_qa.

WHY. The three gates each bundled the remotion project and walked the DOM of every frame of the film with the SAME
props (typeGlide on): three identical censuses per delivery round. The user called the post-render check too long; a
parallel-lanes attempt was measured and dropped (each census already drives cores/2 Chrome tabs). The census is now
kept in the film folder under a key over everything it depends on — the Film props, the renderer's source, the film's
own workshop and the census code — and a gate whose key matches reads it instead of rendering it again."""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import text_safe_qa as ts  # noqa: E402


@pytest.fixture
def census(tmp_path, monkeypatch):
    """film_census with every render step stubbed; `calls` counts the censuses actually run."""
    import remotion_segments as rs
    import workshop as ws
    (tmp_path / "workshop" / "shots").mkdir(parents=True)
    (tmp_path / "workshop" / "shots" / "A.tsx").write_text("export const A = 1;\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(ws, "prepare", lambda out_dir: {})
    monkeypatch.setattr(rs, "minimal_public", lambda props, out_dir, dest: dest)
    monkeypatch.setattr(rs, "timeline", lambda scenes, seam: ([(0, 9)], 10))
    monkeypatch.setattr(ts, "glide_bundle", lambda dest, public=None, env=None: dest)

    def run(jobs, bundle, concurrency=None, extra=()):
        calls.append(jobs[0]["props"])
        return {"film": {"frames": {0: {"lines": [{"t": "x"}]}, 7: {"lines": []}}, "done": {"logged": 10}, "error": None}}
    monkeypatch.setattr(ts, "glide_run", run)
    return tmp_path, calls


def test_the_same_film_is_censused_once(census):
    d, calls = census
    props = {"scenes": [{"shot": "A", "props": {"t": 1}}]}
    a = ts.film_census(str(d), props)
    b = ts.film_census(str(d), props)
    assert len(calls) == 1
    assert a == b, "the kept census must read back exactly as rendered (frame keys are ints)"
    assert sorted(b[0]["frames"]) == [0, 7] and b[1:] == ([(0, 9)], 10)


def test_a_changed_prop_or_workshop_file_is_censused_again(census):
    d, calls = census
    props = {"scenes": [{"shot": "A", "props": {"t": 1}}]}
    ts.film_census(str(d), props)
    ts.film_census(str(d), {"scenes": [{"shot": "A", "props": {"t": 2}}]})
    assert len(calls) == 2
    (d / "workshop" / "shots" / "A.tsx").write_text("export const A = 2;\n", encoding="utf-8")
    ts.film_census(str(d), {"scenes": [{"shot": "A", "props": {"t": 2}}]})
    assert len(calls) == 3


def test_a_damaged_cache_is_rendered_again_not_trusted(census):
    d, calls = census
    props = {"scenes": []}
    ts.film_census(str(d), props)
    path = d / ts.FILM_CENSUS_CACHE
    path.write_bytes(b"\x1f\x8b not gzip")
    ts.film_census(str(d), props)
    assert len(calls) == 2


def test_a_census_that_did_not_finish_is_never_kept(census, monkeypatch):
    d, calls = census
    monkeypatch.setattr(ts, "glide_run", lambda *a, **k: (calls.append(1), {"film": {"frames": {}, "done": None,
                                                                                    "error": "browser died"}})[1])
    ts.film_census(str(d), {"scenes": []})
    ts.film_census(str(d), {"scenes": []})
    assert len(calls) == 2
    assert not (d / ts.FILM_CENSUS_CACHE).exists()


def test_a_replaced_picture_is_censused_again(census):
    """A picture swapped under the same name can lay the page out differently (its box, its wrap)."""
    d, calls = census
    (d / "media").mkdir()
    (d / "media" / "p.png").write_bytes(b"one")
    ts.film_census(str(d), {"scenes": []})
    (d / "media" / "p.png").write_bytes(b"a different, longer picture")
    ts.film_census(str(d), {"scenes": []})
    assert len(calls) == 2
