"""A beat's props are prepared ONCE, for the film and for every gate that renders the beat alone.

WHY. build_scenes (the film) and film_shot_props (text_safe_qa, cjk_type_qa, shot_proof, style_qa…) each prepared a
beat's props in their own code, and they drifted: a LivingMap beat reached the gates as its board words (so they
measured the register's DEMO map), a PhotoToDiagram beat without its traced lines (the render failed), and a
PhotoPlate beat without the photograph's aspect (a gate measured a crop the film never draws). Both now call one
function; this holds them to the same answer on a board that uses all three.
"""
import json
import os
import sys
import wave

from PIL import Image, ImageDraw

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import render_remotion as rr  # noqa: E402


def test_the_film_and_the_gates_get_the_same_props_for_every_beat(tmp_path):
    (tmp_path / "media").mkdir()
    (tmp_path / "audio").mkdir()
    im = Image.new("RGB", (400, 300), (30, 30, 30))
    ImageDraw.Draw(im).rectangle([100, 80, 300, 220], fill=(220, 220, 220))
    im.save(tmp_path / "media" / "p.png")
    for k in range(4):
        with wave.open(str(tmp_path / "audio" / ("%02d.wav" % k)), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\0\0" * 16000)
    maps = {"m": {"nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [["a", "b"]]}}
    slides = [{"index": 1, "shot": "LivingMap", "shot_props": {"map": "m", "add": ["a"]}},
              {"index": 2, "shot": "LivingMap", "shot_props": {"map": "m", "add": ["b"], "focus": ["b"]}},
              {"index": 3, "shot": "PhotoToDiagram", "shot_props": {"src": "media/p.png"}},
              {"index": 4, "shot": "PhotoPlate", "shot_props": {"src": "media/p.png"}}]
    for k, s in enumerate(slides):
        s.update(narration="beat %d" % k, audio="audio/%02d.wav" % k, duration=4.0)
    (tmp_path / "storyboard.json").write_text(json.dumps({"meta": {"maps": maps}, "slides": slides}), encoding="utf-8")
    film = rr.build_scenes(slides, str(tmp_path), None, meta={"maps": maps})
    for s, sc in zip(slides, film):
        assert rr.film_shot_props(s, str(tmp_path)) == sc["props"], s["shot"]
