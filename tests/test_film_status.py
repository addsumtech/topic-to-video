"""film_status: a stopped film's folder says what is done, what is stale and what comes next (the MRI run stopped at a
usage limit mid-fix, 2026-11-19, and picking it up meant reading transcripts); film_qc leaves the record it reads."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import film_qc  # noqa: E402
import film_status as fs  # noqa: E402


def _put(d, rel, t, text="x"):
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    os.utime(p, (t, t))


def _film(d, upto, t0=1_000_000):
    """A folder written step by step, one minute apart, up to `upto` files of the director path."""
    order = ["NOTES.md", "brief.json", "content_plan.json", "script.json", "timeline.json", "design/concepts.md",
             "design/keyframes.jpg", "design/animatic.mp4", "film.html", "shots/s01.js", "_plan.json",
             "work/frames/f_00000.jpg", "work/frames/f_00001.jpg", "audio/mix.wav", "final.mp4", "final.share.mp4",
             "final.srt", "out.cover.png"]
    for k, rel in enumerate(order[:upto]):
        _put(d, rel, t0 + 60 * k, json.dumps({"video": "final.mp4", "fps": 30, "frames": 2}) if rel == "_plan.json" else "x")
    return t0 + 60 * upto


def _state(d):
    return {s["step"]: s["state"] for s in fs.status(str(d))["steps"]}


def test_a_film_stopped_after_its_frames_goes_on_to_the_sound(tmp_path):
    _film(tmp_path, 13)
    r = fs.status(str(tmp_path))
    assert r["next"]["step"] == "7 sound (audio/mix.wav)", r["next"]
    assert _state(tmp_path)["6 frames"] == "done"


def test_shot_code_edited_after_the_frames_makes_them_stale(tmp_path):
    t = _film(tmp_path, 15)
    _put(tmp_path, "shots/s01.js", t + 60)
    r = fs.status(str(tmp_path))
    assert r["next"]["step"] == "6 frames" and "shots/s01.js" in r["next"]["why"], r["next"]


def test_a_script_edited_after_the_voice_asks_for_a_new_voice(tmp_path):
    t = _film(tmp_path, 5)
    _put(tmp_path, "script.json", t + 60)
    assert _state(tmp_path)["4 voice + timeline"] == "stale"


def test_an_encode_older_than_its_frames_is_stale_and_an_unchecked_film_is_not_done(tmp_path):
    t = _film(tmp_path, 18)
    _put(tmp_path, "work/frames/f_00001.jpg", t + 60)
    st = _state(tmp_path)
    assert st["8 encode (final.mp4)"] == "stale" and st["8 film_qc"] == "todo"


def test_a_skipped_animatic_is_said_and_never_sent_back_to(tmp_path):
    _film(tmp_path, 18)
    (tmp_path / "design" / "animatic.mp4").unlink()
    r = fs.status(str(tmp_path))
    assert _state(tmp_path)["5b animatic"] == "skipped" and r["next"]["step"] == "8 film_qc"


def test_film_qc_records_its_run_and_an_only_run_rejudges_on_top_of_it(tmp_path):
    t = _film(tmp_path, 18)
    v = str(tmp_path / "final.mp4")
    film_qc.record(str(tmp_path), v, ["glide", "seams"], None)
    film_qc.record(str(tmp_path), v, [], ["seams"])                       # the seam fixed, re-run alone
    rec = json.loads((tmp_path / "_qc.json").read_text())
    assert rec["red"] == ["glide"] and rec["only"] is None, rec
    st = fs.status(str(tmp_path))
    assert st["next"]["step"] == "8 film_qc" and "glide" in st["next"]["note"]
    film_qc.record(str(tmp_path), v, [], None)
    assert fs.status(str(tmp_path))["next"] is None
    os.utime(v, (t + 600, t + 600))                                          # re-encoded after the check
    assert fs.status(str(tmp_path))["next"]["step"] in ("8 film_qc", "8 deliver (.share.mp4, .srt, cover)")


def test_not_a_film_folder_is_refused(tmp_path, capsys):
    assert fs.main([str(tmp_path)]) == 2
