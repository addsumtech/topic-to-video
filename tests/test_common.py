import os, subprocess, pytest
import _common as c

def test_run_returns_stdout():
    assert c.run(["echo", "hi"]).strip() == "hi"

def test_run_raises_on_failure():
    with pytest.raises(subprocess.CalledProcessError):
        c.run(["false"])

def test_audio_duration_of_generated_clip(tmp_path):
    wav = tmp_path / "a.aiff"
    c.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
           "-t", "1.0", str(wav)])
    d = c.audio_duration(str(wav))
    assert 0.9 <= d <= 1.1

def test_have_tool():
    assert c.have_tool("ffmpeg") is True
    assert c.have_tool("definitely-not-a-tool-xyz") is False

def test_find_chrome_honors_meta_path(tmp_path):
    fake = tmp_path / "MyChrome"; fake.write_text("")
    assert c.find_chrome({"chrome_path": str(fake)}) == str(fake)

def test_find_chrome_ignores_bad_meta_path():
    # a non-existent chrome_path must not be returned; falls through to real discovery (path or None)
    r = c.find_chrome({"chrome_path": "/nope/Chrome"})
    assert r is None or os.path.exists(r)


# ---- shared CSS animation-duration table (validate + scenes must agree on these numbers) ---------

def test_css_anim_durations_match_the_stylesheets():
    import _common
    t = _common.css_anim_durations()
    assert t["draw"] == 1.4 and t["reveal"] == 0.7 and t["float"] == 3.0

def test_element_anim_seconds_prefers_an_inline_override():
    import _common
    assert _common.element_anim_seconds('<path class="draw" style="animation-duration:.5s">') == 0.5

def test_element_anim_seconds_falls_back_to_the_class():
    import _common
    assert _common.element_anim_seconds('<path class="draw connector">') == 1.4

def test_element_anim_seconds_none_without_animation():
    import _common
    assert _common.element_anim_seconds('<div class="card">') is None

def test_element_anim_seconds_ignores_ambient_backdrops():
    # .bg-live/.bg-drift are progress-driven across the whole scene and are never truncated
    import _common
    assert _common.element_anim_seconds('<img class="bg-soft bg-live">') is None


# ---- sources.py: the capture that makes a citation checkable ------------------------------------

def test_source_id_rejects_path_traversal_and_separators():
    import sources, tempfile, pytest
    T = tempfile.mkdtemp()
    for bad in ("../escape", "a/b", "", ".hidden", "A-Upper", "x" * 80):
        with pytest.raises(ValueError):
            sources.add(T, bad, "text", "origin")

def test_source_refuses_an_empty_extract():
    import sources, tempfile, pytest
    with pytest.raises(ValueError):
        sources.add(tempfile.mkdtemp(), "sid", "   \n ", "origin")

def test_resolve_handles_malformed_refs():
    import sources, tempfile
    T = tempfile.mkdtemp(); sources.add(T, "doc", "交付可验收的结果", "o")
    assert sources.resolve(T, "")[0] is False
    assert sources.resolve(T, None)[0] is False
    assert sources.resolve(T, "ghost#x")[0] is False
    assert sources.resolve(T, "doc")[0] is True            # no anchor: exists, unpinned
    assert sources.resolve(T, "doc#交付可验收的结果")[0] is True

def test_anchor_match_normalises_punctuation_and_whitespace():
    import sources, tempfile
    T = tempfile.mkdtemp(); sources.add(T, "doc", "交付、可验收的  结果", "o")
    assert sources.resolve(T, "doc#交付可验收的结果")[0] is True

def test_missing_extract_file_is_reported_not_silently_passed():
    import sources, tempfile, os
    T = tempfile.mkdtemp(); sources.add(T, "doc", "text", "o")
    os.remove(os.path.join(T, "sources", "doc.txt"))
    ok, detail = sources.resolve(T, "doc#text")
    assert ok is False and "missing" in detail


# ── what a sweep did NOT measure ──────────────────────────────────────────────────────────────────────
# `ink_contrast_qa` swept 170 registers and reported 19 "skipped"; a skip reads like a clean result and
# behind those 19 sat four different bugs. These two helpers are the shared answer — the coverage line
# every sweep prints, and the reason it prints beside each name — so they are pinned here once.

def test_coverage_counts_the_universe_not_the_measurements(capsys):
    """The headline must state M, not N. A gate that measured 151 of 170 must not print a line reading 170."""
    k = c.coverage("g", 151, 170, {"Zed": "refused to render — boom"})
    out = capsys.readouterr().out
    assert "measured 151 of 170" in out and "19 NOT measured" in out, out
    assert k == 19


def test_coverage_cannot_hide_an_item_it_lost_without_a_reason(capsys):
    """K comes from the universe, never from the length of the reason map — otherwise a sweep that dropped
    an item and forgot to write down why would report full coverage."""
    k = c.coverage("g", 3, 5, {})
    out = capsys.readouterr().out
    assert k == 2 and "2 NOT measured" in out and "NO recorded reason" in out, out


def test_coverage_names_every_item_with_its_reason(capsys):
    c.coverage("g", 0, 2, {"Alpha": "no fixture for its `src` prop", "Zed": "its type could not be parsed"})
    out = capsys.readouterr().out
    assert "Alpha" in out and "no fixture for its `src` prop" in out
    assert "Zed" in out and "its type could not be parsed" in out


def test_render_error_reports_the_message_not_the_stack():
    """`splitlines()[-1]` on a failed remotion render is `at process.processTicksAndRejections (…)`, which
    is what eight of the nineteen skips carried."""
    blob = ("Bundling...\nAn error occurred:\nError: StateSheet needs at least one `cells` entry\n"
            "    at St (bundle.js:1:2)\n    at process.processTicksAndRejections (node:internal/x)")
    got = c.render_error("", blob)
    assert "needs at least one" in got and "processTicksAndRejections" not in got, got


def test_render_error_reads_an_error_TYPE_not_the_literal_word_Error():
    """The fixed-frame bug's own message names a subclass and starts the line with it: matching `Error` at
    the start of a line reports `Rendered 0/1` and the gate looks like it failed for no reason."""
    blob = ("Rendered 0/1\nRangeError: Cannot use frame 110: Duration of composition is 96, therefore the "
            "highest frame that can be rendered is 95\n    at f (x.js:1:1)")
    got = c.render_error("", blob)
    assert got.startswith("RangeError: Cannot use frame 110"), got
    assert "Rendered" not in got, "the progress counter was glued onto a self-contained message: %r" % got


def test_render_error_says_when_there_was_no_message_at_all():
    got = c.render_error("", "    at process.processTicksAndRejections (node:internal/x)")
    assert "no message" in got, got
    assert "no output at all" == c.render_error("", "")
