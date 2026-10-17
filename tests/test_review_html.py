"""The HTML tier's rendered review is the SAME gate as remotion's (critic_ledger.py), held to design-critic's
H-dimensions instead of shot-critic's S-dimensions:

* the H-series is parsed from agents/design-critic.md by the parser that reads the S-series, its faithfulness row is
  never accepted, and the route rows bind to the dimension that declares them (H8), found the same way as S14;
* every page validate.py credits BUILT or BESPOKE carries a route row;
* critic_brief.py builds a real HTML brief: keyframe_qa first, the delivered frames, a sheet of the page filmstrips
  (scene_NN.png ONLY — never the progress frames beside them), the render recorded;
* a FULL HTML render leaves NOT_DELIVERED.md (the sample and the preview neither write nor remove it), and
  critic_ledger.py --final clears it;
* a board with no authored page (the 原样配音 tier) is not reviewed by a ledger — and the gate says so, it does not pass.
"""
import json
import os
import subprocess
import sys
import time

import pytest
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import critic_ledger as cl  # noqa: E402
import contact_sheet  # noqa: E402
from test_html_design_first import BESPOKE_STYLE, SHARES, STOCK  # noqa: E402

DESIGN_CRITIC = os.path.join(_ROOT, "agents", "design-critic.md")


def _strip(path, tiles=5, colour=(240, 236, 228)):
    """keyframe_qa's per-scene filmstrip: `tiles` 560x315 frames side by side."""
    Image.new("RGB", (560 * tiles, 315), colour).save(path)


def _html_film(tmp_path, pages=(BESPOKE_STYLE, STOCK), review=None, meta_extra=None, fits=None):
    out = tmp_path / "film"
    (out / "pages").mkdir(parents=True, exist_ok=True)
    (out / "_keyframes").mkdir(exist_ok=True)
    slides = []
    for i, body in enumerate(pages, 1):
        rel = "pages/scene_%02d.html" % i
        (out / rel).write_text("<!doctype html><html><head></head><body>%s</body></html>" % body, encoding="utf-8")
        s = {"index": i, "type": "html", "props": {"html": rel}, "narration": "Line %d." % i, "duration": 1.0}
        if (fits or {}).get(i):
            s["shot_fit"] = dict(fits[i])
        slides.append(s)
        _strip(str(out / "_keyframes" / ("scene_%02d.png" % i)))
        # the files keyframe_qa writes BESIDE the strip — never a beat of their own
        for extra in ("scene_%02d_p000.png" % i, "scene_%02d_p100.png" % i, "scene_%02d_resting.png" % i):
            Image.new("RGB", (192, 108), (10, 10, 10)).save(str(out / "_keyframes" / extra))
    meta = {"renderer": "local", "language": "en", "aspect": "16:9"}
    if review is not None:
        meta["review"] = review
    meta.update(meta_extra or {})
    (out / "storyboard.json").write_text(json.dumps({"meta": meta, "slides": slides}), encoding="utf-8")
    sheet, _n, _size = contact_sheet.build(str(out))
    later = time.time() + 1
    os.utime(sheet, (later, later))
    return str(out)


def _ledger(out, **over):
    led = {"reviewer": "independent", "verdict": "PASS", "render_sha256": cl.render_id(out),
           "rows": [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_01.png"}
                    for d, _t in cl.film_dimensions(out)]}
    led.update(over)
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    return led


# ── the H-series: parsed, not listed ────────────────────────────────────────────────────────────────────

def test_the_h_series_is_parsed_from_the_design_critic_by_the_same_parser():
    dims = dict(cl.dimensions(DESIGN_CRITIC, "H"))
    assert len(dims) >= 6 and "H1" in dims
    assert "FAITHFULNESS" in dims["H1"]
    # the rows the brief's task names: faithfulness (the hard gate), routes, A/V + captions, built things
    assert any("ROUTES" in t for t in dims.values()) and any("BURNED CAPTIONS" in t for t in dims.values())
    assert any("BUILT THINGS" in t for t in dims.values())
    # the route rows bind to the dimension that SAYS so, on both series — not to a title regex of one of them
    assert cl.routes_dimension(DESIGN_CRITIC, "H") == "H8"
    assert cl.routes_dimension() == "S14"
    # and the H-series is walked by the precedent test like the S- and E-series
    assert (DESIGN_CRITIC, "H") in [(os.path.abspath(p), x) for p, x in cl.CASE_LAW_FILES]
    pre = cl.precedents(DESIGN_CRITIC, "H")
    assert set(pre) == set(dims), "every H rule carries a precedent or says `none on record`"


def test_every_h_dimension_names_the_existing_checks_it_maps_onto():
    """No new doctrine: each H-dimension's body names the design-critic / critic-av / critic-content checks it
    carries into the ledger."""
    import re
    src = open(DESIGN_CRITIC, encoding="utf-8").read()
    bodies = dict(re.findall(r"^\*\*(H\d+)\s*·(.*?)(?=^\*\*H\d+\s*·|\Z)", src, re.M | re.S))
    for hid, body in bodies.items():
        assert re.search(r"\bD\d+[a-f]?\b|\bR\d+[a-z]?\b|critic-av|critic-content", body), hid
    # every D-check the delivery review is said to cover appears in some H body
    allb = "\n".join(bodies.values())
    for d in ("D1", "D2", "D2c", "D2f", "D5", "D6b", "D6c", "D7", "D8", "D9", "D10", "D11", "R7"):
        assert re.search(r"\b%s\b" % d, allb), d


# ── an HTML film is held to the H-series by the same gate ───────────────────────────────────────────────

def test_an_html_film_is_held_to_the_h_series(tmp_path):
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    assert cl.film_tier(out) == "html"
    tmpl = cl.template(out)
    assert [r["id"] for r in tmpl["rows"]] == [d for d, _ in cl.dimensions(DESIGN_CRITIC, "H")]
    assert tmpl["_critic"] == "agents/design-critic.md"
    # a ledger written against the S-series is missing every H row
    json.dump({"reviewer": "independent", "verdict": "PASS", "render_sha256": cl.render_id(out),
               "rows": [{"id": d, "verdict": "pass", "evidence": "_keyframes/scene_01.png"}
                        for d, _ in cl.dimensions()]}, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    errs = cl.validate(out)[0]
    assert any(e.startswith("H1 ") and "has no row" in e for e in errs), errs
    assert cl.never_accepted(out) == {"H1"} and cl.never_accepted() == {"S3"}


def test_every_built_or_bespoke_page_needs_a_route_row(tmp_path):
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    cl.record_render(out)
    assert cl._design_routes(out) == [(1, "bespoke")]
    _ledger(out)
    errs = cl.validate(out)[0]
    assert any("`routes` is missing" in e and "BUILT or BESPOKE" in e and "(H8)" in e for e in errs), errs
    rows = [{"beat": 1, "route": "bespoke", "visible": False, "evidence": "_keyframes/scene_01.png"}]
    _ledger(out, routes=rows)
    errs = cl.validate(out)[0]
    assert any("H8 does not fail" in e and "stock page" in e for e in errs), errs
    rows[0]["visible"] = True
    _ledger(out, routes=rows)
    assert not cl.validate(out)[0], cl.validate(out)[0]
    assert [(r["beat"], r["route"]) for r in cl.template(out)["routes"]] == [(1, "bespoke")]


def test_an_html_faithfulness_finding_is_never_accepted(tmp_path):
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    cl.record_render(out)
    rows = [{"beat": 1, "route": "bespoke", "visible": True, "evidence": "_keyframes/scene_01.png"}]
    led = _ledger(out, routes=rows, verdict="REVISE")
    led["rows"][0] = {"id": "H1", "verdict": "fail", "evidence": "_keyframes/scene_01.png",
                      "fix": "replace the unsourced 70% with the brief's 64%"}
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    b = json.load(open(os.path.join(out, "storyboard.json")))
    b["meta"]["review"]["accepted"] = [{"id": "H1", "user_answer": "fine, ship it", "render_sha256": cl.render_id(out)}]
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    errs = cl.validate(out, final=True)[0]
    assert any("H1 is a faithfulness/sourcing finding" in e and "never" in e for e in errs), errs


def test_a_film_with_no_authored_page_is_not_applicable_never_a_pass(tmp_path):
    out = str(tmp_path)
    json.dump({"meta": {"renderer": "local"},
               "slides": [{"index": 1, "type": "slide", "image": "s1.png"}]},
              open(os.path.join(out, "storyboard.json"), "w"))
    assert cl.film_tier(out) is None
    errs, _ = cl.validate(out, final=True)
    assert errs and "no authored page" in errs[0], errs
    for flag in ([], ["--final"], ["--emit-template"]):
        p = subprocess.run([sys.executable, cl.__file__, out] + flag, capture_output=True, text=True)
        assert p.returncode == 2 and "NOT APPLICABLE" in p.stdout and "critic-av" in p.stdout, (flag, p.stdout)
    assert not os.path.exists(os.path.join(out, cl.LEDGER_NAME))
    # and a remotion board, or one with no board at all, keeps the S-series it always had
    json.dump({"meta": {"renderer": "remotion"}, "slides": []}, open(os.path.join(out, "storyboard.json"), "w"))
    assert cl.film_tier(out) == "remotion"
    os.remove(os.path.join(out, "storyboard.json"))
    assert cl.film_tier(out) == "remotion"


# ── the contact sheet: scene_NN.png only, labelled with something a reviewer can use ─────────────────────

def test_the_contact_sheet_reads_only_scene_nn_and_lays_strips_out_wide(tmp_path):
    out = _html_film(tmp_path, pages=(BESPOKE_STYLE, STOCK, STOCK))
    path, n, size = contact_sheet.build(out)
    assert n == 3, "the progress frames and the resting frame beside each strip are not beats"
    labels = contact_sheet.labels(out)
    assert labels[1] == "BESPOKE · scene_01.html" and labels[2] == "AS-IS · scene_02.html", labels
    # a 5-tile strip is ONE wide cell: each tile at least 160px, not 64px inside a single-frame cell
    assert size[0] >= 5 * 160, size
    # numbered numerically, so beat 100 does not sort before beat 11
    kdir = os.path.join(out, "_keyframes")
    for i in (11, 100):
        _strip(os.path.join(kdir, "scene_%02d.png" % i))
    assert contact_sheet.build(out)[1] == 5


def test_a_remotion_sheet_is_unchanged_one_frame_per_cell(tmp_path):
    out = str(tmp_path)
    os.makedirs(os.path.join(out, "_keyframes", "motion"))
    json.dump({"meta": {"renderer": "remotion"}, "slides": [{"index": 1, "shot": "SplitFlap"}, {"index": 2, "shot": "TermSpace"}]},
              open(os.path.join(out, "storyboard.json"), "w"))
    for i in (1, 2):
        Image.new("RGB", (1920, 1080), (30, 30, 30)).save(os.path.join(out, "_keyframes", "scene_%02d.png" % i))
        Image.new("RGB", (1920, 1080), (90, 30, 30)).save(os.path.join(out, "_keyframes", "motion", "scene_%02d.png" % i))
    _p, n, size = contact_sheet.build(out)
    assert n == 2 and contact_sheet.labels(out) == {1: "SplitFlap", 2: "TermSpace"}
    assert size[0] == 5 * (320 + 6) + 6


# ── the brief ──────────────────────────────────────────────────────────────────────────────────────────

def test_the_html_brief_is_a_real_brief(tmp_path, monkeypatch):
    import critic_brief
    calls = []
    monkeypatch.setattr(critic_brief, "_run", lambda script, *a, **k: calls.append(script) or "(stubbed %s)" % script)
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    text = critic_brief.build(out)
    assert "agents/design-critic.md" in text and "H-dimensions" in text
    assert "not a `remotion` film" not in text
    for script in ("keyframe_qa.py", "validate.py", "check_av.py", "rhythm_qa.py", "pedagogy_qa.py", "voice_qa.py"):
        assert script in calls, (script, calls)
    assert "shot_proof.py" not in calls and "text_safe_qa.py" not in calls
    fast = text[text.index("**Review depth"):].split("\n")[0]
    assert "critic-av.md's lens (H7)" in fast and "USER" in fast and "never as a FAIL" in fast, fast
    assert "Routes to confirm (H8)" in text and "beat 1 · BESPOKE" in text
    assert "| 1 | html | BESPOKE | pages/scene_01.html |" in text
    assert "No `_frames/` frames" in text, "no out.mp4: the brief must say H7 has nothing to read"
    # a gate main() already ran is not run twice
    calls.clear()
    text = critic_brief.build(out, {"keyframe_qa.py": "(already ran)"})
    assert "keyframe_qa.py" not in calls and "(already ran)" in text


def _tiny_mp4(path, seconds=2.0):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=160x90:rate=10:duration=%s" % seconds, "-pix_fmt", "yuv420p", path], check=True)


def test_the_brief_runs_keyframe_qa_first_pulls_delivered_frames_and_records_the_render(tmp_path, monkeypatch):
    import critic_brief
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    _tiny_mp4(os.path.join(out, "out.mp4"))
    open(os.path.join(out, "out.srt"), "w").write("1\n00:00:00,000 --> 00:00:01,000\nLine 1.\n")
    order = []

    def fake_run(script, out_dir, *a, **k):
        order.append(script)
        if script == "keyframe_qa.py":       # it re-shoots every page, in a colour the old strips never had
            for i in (1, 2):
                _strip(os.path.join(out_dir, "_keyframes", "scene_%02d.png" % i), colour=(200, 40, 40))
        return "(stubbed %s)" % script
    monkeypatch.setattr(critic_brief, "_run", fake_run)
    assert critic_brief.main([out]) == 0
    assert order[0] == "keyframe_qa.py" and order.count("keyframe_qa.py") == 1, order
    px = Image.open(os.path.join(out, cl.CONTACT_SHEET)).convert("RGB").getpixel((20, 20))
    assert px[0] > 150 and px[1] < 90, ("the sheet shows the strips from BEFORE keyframe_qa re-shot the pages", px)
    assert sorted(os.listdir(os.path.join(out, "_frames"))) == ["scene_01.png", "scene_02.png"]
    assert cl.render_id(out) in cl.history_shas(out)
    text = open(os.path.join(out, "_critic_brief.md"), encoding="utf-8").read()
    assert "2 frame(s), from `out.mp4`" in text


# ── NOT_DELIVERED.md on the HTML tier ──────────────────────────────────────────────────────────────────

@pytest.fixture
def html_render_board(tmp_path, fixtures_dir, monkeypatch):
    """A real render.py board (the deck fixture, voiced offline by `say`) whose first beat is an HTML page. The page
    is drawn as its slide image (monkeypatched), so the test needs ffmpeg and say but no Chrome."""
    import _common
    if not (_common.have_tool("say") and _common.have_tool("ffmpeg")):
        pytest.skip("needs say + ffmpeg")
    import ingest, tts, render, storyboard as sb
    out = str(tmp_path / "proj")
    ingest.ingest(os.path.join(fixtures_dir, "deck.pdf"), out)
    data = sb.load(os.path.join(out, "storyboard.json"))
    data["meta"]["voice"] = "say:Samantha"
    for s in data["slides"]:
        s["narration"] = "This is slide %d." % s["index"]
    sb.save(data, os.path.join(out, "storyboard.json"))
    tts.synthesize(out)
    data = sb.load(os.path.join(out, "storyboard.json"))
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    open(os.path.join(out, "pages", "scene_01.html"), "w").write("<!doctype html><html><body>x</body></html>")
    slides_only = json.loads(json.dumps(data))
    data["slides"][0]["type"] = "html"
    data["slides"][0]["props"] = {"html": "pages/scene_01.html"}
    sb.save(data, os.path.join(out, "storyboard.json"))
    orig = render._render_slide
    monkeypatch.setattr(render, "_render_slide", lambda slide, *a, **k: orig(dict(slide, type="slide"), *a, **k))
    return out, slides_only


def test_a_full_html_render_leaves_not_delivered_and_the_sample_and_preview_leave_it_alone(html_render_board):
    import render
    import storyboard as sb
    out, slides_only = html_render_board
    nd = os.path.join(out, "NOT_DELIVERED.md")
    render.render(out, sample=1)
    render.render(out, preview=True)
    assert not os.path.exists(nd), "the sample / preview wrote the delivery marker"
    render.render(out)
    text = open(nd, encoding="utf-8").read()
    assert "critic_brief.py" in text and "design-critic.md" in text and "--final" in text
    open(nd, "w").write("# sentinel\n")
    render.render(out, sample=1)
    render.render(out, preview=True)
    assert open(nd).read() == "# sentinel\n", "the sample / preview rewrote or removed the marker"
    # the 原样配音 tier has no ledger to clear a marker, so its render writes none
    os.remove(nd)
    sb.save(slides_only, os.path.join(out, "storyboard.json"))
    render.render(out)
    assert not os.path.exists(nd)


def test_final_clears_the_marker_on_the_html_tier(tmp_path):
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    cl.record_render(out)
    _ledger(out, routes=[{"beat": 1, "route": "bespoke", "visible": True, "evidence": "_keyframes/scene_01.png"}])
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").write("# not yet\n")
    p = subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    assert p.returncode == 1 and "no machine-gate exit codes" in p.stdout, "delivered with no gate run"
    cl.record_render(out, gates={cl.gate_name(s, a): {"exit": 0, "blocking": b}
                                 for _l, s, a, _t, b in cl.delivery_gates(out)})
    assert [s for _l, s, _a, _t, _b in cl.delivery_gates(out)][0] == "keyframe_qa.py"
    p = subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    assert p.returncode == 0 and "html tier" in p.stdout and "design-critic" in p.stdout, p.stdout
    assert not os.path.exists(os.path.join(out, "NOT_DELIVERED.md")), p.stdout


# ── the docs say what the code does ────────────────────────────────────────────────────────────────────

def test_the_docs_describe_the_pin_and_the_never_accepted_findings_the_code_enforces():
    import glob
    docs = ["SKILL.md"] + [os.path.relpath(p, _ROOT) for p in glob.glob(os.path.join(_ROOT, "agents", "*.md"))
                           + glob.glob(os.path.join(_ROOT, "references", "*.md"))]
    for rel in docs:
        src = open(os.path.join(_ROOT, rel), encoding="utf-8").read()
        # the pin is the render id (sheet + out.mp4 + out.srt); a doc telling the reader to pin the sheet alone
        # writes exactly the pin critic_ledger.py now refuses
        assert "sha256 of _contact_sheet.png" not in src and "contact_sheet_sha256" not in src, rel
    skill = open(os.path.join(_ROOT, "SKILL.md"), encoding="utf-8").read()
    # the code never accepts faithfulness/sourcing (S3 / H1) — and nothing else; A/V sync is check_av's gate
    assert cl.never_accepted() == {"S3"}
    assert "never on an A/V sync or faithfulness finding" not in skill
    row = next(l for l in skill.split("\n") if l.startswith("| step 9e critic-av"))
    assert "faithfulness or sourcing" in row and "check_av.py" in row, row


def test_a_failed_frame_pull_leaves_no_partial_set_for_the_brief_to_cite(tmp_path, monkeypatch):
    import critic_brief
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    _tiny_mp4(os.path.join(out, "out.mp4"))
    monkeypatch.setattr(critic_brief, "_run", lambda script, *a, **k: "(stubbed %s)" % script)
    assert critic_brief.main([out]) == 0
    assert len(os.listdir(os.path.join(out, "_frames"))) == 2
    b = json.load(open(os.path.join(out, "storyboard.json")))
    del b["slides"][1]["duration"]                   # beat 2 can no longer be located in out.mp4
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    assert critic_brief.main([out]) == 0
    assert [f for f in os.listdir(os.path.join(out, "_frames")) if f.endswith(".png")] == []
    assert "No `_frames/` frames" in open(os.path.join(out, "_critic_brief.md"), encoding="utf-8").read()


# ── waived gate findings on the HTML tier: H6 owns energy; a legacy film still confirms its waivers ─────────

def test_an_html_waiver_row_binds_to_h6_and_a_legacy_film_still_needs_it(tmp_path):
    import validate as v
    energy = {"energy_waiver": "a quiet editorial film, held to its narration"}
    out = _html_film(tmp_path, review={"tier": "thorough", "user_answer": "thorough", "preselected": "fast"},
                     fits={2: SHARES}, meta_extra=energy)
    cl.record_render(out)
    routes = [{"beat": 1, "route": "bespoke", "visible": True, "evidence": "_keyframes/scene_01.png"}]
    led = _ledger(out, routes=routes)
    assert any("`waivers` is missing" in e for e in cl.validate(out)[0])
    led = _ledger(out, routes=routes, verdict="REVISE",
                  waivers=[{"key": "energy_waiver", "holds": False, "evidence": "_keyframes/scene_02.png"}])
    assert any("H6, which owns it, does not fail" in e for e in cl.validate(out)[0])
    i = [r["id"] for r in led["rows"]].index("H6")
    led["rows"][i] = {"id": "H6", "verdict": "fail", "evidence": "_keyframes/scene_02.png", "fix": "cue the reveals"}
    json.dump(led, open(os.path.join(out, cl.LEDGER_NAME), "w"))
    assert not cl.validate(out)[0], cl.validate(out)[0]
    # a film whose design the user KEPT (made before design-first) needs no route rows for the kept pages — and
    # still confirms its waivers: the keep waives design-first, nothing else
    b = json.load(open(os.path.join(out, "storyboard.json")))
    for sl in b["slides"]:
        sl.pop("shot_fit", None)
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    assert v.keep_design(out, "keep it as it is")[0]
    cl.record_render(out)
    _ledger(out)
    errs = cl.validate(out)[0]
    assert not any("`routes`" in e for e in errs) and any("`waivers` is missing" in e for e in errs), errs


# ── M7: one tier definition, matching validate's behaviour before the tiers were named ──────────────────────

def test_one_tier_definition_for_every_renderer_value(tmp_path):
    import validate as v
    html = [{"index": 1, "type": "html", "props": {"html": "pages/scene_01.html"}}]
    slide = [{"index": 1, "type": "slide", "image": "s.png"}]
    cases = [({"renderer": "remotion"}, html, "remotion"), ({"renderer": "remotion-bespoke"}, html, "remotion"),
             ({"renderer": "local"}, html, "html"), ({}, html, "html"),
             # remotion-legacy cannot render, but its pages are pages: validate gave it the HTML floor before
             ({"renderer": "remotion-legacy"}, html, "html"),
             ({"renderer": "local"}, slide, None), ({"renderer": "remotion-legacy"}, slide, None)]
    for meta, slides, want in cases:
        assert v.film_tier(meta, slides) == want, (meta, want)
        out = tmp_path / ("t%d" % cases.index((meta, slides, want)))
        out.mkdir()
        (out / "storyboard.json").write_text(json.dumps({"meta": meta, "slides": slides}))
        assert cl.film_tier(str(out)) == want, (meta, want)
    # and the floor runs on a remotion-legacy board with pages, as it did before this branch
    meta, slides, outd = __import__("test_html_design_first")._film(tmp_path / "leg", [STOCK, STOCK])
    meta["renderer"] = "remotion-legacy"
    errs = []
    v._design_first(meta, slides, errs, [], outd, v.film_tier(meta, slides))
    assert any(e.startswith("design-first") for e in errs), errs


# ── M1 / M6: nothing from an earlier film is presented as this one ─────────────────────────────────────────

def test_no_out_mp4_means_no_delivered_frames_from_an_earlier_film(tmp_path, monkeypatch):
    import critic_brief
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    os.makedirs(os.path.join(out, "_frames"))
    for i in (1, 2, 3, 4, 5, 6):
        Image.new("RGB", (16, 9), (9, 9, 9)).save(os.path.join(out, "_frames", "scene_%02d.png" % i))
    monkeypatch.setattr(critic_brief, "_run", lambda s, *a, **k: critic_brief.GateOutput("(stub %s)" % s, 0))
    assert critic_brief.main([out]) == 0
    assert [f for f in os.listdir(os.path.join(out, "_frames")) if f.endswith(".png")] == []
    assert "No `_frames/` frames" in open(os.path.join(out, "_critic_brief.md"), encoding="utf-8").read()


def test_no_sheet_means_no_render_recorded_and_no_old_sheet_left(tmp_path, monkeypatch, capsys):
    import critic_brief
    import shutil
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    shutil.rmtree(os.path.join(out, "_keyframes"))          # nothing to build a sheet from; an OLD sheet is left
    assert os.path.exists(os.path.join(out, cl.CONTACT_SHEET))
    monkeypatch.setattr(critic_brief, "_run", lambda s, *a, **k: critic_brief.GateOutput("(stub %s)" % s, 0))
    assert critic_brief.main([out]) == 0
    said = capsys.readouterr().out
    assert "render NOT recorded: the contact sheet was not built" in said, said
    assert not os.path.exists(os.path.join(out, cl.HISTORY))
    assert not os.path.exists(os.path.join(out, cl.CONTACT_SHEET)), "an old sheet would pin this film to a dead one"


# ── determinism: an unchanged film briefed twice is the same render, and keyframe_qa runs only on change ───

def test_briefing_an_unchanged_film_twice_changes_nothing_and_reshoots_only_on_change(tmp_path, monkeypatch):
    import critic_brief
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    calls = []

    def fake(script, out_dir, *a, **k):
        calls.append(script)
        if script == "keyframe_qa.py":
            for i in (1, 2):
                _strip(os.path.join(out_dir, "_keyframes", "scene_%02d.png" % i), colour=(200, 40, 40))
        return critic_brief.GateOutput("(stub %s)" % script, 0)
    monkeypatch.setattr(critic_brief, "_run", fake)
    assert critic_brief.main([out]) == 0
    rid, hist = cl.render_id(out), open(os.path.join(out, cl.HISTORY)).read()
    assert calls.count("keyframe_qa.py") == 1
    gates = cl.gate_record(out, rid)
    assert gates["keyframe_qa.py"] == {"exit": 0, "blocking": True}
    assert gates["voice_qa.py"]["blocking"] is False and "validate.py" in gates
    # the review answer is written to the board between briefs: not a keyframe input
    b = json.load(open(os.path.join(out, "storyboard.json")))
    b["meta"]["review"]["user_answer"] = "fast, please"
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    calls.clear()
    assert critic_brief.main([out]) == 0
    assert "keyframe_qa.py" not in calls, "keyframe_qa re-shot a film none of whose inputs changed"
    assert cl.render_id(out) == rid and open(os.path.join(out, cl.HISTORY)).read() == hist
    assert "(not re-run" in open(os.path.join(out, "_critic_brief.md"), encoding="utf-8").read()
    # a page changes: the pages are re-shot
    with open(os.path.join(out, "pages", "scene_02.html"), "a") as fh:
        fh.write("<!-- edited -->")
    calls.clear()
    assert critic_brief.main([out]) == 0
    assert calls.count("keyframe_qa.py") == 1


def test_the_brief_and_final_say_what_the_user_kept(tmp_path, monkeypatch):
    import critic_brief
    import validate as v
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"})
    assert v.keep_design(out, "keep it as it is, just fix the line")[0]
    monkeypatch.setattr(critic_brief, "_run", lambda s, *a, **k: critic_brief.GateOutput("(stub %s)" % s, 0))
    assert critic_brief.main([out]) == 0
    text = open(os.path.join(out, "_critic_brief.md"), encoding="utf-8").read()
    assert "kept by the user's decision for beat(s) 1, 2" in text
    _ledger(out)
    open(os.path.join(out, "NOT_DELIVERED.md"), "w").write("# not yet\n")
    p = subprocess.run([sys.executable, cl.__file__, out, "--final"], capture_output=True, text=True)
    assert p.returncode == 0 and "design-first: kept by the user's decision for beat(s) 1, 2" in p.stdout, p.stdout


def test_a_page_that_reads_another_films_theme_is_an_error(tmp_path):
    # pages link assets by ABSOLUTE file:// path, so a copied film kept reading the original's theme.css — measured
    # on a copy of the skill's own jev-html: an edit to the copy's theme never reached its render
    import validate as v
    orig, copy = tmp_path / "orig", tmp_path / "copy"
    for d in (orig, copy):
        (d / "pages").mkdir(parents=True)
        (d / "storyboard.json").write_text("{}")
        (d / "theme.css").write_text(":root{}")
    (orig / "photo.png").write_bytes(b"x")
    page = ('<html><head><link rel="stylesheet" href="file://%s"></head><body><img src="file://%s"></body></html>'
            % (orig / "theme.css", orig / "photo.png"))
    (copy / "pages" / "scene_01.html").write_text(page)
    errs, warns = [], []
    v._check_html_assets(str(copy), "pages/scene_01.html", False, 1, errs, warns)
    assert any("ANOTHER film's theme.css" in e and str(orig) in e for e in errs), errs
    assert any("a file of another film" in w and "photo.png" in w for w in warns), warns
    # the original reading its own files is clean
    (orig / "pages" / "scene_01.html").write_text(page)
    errs, warns = [], []
    v._check_html_assets(str(orig), "pages/scene_01.html", False, 1, errs, warns)
    assert not any("another film" in x.lower() for x in errs + warns), (errs, warns)


def test_the_brief_says_where_each_beats_facts_come_from(tmp_path):
    # both critics' methods said the brief carried it and neither did: the first delivery critic on this tier traced
    # every page by hand-grepping sources/*.txt
    import critic_brief
    out = tmp_path / "film"
    (out / "sources").mkdir(parents=True)
    json.dump({"wiki": {"title": "Wikipedia: Jev", "tier": "secondary", "as_of": "2026-09-15"}},
              open(out / "sources" / "index.json", "w"))
    (out / "sources" / "wiki.txt").write_text("Jev returns typed values.")
    json.dump({"evidence": [{"claim": "Jev returns typed values", "source_ref": "wiki#returns typed values"},
                            {"claim": "an unsourced claim"}]}, open(out / "brief.json", "w"))
    json.dump({"beats": [{"source_ref": "wiki#returns typed values · ghost#nowhere"}, {"stage": "land"}]},
              open(out / "content_plan.json", "w"))
    text = "\n".join(critic_brief._sources_lines(str(out), 2))
    assert "beat 1: `wiki` «returns typed values» · `ghost` (NOT in sources/index.json)" in text, text
    assert "beat 2: **no source_ref**" in text and "an unsourced claim ← **no source_ref**" in text, text
    assert "`wiki` Wikipedia: Jev (secondary, as of 2026-09-15)" in text and "missing" not in text, text
    # an older plan with no per-beat refs says so rather than dropping the section
    json.dump({"beats": [{"stage": "ground"}]}, open(out / "content_plan.json", "w"))
    os.remove(out / "sources" / "wiki.txt")
    text = "\n".join(critic_brief._sources_lines(str(out), 1))
    assert "NO per-beat `source_ref`" in text and "sources/wiki.txt is missing" in text, text


def test_the_html_brief_states_the_caption_band_in_pixels():
    import critic_brief
    from _caption_band import caption_band_px
    assert "y ≥ %d" % (1080 - caption_band_px(1920, 1080)) in critic_brief._caption_band_line({})
    assert "1080x1920" in critic_brief._caption_band_line({"aspect": "9:16"})


def test_a_brief_after_gates_on_the_same_render_reuses_them_and_any_input_change_reruns(tmp_path, monkeypatch):
    # `--gates` before the review question, then the brief on the same render, ran every delivery gate twice — two to
    # three and a half minutes re-measuring a film nobody had touched
    import critic_brief
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    calls, codes = [], {}

    def fake(script, out_dir, *a, **k):
        calls.append(cl.gate_name(script, a))
        if script == "keyframe_qa.py":
            for i in (1, 2):
                _strip(os.path.join(out_dir, "_keyframes", "scene_%02d.png" % i), colour=(200, 40, 40))
        return critic_brief.GateOutput("(stub %s)" % script, codes.get(script, 0))
    monkeypatch.setattr(critic_brief, "_run", fake)
    need = sorted(cl.gate_name(s, a) for _l, s, a, _t, _b in cl.delivery_gates(out))
    assert critic_brief.main([out, "--gates"]) == 0 and sorted(calls) == need
    calls.clear()
    assert critic_brief.main([out]) == 0
    assert calls == [], "the brief re-ran gates --gates had just run on this render"
    assert sorted(cl.gate_record(out, cl.render_id(out))) == need, "the reused verdicts are still recorded"
    brief = open(os.path.join(out, "_critic_brief.md"), encoding="utf-8").read()
    assert brief.count("not re-run") >= len(need) - 1 and "(stub validate.py)" in brief
    # the review answer is written between the two runs: not an input to any gate
    b = json.load(open(os.path.join(out, "storyboard.json")))
    b["meta"]["review"]["user_answer"] = "fast, please"
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    calls.clear()
    critic_brief.main([out])
    assert calls == [], calls
    # anything else on the board is: every gate runs again
    b["slides"][0]["narration"] = b["slides"][0].get("narration", "") + " 再说一句。"
    json.dump(b, open(os.path.join(out, "storyboard.json"), "w"))
    calls.clear()
    critic_brief.main([out])
    assert sorted(calls) == need, calls
    # so is a file nobody listed — inputs are everything but the review's and the gates' own outputs
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    open(os.path.join(out, "media", "new.png"), "wb").write(b"x")
    calls.clear()
    critic_brief.main([out])
    assert "validate.py" in calls, calls
    # a gate that did not finish is never reused (an input changes first, so every gate really runs)
    codes["check_av.py"] = "timeout"
    open(os.path.join(out, "media", "another.png"), "wb").write(b"y")
    calls.clear()
    critic_brief.main([out, "--gates"])
    assert "check_av.py" in calls, calls
    calls.clear()
    critic_brief.main([out])
    assert calls == ["check_av.py"], calls


def test_the_gate_fingerprint_sees_the_skills_underscore_files_and_survives_a_dangling_link(tmp_path, monkeypatch):
    """`_`-names were skipped in the SKILL tree too, so editing scripts/_common.py replayed a gate's old PASS; and a
    dangling link in the film folder crashed the brief before any gate ran."""
    import critic_brief
    skill = tmp_path / "skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "scripts" / "_common.py").write_text("A = 1\n")
    (skill / "scripts" / "__pycache__").mkdir()
    (skill / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    film = tmp_path / "film"
    film.mkdir()
    (film / "storyboard.json").write_text("{}")
    os.symlink(str(tmp_path / "gone.png"), str(film / "pic.png"))
    monkeypatch.setattr(critic_brief, "_HERE", str(skill / "scripts"))
    a = critic_brief.gate_inputs(str(film))
    (skill / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"\x01")
    assert critic_brief.gate_inputs(str(film)) == a, "a bytecode cache is not an input"
    (skill / "scripts" / "_common.py").write_text("A = 2\n")
    assert critic_brief.gate_inputs(str(film)) != a, "an edit to _common.py must change the fingerprint"


def test_a_failed_gate_is_run_again_not_replayed(tmp_path, monkeypatch):
    """A failure can be the environment's (a flaky browser, a missing tool) — the fingerprint cannot see it, so only a
    PASS is reused."""
    import critic_brief
    out = _html_film(tmp_path, review={"tier": "fast", "user_answer": "fast", "preselected": "fast"},
                     fits={2: SHARES})
    calls = []

    def fake(script, out_dir, *a, **k):
        calls.append(script)
        if script == "keyframe_qa.py":
            for i in (1, 2):
                _strip(os.path.join(out_dir, "_keyframes", "scene_%02d.png" % i), colour=(200, 40, 40))
        return critic_brief.GateOutput("(stub %s)" % script, 1 if script == "rhythm_qa.py" else 0)
    monkeypatch.setattr(critic_brief, "_run", fake)
    critic_brief.main([out, "--gates"])
    assert "rhythm_qa.py" in calls
    calls.clear()
    critic_brief.main([out, "--gates"])
    assert calls == ["rhythm_qa.py"], calls
