import os, json, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import imagefetch as F


def test_license_ok_accepts_free_rejects_nonfree():
    for good in ("Public domain", "CC0", "CC BY 4.0", "CC BY-SA 3.0", "No restrictions", "PDM"):
        assert F._license_ok(good), good
    for bad in ("", "Non-free media", "Fair use", "All rights reserved", "Copyright, used with permission"):
        assert not F._license_ok(bad), bad

def test_license_rejects_nc_and_nd_variants():
    # NonCommercial / NoDerivatives CC licenses are NOT free for a duotone-treating video deck — reject
    # them even though the string also contains "cc by" (the _BAD check wins, evaluated first)
    for bad in ("CC BY-NC 4.0", "CC BY-NC-SA 3.0", "CC BY-ND 4.0", "CC BY-NC-ND 2.0",
                "Creative Commons Attribution-NonCommercial 4.0"):
        assert not F._license_ok(bad), bad
    # the free BY / BY-SA variants still pass (no -nc/-nd substring)
    for good in ("CC BY 4.0", "CC BY-SA 4.0", "CC BY 2.5"):
        assert F._license_ok(good), good


def test_strip_html():
    assert F._strip_html("<a href='x'>Ronny <b>Siegel</b></a>") == "Ronny Siegel"
    assert F._strip_html(None) == ""


def test_attribution_line_from_meta():
    meta = {"artist": "Ronny Siegel", "license": "CC BY 4.0", "source": "https://commons..."}
    line = F.attribution_line(meta)
    assert "Ronny Siegel" in line and "CC BY 4.0" in line and "Wikimedia Commons" in line


def test_attribution_line_falls_back_to_credit_then_generic():
    assert "Wikimedia Commons" in F.attribution_line({"license": "CC0"})   # no artist/credit


def test_hex_rgb():
    assert F._hex_rgb("#161412") == (22, 20, 18)
    assert F._hex_rgb("f5f2ea") == (245, 242, 234)


def test_duotone_maps_grayscale_to_ramp(tmp_path):
    from PIL import Image
    src = tmp_path / "src.png"
    # a black->white horizontal gradient
    img = Image.new("L", (256, 8))
    for x in range(256):
        for y in range(8):
            img.putpixel((x, y), x)
    img.convert("RGB").save(src)
    out = tmp_path / "duo.png"
    F.duotone(str(src), str(out), shadow=(20, 10, 0), highlight=(240, 230, 220))
    res = Image.open(out).convert("RGB")
    assert res.getpixel((0, 4))[0] < 40      # shadow end maps near the shadow colour
    assert res.getpixel((255, 4))[0] > 200   # highlight end maps near the highlight colour


def test_duotone_tritone_midpoint(tmp_path):
    from PIL import Image
    src = tmp_path / "g.png"
    img = Image.new("L", (256, 4))
    for x in range(256):
        for y in range(4):
            img.putpixel((x, y), x)
    img.convert("RGB").save(src)
    out = tmp_path / "tri.png"
    F.duotone(str(src), str(out), shadow=(0, 0, 0), mid=(150, 100, 50), highlight=(250, 250, 250))
    res = Image.open(out).convert("RGB")
    r, g, b = res.getpixel((128, 2))         # the middle input maps near the MID tone
    assert abs(r - 150) < 25 and abs(g - 100) < 25 and abs(b - 50) < 25


def test_search_parses_commons_response(monkeypatch):
    fake = {"query": {"pages": {"1": {"title": "File:Tokyo railway map en.svg", "imageinfo": [{
        "thumburl": "https://upload/x.png", "url": "https://upload/x.svg", "mime": "image/svg+xml",
        "thumbwidth": 1600, "thumbheight": 1000,
        "extmetadata": {"LicenseShortName": {"value": "CC0"}, "Artist": {"value": "<a>Naoki</a>"}},
    }]}}}}
    monkeypatch.setattr(F, "_http_json", lambda params, timeout=30: fake)
    got = F.search("Tokyo railway map")
    assert len(got) == 1
    assert got[0]["license"] == "CC0" and got[0]["artist"] == "Naoki" and got[0]["width"] == 1600


def test_fetch_filters_by_license_and_writes_sidecar(tmp_path, monkeypatch):
    cands = [
        {"title": "File:bad.jpg", "url": "u1", "mime": "image/jpeg", "license": "Non-free", "artist": "", "credit": "", "source": "s1", "width": 1600, "height": 1000},
        {"title": "File:good map.png", "url": "u2", "mime": "image/png", "license": "CC0", "artist": "N", "credit": "", "source": "s2", "width": 1600, "height": 1000},
    ]
    monkeypatch.setattr(F, "search", lambda q, limit=12, width=1600: cands)
    downloaded = {}
    monkeypatch.setattr(F, "_download", lambda url, out, timeout=60: downloaded.__setitem__("url", url) or open(out, "wb").write(b"x" * 2000))
    out = tmp_path / "img.png"
    meta = F.fetch("a map", str(out), prefer="map")
    assert meta and meta["license"] == "CC0"          # skipped the non-free candidate
    assert downloaded["url"] == "u2"
    side = json.load(open(str(out) + ".json"))
    assert side["title"] == "File:good map.png" and side["query"] == "a map"


def test_fetch_returns_none_when_nothing_license_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "search", lambda q, limit=12, width=1600: [
        {"title": "x", "url": "u", "mime": "image/jpeg", "license": "All rights reserved", "artist": "", "credit": "", "source": "", "width": 1600, "height": 1000}])
    assert F.fetch("q", str(tmp_path / "n.png")) is None


def test_the_depicts_filter_is_a_parameter_and_never_applied_on_its_own():
    """A caller may restrict a search to files that DECLARE they depict a QID. Nothing resolves a term to a
    QID automatically, because resolution was measured to be unreliable — the top entity for "trust" is a
    French rock band — and a confidently wrong photograph is worse than a vaguely right one."""
    import inspect
    src = inspect.getsource(F.fetch)
    assert "resolve_concept" not in src, (
        "fetch() resolves a concept automatically; the measured failure in resolve_concept's docstring says "
        "why that puts a wrong picture on a frame")
    assert "depicts" in inspect.signature(F.search).parameters


def test_search_builds_a_depicts_query_only_when_given_one(monkeypatch):
    seen = {}

    def fake(params, timeout=30, api=None):
        seen["q"] = params.get("gsrsearch")
        return {"query": {"pages": {}}}
    monkeypatch.setattr(F, "_http_json", fake)
    F.search("a cat")
    assert seen["q"] == "a cat"
    F.search("a cat", depicts="Q146")
    assert seen["q"].startswith("haswbstatement:P180=Q146 "), seen["q"]
