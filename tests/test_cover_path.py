"""The cover frame is written where cover.py then looks for it, whatever out_dir was given as (scripts/cover.py).

Measured 2026-11-01: rendering a film named by a RELATIVE out_dir, the cover still ran with the renderer's working
directory (remotion/) and wrote `<rel>/.cover_frame.png` under remotion/, while cover.py looked for it under the
caller's directory, found nothing, and the film shipped with no cover — leaving a stray directory in the repository.
"""
import json
import os

import cover


def test_the_cover_frame_path_is_absolute_for_a_relative_out_dir(tmp_path, monkeypatch):
    import remotion_segments as _rs
    import render_remotion as _rr
    import stage_frames as _sf
    film = tmp_path / "films" / "f"
    film.mkdir(parents=True)
    (film / "storyboard.json").write_text(json.dumps({"meta": {}, "slides": [{"index": 1}]}))
    seen = {}

    class FakeStills:
        def __init__(self, out_dir, payload):
            seen["out_dir"] = out_dir

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def still(self, frame, payload, png):
            seen["png"] = png
            from PIL import Image
            Image.new("RGB", (1080, 1920), (10, 10, 10)).save(png)
            return 0, ""

    monkeypatch.setattr(_sf, "film_payload", lambda out_dir, board: {"aspect": "9:16", "scenes": [{"durF": 60}]})
    monkeypatch.setattr(_sf, "sample_frames", lambda *a, **k: {})
    monkeypatch.setattr(_sf, "Stills", FakeStills)
    monkeypatch.setattr(_rs, "timeline", lambda scenes, seam: ([(0, 60)], 60))
    monkeypatch.setattr(_rr, "frame_at_t", lambda dur, t: 30)
    monkeypatch.setattr(cover, "_title_top", lambda *a: 100)
    monkeypatch.setattr(cover, "_content_bottom", lambda *a: 1600)
    monkeypatch.setattr(cover, "card", lambda im, top, bottom: im)
    monkeypatch.chdir(tmp_path)
    dest = cover.cover(os.path.join("films", "f"))
    assert os.path.isabs(seen["png"]), seen
    assert os.path.isabs(seen["out_dir"]), seen
    assert os.path.exists(os.path.join(str(film), "out.cover.png")) and os.path.isabs(dest)
