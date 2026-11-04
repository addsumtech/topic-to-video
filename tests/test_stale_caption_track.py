"""An authored `captions` track timed for another voice is flagged.

`tts.py --only N` re-voices one beat and keeps every other field on the board — including beat N's own authored
`captions` track, whose times came from the OLD audio. The track then ends seconds before or after the new clip, and
every chunk shows off its words; nothing said so (a QR-code film, 2026-11-04, re-voiced beats and re-derived its
tracks by hand). A track whose last cue ends away from the beat's duration was timed for a different clip."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import validate  # noqa: E402


def _warns(tmp_path, end, duration):
    caps = [{"start": 0.0, "end": 2.0, "text": "第一句话"}, {"start": 2.0, "end": end, "text": "第二句话"}]
    (tmp_path / "audio").mkdir(exist_ok=True)
    board = {"meta": {"title": "t", "voice": "say", "language": "zh"},
             "slides": [{"index": 1, "type": "title", "props": {"title": "t"}, "narration": "第一句话。第二句话。",
                         "duration": duration, "captions": caps}]}
    return [w for w in validate.evaluate(board, str(tmp_path), pre_tts=False)["warnings"] if "timed for" in w]


def test_a_track_ending_off_the_clip_warns(tmp_path):
    assert len(_warns(tmp_path, 4.0, 6.5)) == 1
    assert len(_warns(tmp_path, 7.8, 6.5)) == 1


def test_a_track_ending_on_the_clip_is_quiet(tmp_path):
    assert _warns(tmp_path, 6.5, 6.5) == []
    assert _warns(tmp_path, 6.3, 6.5) == []          # a last chunk may stop just short of the tail pad
