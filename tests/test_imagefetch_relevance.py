"""imagefetch takes a picture only when the file's own record names the subject.

The 2026-10-30 generality validation asked Commons for "lever escapement" and got a piano action. The fixtures here
are the records Commons actually returned (titles, descriptions, categories copied from the live answer), in the
order the API delivers them: `pages` keyed by page id, the relevance rank in a separate `index`."""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import imagefetch as F


def _page(title, index, desc="", cats="", obj=None, width=1600, orig=None, mime="image/jpeg", thumburl=None,
          lic="CC BY-SA 3.0"):
    orig = orig or width
    return {"title": title, "index": index, "imageinfo": [{
        "thumburl": thumburl or "https://upload.example/%d/%dpx-x.jpg" % (index, width),
        "url": "https://upload.example/%d/full.jpg" % index, "descriptionurl": "https://commons.example/%d" % index,
        "mime": mime, "width": orig, "height": orig * 2 // 3, "thumbwidth": width, "thumbheight": width * 2 // 3,
        "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": "A. Person"},
                        "ObjectName": {"value": obj or title[5:].rsplit(".", 1)[0]},
                        "ImageDescription": {"value": desc}, "Categories": {"value": cats}}}]}


# page ids ascend with upload date; the piano (an 1884 Britannica plate) is the oldest upload and Commons' 8th hit
LEVER = {"query": {"pages": {
    "1001": _page("File:Britannica Pianoforte Erard Double Escapement Action.png", 8, mime="image/png",
                  desc="Sébastien Érard's double escapement piano action of 1884. The double escapement or repetition "
                       "is effected by a spring in the balance pressing the hinged lever upwards",
                  cats="Sébastien Érard|Piano action|PD Britannica|Repetition actions"),
    "2002": _page("File:Chinese movement escapement and jewels.jpg", 2,
                  desc="The balance wheel, pallet fork, escapement wheel, and a few of the gears of a Chinese movement",
                  cats="GFDL|Balance wheels|Self-published work|Lever escapements"),
    "3003": _page("File:Lever of a Watch Lever Escapement.jpg", 1, desc="Pallet fork of a Watch Lever escapement",
                  cats="Flickr images reviewed by FlickreviewR|Lever escapements"),
}}}


def _jpeg(w=1600, h=1000):
    from PIL import Image
    buf = io.BytesIO()
    Image.effect_noise((w, h), 40).convert("RGB").save(buf, "JPEG", quality=60)
    return buf.getvalue()


def _serve(monkeypatch, answer, image=None):
    image = image if image is not None else _jpeg()
    def urlopen(req, timeout=None):
        url = req.full_url
        return io.BytesIO(json.dumps(answer).encode() if "api.php" in url else image)
    monkeypatch.setattr(F.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(F, "_sleep", lambda s: None)


def test_search_keeps_commons_rank_not_page_id_order(monkeypatch):
    _serve(monkeypatch, LEVER)
    titles = [c["title"] for c in F.search("lever escapement")]
    assert titles[0] == "File:Lever of a Watch Lever Escapement.jpg", titles
    assert titles[-1].startswith("File:Britannica Pianoforte"), titles


def test_lever_escapement_never_returns_the_piano(tmp_path, monkeypatch):
    # the piano alone: its title says escapement, its prose says "hinged lever" — neither names a lever escapement
    only_piano = {"query": {"pages": {"1001": LEVER["query"]["pages"]["1001"]}}}
    _serve(monkeypatch, only_piano)
    why = []
    assert F.fetch("lever escapement", str(tmp_path / "a.jpg"), why=why) is None
    assert not (tmp_path / "a.jpg").exists()
    assert any("Pianoforte" in w and "'lever'" in w and "description prose" in w for w in why), why
    assert any(w.startswith("hint:") and "--require escapement" in w for w in why), why
    # with the real answer, the real lever escapement is taken and the sidecar says which field named each term
    _serve(monkeypatch, LEVER)
    meta = F.fetch("lever escapement", str(tmp_path / "b.jpg"))
    assert meta["title"] == "File:Lever of a Watch Lever Escapement.jpg"
    assert meta["relevance"]["where"] == {"lever": "title", "escapement": "title"}


@pytest.mark.parametrize("query,cand,ok", [
    # categories are statements about the picture
    ("lever escapement", {"title": "File:Chinese movement escapement and jewels.jpg",
                          "categories": "Balance wheels|Lever escapements"}, True),
    # a description attests only with the whole phrase in order
    ("lever escapement", {"title": "File:Frederique Constant escapement wheel in Silicium.jpg",
                          "description": "uses less power than a standard lever escapement"}, True),
    ("balance hairspring", {"title": "File:Alarm Clock Balance Wheel.jpg",
                            "description": "the hairspring is visible under the balance"}, False),
    # plural of a short word, accent and sharp-s folding, a compound written as two words
    ("red fox", {"title": "File:Common red foxes in the snow.jpg"}, True),
    ("Glashütte", {"title": "File:Glashuette station.jpg"}, False),        # ue is not u-umlaut folded: no guess
    ("Glashütte", {"title": "File:Glashütte (Sachsen) 01.JPG"}, True),
    ("Großglockner", {"title": "File:Grossglockner north face.jpg"}, True),
    ("hairspring", {"title": "File:Watch hair spring macro.jpg"}, True),
    # CJK: attested where a record carries the glyphs, here a Japanese description
    ("富士山", {"title": "File:Mount Fuji from Mount Aino.jpg", "description": "愛鷹山から見た富士山"}, True),
    ("富士山", {"title": "File:Mount Fuji at sunset.jpg"}, False),
    # a format word is not required; the subject is
    ("Swiss lever escapement diagram", {"title": "File:Anker 02.svg",
                                         "categories": "Swiss lever escapements|Self-published work"}, True),
    # an ambiguous term passes for every sense — the query must name the sense
    ("jaguar cat", {"title": "File:1970 Jaguar E-Type Roadster.jpg", "categories": "Jaguar E-Type"}, False),
])
def test_relevance_judges_the_record(query, cand, ok):
    req, fmt = F.key_terms(query)
    assert F.relevance(cand, req, fmt)["ok"] is ok, F.relevance(cand, req, fmt)


def test_a_query_that_names_no_subject_is_refused_loudly():
    with pytest.raises(ValueError, match="names no subject"):
        F.key_terms("a photo of the diagram")


def test_require_admits_a_record_missing_only_a_qualifier(tmp_path, monkeypatch):
    ans = {"query": {"pages": {"7": _page("File:Pocket Watch (48709221118).jpg", 3,
                                          desc="Antique pocket watch, movement with balance visible")}}}
    _serve(monkeypatch, ans)
    assert F.fetch("pocket watch movement balance", str(tmp_path / "a.jpg")) is None
    meta = F.fetch("pocket watch movement balance", str(tmp_path / "a.jpg"), require=["pocket watch"])
    assert meta and meta["relevance"]["terms"] == ["pocket", "watch"]


def test_the_thumb_url_names_the_pixels_not_thumbwidth(monkeypatch):
    # a 1255 px tiff asked for at 1600: thumbwidth says 1600, the URL Commons hands back is a 960 px jpeg
    tif = _page("File:Unruh-Spirale-Schwingsystem.tif", 1, mime="image/tiff", orig=1255,
                thumburl="https://thumb.example/5/59/U.tif/lossy-page1-960px-U.tif.jpg?utm_source=x")
    _serve(monkeypatch, {"query": {"pages": {"1": tif}}})
    got = F.search("Unruh Spirale")[0]
    assert got["width"] == 960, got["width"]
    assert F.fetch("Unruh Spirale", "/nonexistent/x.jpg", min_width=1000) is None   # refused before any download


def test_min_width_is_judged_on_the_downloaded_file_and_prefer_cannot_bypass_it(tmp_path, monkeypatch):
    from PIL import Image
    buf = io.BytesIO()
    Image.effect_noise((417, 277), 64).convert("RGB").save(buf, "PNG")       # noise: a real-sized file
    # the API claims 1600 (no px in the URL, no smaller original reported): only the file can say it is 417
    lie = _page("File:Tokyo railway map small.png", 1, mime="image/png", thumburl="https://u.example/plain.png")
    lie["imageinfo"][0].pop("width")
    _serve(monkeypatch, {"query": {"pages": {"1": lie}}}, image=buf.getvalue())
    why = []
    out = tmp_path / "m.png"
    assert F.fetch("Tokyo railway map", str(out), prefer="map", min_width=800, why=why) is None
    assert not out.exists() and any("417 px wide" in w for w in why), why


def test_a_download_that_is_not_an_image_is_never_handed_on(tmp_path, monkeypatch):
    # an HTML error page served with a 200: the API's width claim cannot stand in for the file
    _serve(monkeypatch, LEVER, image=b"<html>" + b"x" * 4000)
    why = []
    assert F.fetch("lever escapement", str(tmp_path / "e.jpg"), why=why) is None
    assert not (tmp_path / "e.jpg").exists() and any("not a readable image" in w for w in why), why
