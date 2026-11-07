"""A brand mark is the product's own, read off the mark itself.

The WorkBuddy film (2026-11-07) took refs/logo.DFsvaNxA.svg from the product's own docs site as WorkBuddy's mark and
built the whole palette from it; the file was CodeBuddy's, a sibling product's, and nothing noticed until a contact
sheet showed "CODE-BUDDY". A file name and the page it came from do not say whose mark it is; the mark's own letters
do. scripts/brand_mark.py reads every mark the film uses and records what it says beside it; validate refuses a mark
that was never read, one that names another product, and a symbol with no words that nobody confirmed.
"""
import hashlib
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import brand_mark as bm   # noqa: E402

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 116 40"><path d="M12.5 3.25C18.1 3.25 22.4 7.6 22.4 13.2'
       'L22.4 26.8C22.4 32.4 18.1 36.75 12.5 36.75Z" fill="#0EC8A9"/></svg>')


# ── whose name the mark's letters spell ──────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name,reads,ok", [
    ("WorkBuddy", ["WORK", "BUDDY"], True),              # a stacked wordmark reads as two lines
    ("WorkBuddy", ["WorkBuddy>_"], True),                # the mark's own glyphs around the name
    ("WorkBuddy", ["W0RKBUDDY"], True),                  # one OCR slip is not another product
    ("WorkBuddy", ["CODE-BUDDY"], False),                # the sibling product
    ("WorkBuddy", ["CODE", "BUDDY"], False),
    ("Grok Bot", ["grok"], False),                       # half the name is not the name
    ("扣子", ["扣子空间"], True),
    ("扣子", ["豆包"], False),
])
def test_the_name_is_read_off_the_mark(name, reads, ok):
    assert bm.matches(name, reads) is ok


@pytest.mark.parametrize("reads,want", [
    (["WORK", "BUDDY"], "match"), (["CODE-BUDDY"], "mismatch"), ([], "no-text"),
    (["31"], "no-text"),                                 # Google Calendar's icon carries the date, not a name
    (["•", ">_"], "no-text"),
])
def test_a_mark_with_no_letters_is_a_symbol_not_a_mismatch(reads, want):
    assert bm.verdict("WorkBuddy", reads) == want


def test_the_product_name_is_the_brand_s_then_the_product_field():
    assert bm.product_name({"brand": {"name": "Grok Bot"}, "product": "x"}) == "Grok Bot"
    assert bm.product_name({"product": "WorkBuddy"}) == "WorkBuddy"
    assert bm.product_name({}) is None


# ── which files are marks, and which the film uses ──────────────────────────────────────────────────────────────
def _film(tmp_path, meta=None, files=None):
    d = tmp_path / "film"
    (d / "workshop" / "shots").mkdir(parents=True)
    for rel, text in (files or {}).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (d / "storyboard.json").write_text(json.dumps({"meta": meta or {}, "slides": []}), encoding="utf-8")
    return str(d)


def test_marks_are_the_brand_folder_and_files_named_as_marks(tmp_path):
    d = _film(tmp_path, files={"assets/brand/wb.svg": SVG, "refs/logo.DFsvaNxA.svg": SVG, "refs/app_icon.png": "x",
                               "refs/create_task.png": "x", "media/photo.jpg": "x", "refs/notes.txt": "logo"})
    assert sorted(bm.candidates(d)) == ["assets/brand/wb.svg", "refs/app_icon.png", "refs/logo.DFsvaNxA.svg"]


def test_brand_in_a_file_s_name_is_not_a_mark(tmp_path):
    # the topic-to-video promo's media/films/sm-brand.jpg is a still of another film's end card, not a logo
    d = _film(tmp_path, files={"media/films/sm-brand.jpg": "x", "refs/brand-guide-photo.png": "x"})
    assert bm.candidates(d) == []


def test_a_third_party_mark_is_read_against_its_own_name(tmp_path):
    # the Grok Bot film shows Gmail's mark as a connected app: it must be Gmail's, not Grok Bot's
    d = _film(tmp_path, meta={"product": "Grok Bot"}, files={
        "media/logo_gmail.png": "x", "media/logo_gmail.png.json": json.dumps({"brand": "Gmail"}),
        "workshop/shots/kit.ts": "const s = 'media/logo_gmail.png';"})
    assert bm.expected_name(d, "media/logo_gmail.png", "Grok Bot") == "Gmail"
    _identity(d, "media/logo_gmail.png", name="Gmail", reads=["Gmail"], verdict="match")
    assert bm.lint(d) == ([], [])


def test_third_party_marks_alone_need_no_product_name(tmp_path):
    d = _film(tmp_path, files={
        "media/logo_gmail.png": "x", "media/logo_gmail.png.json": json.dumps({"brand": "Gmail"}),
        "workshop/shots/kit.ts": "const s = 'media/logo_gmail.png';"})
    _identity(d, "media/logo_gmail.png", name="Gmail", reads=["Gmail"], verdict="match")
    assert bm.lint(d) == ([], [])


def test_a_file_its_sidecar_calls_a_brand_mark_is_one_whatever_its_name(tmp_path):
    # the WorkBuddy mark was refs/workbuddy-black.bFkZ_JU-.svg: no mark word in its name, "brand mark" in its sidecar
    d = _film(tmp_path, files={"refs/codebuddy-black.svg": SVG,
                               "refs/codebuddy-black.svg.json": json.dumps({"use": "brand mark / UI reference"}),
                               "refs/sheet.png": "x", "refs/sheet.png.json": json.dumps({"use": "UI reference"})})
    assert bm.candidates(d) == ["refs/codebuddy-black.svg"]


def test_a_mark_inlined_into_the_workshop_s_code_is_used(tmp_path):
    d = _film(tmp_path, files={"refs/logo.a.svg": SVG,
                               "workshop/shots/kit.ts": "export const LOGO = `%s`;" % SVG})
    assert bm.used(d, "refs/logo.a.svg")


def test_a_mark_named_in_a_string_is_used_and_one_named_in_a_comment_is_not(tmp_path):
    d = _film(tmp_path, files={"refs/logo.a.svg": SVG, "refs/logo.b.svg": SVG.replace("12.5", "99.5"),
                               "workshop/shots/kit.ts": "// refs/logo.b.svg is the sibling product's: never use it\n"
                                                        "const src = staticFile('refs/logo.a.svg');"})
    assert bm.used(d, "refs/logo.a.svg")
    assert not bm.used(d, "refs/logo.b.svg")


def test_the_declared_brand_logo_is_used(tmp_path):
    d = _film(tmp_path, meta={"brand": {"logo": "assets/brand/x.png"}}, files={"assets/brand/x.png": "x"})
    assert bm.used(d, "assets/brand/x.png")


# ── what validate refuses ────────────────────────────────────────────────────────────────────────────────────
def _identity(d, rel, **kw):
    p = os.path.join(d, rel)
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
    side = p + ".json"
    meta = json.load(open(side)) if os.path.exists(side) else {}
    meta["identity"] = dict({"sha256": sha, "name": "WorkBuddy"}, **kw)
    json.dump(meta, open(side, "w"))


def _used_mark(tmp_path, meta=None):
    return _film(tmp_path, meta=dict({"product": "WorkBuddy"}, **(meta or {})),
                 files={"refs/logo.a.svg": SVG, "workshop/shots/kit.ts": "const s = 'refs/logo.a.svg';"})


def test_a_used_mark_that_was_never_read_is_an_error(tmp_path):
    errors, _w = bm.lint(_used_mark(tmp_path))
    assert errors and "brand_mark.py" in errors[0] and "refs/logo.a.svg" in errors[0]


def test_a_mark_that_names_another_product_is_an_error_quoting_what_it_says(tmp_path):
    d = _used_mark(tmp_path)
    _identity(d, "refs/logo.a.svg", reads=["CODE-BUDDY"], verdict="mismatch")
    errors, _w = bm.lint(d)
    assert errors and "CODE-BUDDY" in errors[0] and "WorkBuddy" in errors[0]


def test_a_mark_that_reads_the_product_passes(tmp_path):
    d = _used_mark(tmp_path)
    _identity(d, "refs/logo.a.svg", reads=["WORK", "BUDDY"], verdict="match")
    assert bm.lint(d) == ([], [])


def test_a_symbol_with_no_words_needs_someone_to_say_whose_it_is(tmp_path):
    d = _used_mark(tmp_path)
    _identity(d, "refs/logo.a.svg", reads=[], verdict="no-text")
    errors, _w = bm.lint(d)
    assert errors and "confirmed" in errors[0]
    _identity(d, "refs/logo.a.svg", reads=[], verdict="no-text", confirmed="the user: 'yes, that's our app icon'")
    assert bm.lint(d) == ([], [])


def test_a_mark_changed_after_it_was_read_must_be_read_again(tmp_path):
    d = _used_mark(tmp_path)
    _identity(d, "refs/logo.a.svg", reads=["WORKBUDDY"], verdict="match")
    with open(os.path.join(d, "refs/logo.a.svg"), "a") as fh:
        fh.write("<!-- edited -->")
    errors, _w = bm.lint(d)
    assert errors and "changed" in errors[0]


def test_a_read_against_another_name_is_read_again(tmp_path):
    # the verdict was for a different product name: it says nothing about this one
    d = _used_mark(tmp_path, meta={"product": "CodeBuddy"})
    _identity(d, "refs/logo.a.svg", reads=["WORKBUDDY"], verdict="match")
    errors, _w = bm.lint(d)
    assert errors and "CodeBuddy" in errors[0]


def test_a_film_that_uses_a_mark_must_name_its_product(tmp_path):
    d = _film(tmp_path, files={"refs/logo.a.svg": SVG, "workshop/shots/kit.ts": "const s = 'refs/logo.a.svg';"})
    errors, _w = bm.lint(d)
    assert errors and "meta.product" in errors[0]


def test_a_film_with_no_mark_is_not_asked_anything(tmp_path):
    assert bm.lint(_film(tmp_path)) == ([], [])


# ── reading a real mark (macOS Vision or tesseract, and Chrome to rasterise an svg) ─────────────────────────────
_CAN_READ = bm.can_read()


@pytest.mark.skipif(not _CAN_READ, reason="needs text recognition and Chrome")
def test_a_wordmark_s_letters_are_read_and_another_product_is_caught(tmp_path):
    d = _film(tmp_path, meta={"product": "WorkBuddy"}, files={
        "refs/logo.code.svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100"><text x="10" y="70" '
                              'font-family="Helvetica" font-weight="700" font-size="64" fill="#6b4cf6">CODE-BUDDY</text>'
                              '</svg>',
        "workshop/shots/kit.ts": "const s = 'refs/logo.code.svg';"})
    res = bm.check(d)
    assert [r["verdict"] for r in res] == ["mismatch"]
    assert any("CODE" in t.upper() for t in res[0]["reads"])
    errors, _w = bm.lint(d)
    assert errors and "CODE" in errors[0].upper()


@pytest.mark.parametrize("renderer", ["remotion", "local"])
def test_validate_refuses_an_unread_mark_on_both_tiers(tmp_path, renderer):
    import validate as v
    d = _used_mark(tmp_path)
    board = {"meta": {"renderer": renderer, "product": "WorkBuddy"},
             "slides": [{"index": 1, "narration": "A sentence.", "duration": 5.0, "audio": "audio/01.mp3",
                         **({"shot": "KnowledgeGraph", "shot_props": {}} if renderer == "remotion" else
                            {"image": "frames/01.png"})}]}
    with open(os.path.join(d, "storyboard.json"), "w") as fh:
        json.dump(board, fh)
    errs = v.evaluate(board, d)["errors"]
    assert any(e.startswith("brand mark") and "refs/logo.a.svg" in e for e in errs), errs
