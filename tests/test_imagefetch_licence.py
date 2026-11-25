"""imagefetch keeps what a credit needs and what a licence does not clear (2026-11-25 imagery audit): a Commons
record's licence URL and restrictions travel into the picture's record and its film credit; a NASA item credited to
someone else is not "Public domain (NASA)" and is refused by the licence gate."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import imagefetch as F  # noqa: E402


def test_a_commons_record_keeps_its_licence_url_and_restrictions(monkeypatch):
    em = {"LicenseShortName": {"value": "CC BY-SA 4.0"}, "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
          "AttributionRequired": {"value": "true"}, "Restrictions": {"value": "personality"},
          "Artist": {"value": "A. Photographer"}, "Credit": {"value": "Own work"}, "ObjectName": {"value": "Tower"},
          "ImageDescription": {"value": "A tower"}, "Categories": {"value": "Towers"}}
    page = {"title": "File:Tower.jpg", "index": 1, "imageinfo": [{"url": "https://u/Tower.jpg", "thumburl": "https://u/3840px-Tower.jpg",
            "mime": "image/jpeg", "width": 5000, "height": 3000, "thumbwidth": 3840, "thumbheight": 2304,
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Tower.jpg", "extmetadata": em}]}
    monkeypatch.setattr(F, "_http_json", lambda params, timeout=30, api=None: {"query": {"pages": {"1": page}}})
    c = F.search("tower")[0]
    assert c["license_url"].endswith("/by-sa/4.0") and c["restrictions"] == "personality" and c["attribution_required"] == "true"


def test_a_nasa_item_credited_to_someone_else_is_not_cleared(monkeypatch):
    items = {"collection": {"items": [
        {"href": "h1", "links": [{"rel": "preview", "href": "https://p/1.jpg"}],
         "data": [{"title": "Exoplanet", "nasa_id": "a1", "description": "Artist concept. Image credit: ESO/M. Kornmesser"}]},
        {"href": "h2", "links": [{"rel": "preview", "href": "https://p/2.jpg"}],
         "data": [{"title": "Deep field", "nasa_id": "a2", "description": "Credit: NASA, ESA, CSA, STScI"}]}]}}
    monkeypatch.setattr(F, "_get", lambda url, timeout, what: json.dumps(items))
    a, b = F.search_nasa("planet")
    assert not F._license_ok(a["license"]) and "ESO" in a["license"]
    assert F._license_ok(b["license"]) and b["license"] == "Public domain (NASA)"


def test_commons_is_asked_for_its_largest_standard_width_by_default(monkeypatch):
    """At 1600 Commons rounded up to 1920: a 4861 px original arrived at the frame's own width, no room for a push.
    3840 is its largest standard width (a smaller original arrives whole, never enlarged)."""
    seen = {}
    def fake(params, timeout=30, api=None):
        seen.update(params)
        return {"query": {"pages": {}}}
    monkeypatch.setattr(F, "_http_json", fake)
    F.search("tower")
    assert seen["iiurlwidth"] == 3840 == F.DEFAULT_WIDTH
