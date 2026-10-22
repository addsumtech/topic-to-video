"""deliver.py hands the user the video where they look for it — the Desktop, else Downloads — and never inside this
skill's folder or ~/.claude."""
import json
import os
import stat
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import deliver as dv  # noqa: E402


def _film(tmp_path, title=None, srt=True):
    out = tmp_path / "film"
    out.mkdir()
    (out / "out.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    if srt:
        (out / "out.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n字幕\n", encoding="utf-8")
    if title is not None:
        (out / "storyboard.json").write_text(json.dumps({"meta": {"title": title}, "slides": []}), encoding="utf-8")
    return str(out)


def _home(tmp_path, desktop=True, downloads=True):
    home = tmp_path / "home"
    home.mkdir()
    if desktop:
        (home / "Desktop").mkdir()
    if downloads:
        (home / "Downloads").mkdir()
    return str(home)


def test_the_video_lands_on_the_desktop_named_for_the_film(tmp_path):
    out = _film(tmp_path, title="MRI 成像原理")
    home = _home(tmp_path)
    paths = dv.deliver(out, home=home)
    assert paths[0] == os.path.join(home, "Desktop", "MRI 成像原理.mp4")
    assert os.path.isfile(paths[0])
    assert paths[1] == os.path.join(home, "Desktop", "MRI 成像原理.srt"), "the captions sit beside the video under its name"


def test_downloads_takes_it_when_the_desktop_cannot_be_written(tmp_path):
    out = _film(tmp_path, title="Espresso")
    home = _home(tmp_path)
    desk = os.path.join(home, "Desktop")
    os.chmod(desk, stat.S_IRUSR | stat.S_IXUSR)
    try:
        if os.access(desk, os.W_OK) and dv._writable(desk):
            pytest.skip("this account can write a read-only folder (running as root?)")
        assert dv.deliver(out, home=home)[0] == os.path.join(home, "Downloads", "Espresso.mp4")
    finally:
        os.chmod(desk, stat.S_IRWXU)


def test_no_folder_the_user_browses_is_refused_by_name(tmp_path):
    out = _film(tmp_path)
    home = _home(tmp_path, desktop=False, downloads=False)
    with pytest.raises(SystemExit) as e:
        dv.deliver(out, home=home)
    assert "--to" in str(e.value)


def test_the_skill_folder_and_dot_claude_are_never_destinations(tmp_path):
    out = _film(tmp_path)
    home = _home(tmp_path)
    for bad in (os.path.join(_ROOT, "remotion"), os.path.join(home, ".claude", "projects")):
        os.makedirs(bad, exist_ok=True)
        with pytest.raises(SystemExit) as e:
            dv.deliver(out, to=bad, home=home)
        assert "where the user does not look" in str(e.value)


def test_a_second_delivery_never_overwrites_the_first(tmp_path):
    out = _film(tmp_path, title="City")
    home = _home(tmp_path)
    first = dv.deliver(out, home=home)[0]
    second = dv.deliver(out, home=home)[0]
    assert first != second and second.endswith("City (2).mp4") and os.path.isfile(first)


def test_the_out_dir_name_is_used_without_a_title_and_a_missing_video_is_refused(tmp_path):
    out = _film(tmp_path, srt=False)
    home = _home(tmp_path)
    assert dv.deliver(out, home=home) == [os.path.join(home, "Desktop", "film.mp4")]
    os.remove(os.path.join(out, "out.mp4"))
    with pytest.raises(SystemExit) as e:
        dv.deliver(out, home=home)
    assert "render the film first" in str(e.value)


def test_a_title_cannot_escape_the_folder(tmp_path):
    out = _film(tmp_path, title="../../etc/pass:wd")
    home = _home(tmp_path)
    path = dv.deliver(out, home=home)[0]
    assert os.path.dirname(path) == os.path.join(home, "Desktop")


def test_the_sample_is_delivered_under_its_own_name(tmp_path):
    import deliver as _d
    film = tmp_path / "film"; film.mkdir()
    (film / "sample.mp4").write_bytes(b"sample")
    desk = tmp_path / "Desktop"; desk.mkdir()
    paths = _d.deliver(str(film), to=str(desk), home=str(tmp_path), what="sample")
    assert [os.path.basename(p) for p in paths] == ["film - sample.mp4"]
    import pytest
    with pytest.raises(SystemExit, match="no preview.mp4"):
        _d.deliver(str(film), to=str(desk), home=str(tmp_path), what="preview")
