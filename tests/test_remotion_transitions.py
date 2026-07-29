"""P3 backstop — cross-scene transitions in the Remotion tier.

A marked seam (a scene's out-edge or the next scene's in-edge) becomes a real cross-scene transition the
TS TransitionSeries renders, replacing two within-clip dips. These lock the A/V-SAFE contract: the seam
fades are de-doubled, the overlap is clamped to the audio breath, total duration subtracts the overlaps,
and the standalone SRT shifts later scenes earlier by the cumulative overlap (so it matches the burned,
scene-local captions)."""
import pytest
import render_remotion as rr
import storyboard as sb


def _board(n=3, style=None, secs=0.2, dur=4.0, breath=None):
    m = {"fps": 30, "renderer": "remotion", "captions": True, "transition": "dip", "transition_seconds": secs}
    if style:
        m["transition_style"] = style
    if breath is not None:
        m["audio_breath"] = breath
    d = sb.new_storyboard(m)
    for i in range(1, n + 1):
        s = sb.new_scene(i, "title", {"title": "S%d" % i}, narration="Scene %d words here now." % i)
        s["image"] = ".assets/x.png"; s["audio"] = "audio/%02d.mp3" % i; s["duration"] = dur
        s["transition"] = "dip"; s["transition_seconds"] = secs
        d["slides"].append(s)
    return d


def _total(scenes):
    return sum(s["durationInFrames"] for s in scenes) - sum((s["transitionToNext"] or {}).get("durationInFrames", 0) for s in scenes)


def test_seam_becomes_transition_and_dedoubles_fades(tmp_path):
    scs = rr.build_props(_board(3), str(tmp_path))["scenes"]
    # scene 1: opening fade kept, out-edge handed to the transition
    assert scs[0]["fadeInFrames"] == 6 and scs[0]["fadeOutFrames"] == 0
    assert scs[0]["transitionToNext"] == {"style": "fade", "durationInFrames": 6}
    # middle: both seam fades zeroed
    assert scs[1]["fadeInFrames"] == 0 and scs[1]["fadeOutFrames"] == 0
    # last: closing fade kept, no transition
    assert scs[-1]["fadeOutFrames"] == 6 and scs[-1]["transitionToNext"] is None


def test_total_duration_subtracts_overlaps(tmp_path):
    scs = rr.build_props(_board(3, dur=4.0, secs=0.2), str(tmp_path))["scenes"]
    assert _total(scs) == 360 - 12  # 3*120 frames - two 6-frame overlaps


def test_overlap_clamped_to_audio_breath(tmp_path):
    # a 1.0s transition (30f) must be clamped to the breath (0.42s -> 13f) so it can't eat live narration
    scs = rr.build_props(_board(2, secs=1.0, breath=0.42), str(tmp_path))["scenes"]
    ov = scs[0]["transitionToNext"]["durationInFrames"]
    assert ov == round(0.42 * 30), ov  # clamped, not 30


@pytest.mark.parametrize("style,expect", [
    ("dip", "fade"), ("fadethrough", "fade"), ("push", "slide"),
    ("lift", "slide-up"), ("wipe", "wipe"), ("drift", "slide"), ("blur", "blur")])
def test_transition_style_maps(tmp_path, style, expect):
    scs = rr.build_props(_board(2, style=style), str(tmp_path))["scenes"]
    assert scs[0]["transitionToNext"]["style"] == expect


def test_per_scene_style_override(tmp_path):
    d = _board(2, style="dip")
    d["slides"][0]["transition_style"] = "wipe"  # override just this seam
    scs = rr.build_props(d, str(tmp_path))["scenes"]
    assert scs[0]["transitionToNext"]["style"] == "wipe"


def test_hard_cut_seam_has_no_transition(tmp_path):
    d = _board(2)
    for s in d["slides"]:
        s["transition"] = "none"  # no edges -> no seam -> a cut
    scs = rr.build_props(d, str(tmp_path))["scenes"]
    assert scs[0]["transitionToNext"] is None


def test_overlap_zeroed_when_mastering_off(tmp_path):
    """audio_master:false means no trailing-breath silence exists, so the overlap must clamp to ~1 frame
    (a cut) — a real cross-fade there would eat live narration."""
    d = _board(2, secs=0.5)
    d["meta"]["audio_master"] = False
    scs = rr.build_props(d, str(tmp_path))["scenes"]
    assert scs[0]["transitionToNext"]["durationInFrames"] == 1  # not 15 (0.5s)


def test_single_scene_board_has_no_transition(tmp_path):
    scs = rr.build_props(_board(1), str(tmp_path))["scenes"]
    assert scs[0]["transitionToNext"] is None
    assert scs[0]["fadeInFrames"] == 6 and scs[0]["fadeOutFrames"] == 6  # both edges kept (open+close)


def test_overlapped_srt_shifts_later_scenes_earlier(tmp_path):
    import os
    d = _board(2, secs=0.4, dur=3.0)
    # write the audio-less board's srt via the overlapped writer; check scene 2 starts 0.4s early
    rr._write_srt_overlapped(d, str(tmp_path), str(tmp_path / "out.srt"))
    srt = (tmp_path / "out.srt").read_text()
    assert "00:00:02,600 -->" in srt  # scene 2 at 3.0 - 0.4 overlap = 2.6s (not 3.0)
