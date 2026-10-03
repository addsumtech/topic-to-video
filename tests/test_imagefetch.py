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


# ── a failed request is not an empty result ─────────────────────────────────────────────────────────────
# Commons answers a burst of searches with HTTP 429. fetch() used to swallow it and return None, which reads
# as "no license-clean image exists" and degrades a documentary beat on a busy network. These drive the real
# request path through a mocked urlopen, so they exercise the retry and the failure message end to end.

import email.message
import io
import urllib.error

_SEARCH_ANSWER = {"query": {"pages": {"1": {"title": "File:River and city.jpg", "imageinfo": [{
    "thumburl": "https://upload.example/river.jpg", "url": "https://upload.example/river-full.jpg",
    "mime": "image/jpeg", "thumbwidth": 1600, "thumbheight": 1100,
    "descriptionurl": "https://commons.example/File:River_and_city.jpg",
    "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 3.0"}, "Artist": {"value": "A Photographer"}},
}]}}}}
_IMAGE_BYTES = b"\xff\xd8" + b"jpeg" * 600


def _http_error(url, code, retry_after=None):
    headers = email.message.Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError(url, code, "Too Many Requests" if code == 429 else "Error", headers, None)


def _fake_commons(failures):
    """A urlopen stand-in: each URL kind ('api' or 'file') first raises the queued errors, then answers."""
    calls = []

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        kind = "api" if "api.php" in url else "file"
        calls.append(kind)
        queue = failures.get(kind) or []
        if queue:
            raise queue.pop(0)(url)
        body = json.dumps(_SEARCH_ANSWER).encode() if kind == "api" else _IMAGE_BYTES
        return io.BytesIO(body)
    return urlopen, calls


def test_a_rate_limited_search_is_retried_and_the_image_still_arrives(tmp_path, monkeypatch):
    urlopen, calls = _fake_commons({"api": [lambda u: _http_error(u, 429, retry_after=2)]})
    monkeypatch.setattr(F.urllib.request, "urlopen", urlopen)
    waits = []
    monkeypatch.setattr(F, "_sleep", waits.append, raising=False)
    out = tmp_path / "river.jpg"
    meta = F.fetch("Shenzhen River", str(out))
    assert meta is not None, "one 429 from Commons made fetch() report that no image exists"
    assert out.read_bytes() == _IMAGE_BYTES
    assert meta["artist"] == "A Photographer" and json.load(open(str(out) + ".json"))["license"] == "CC BY-SA 3.0"
    assert calls == ["api", "api", "file"], calls          # the search was asked again, once
    assert waits == [2.0], "the server's Retry-After (2 s) was not the wait used: %r" % waits


def test_a_persistent_rate_limit_fails_loud_and_never_reads_as_nothing_found(tmp_path, monkeypatch):
    error = getattr(F, "FetchError", None)
    assert error is not None, "imagefetch has no distinct failure for a request Commons did not answer"
    urlopen, calls = _fake_commons({"api": [lambda u: _http_error(u, 429)] * 50})
    monkeypatch.setattr(F.urllib.request, "urlopen", urlopen)
    waits = []
    monkeypatch.setattr(F, "_sleep", waits.append, raising=False)
    with pytest.raises(error) as got:
        F.fetch("Shenzhen River", str(tmp_path / "river.jpg"))
    msg = str(got.value)
    assert got.value.kind == "rate-limit" and "429" in msg and "rate-limiting" in msg, msg
    assert "NOT a finding" in msg and "no license-clean image found" not in msg, msg
    assert len(calls) == F._RETRIES + 1, "the retries are not bounded: %d requests" % len(calls)
    assert waits == [F._BACKOFF_S * 2 ** i for i in range(F._RETRIES)], waits   # backoff with no Retry-After
    assert not (tmp_path / "river.jpg").exists()


def test_the_cli_reports_a_rate_limit_as_a_failure_not_as_an_empty_search(tmp_path, monkeypatch, capsys):
    urlopen, _calls = _fake_commons({"api": [lambda u: _http_error(u, 429)] * 50})
    monkeypatch.setattr(F.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(F, "_sleep", lambda s: None, raising=False)
    monkeypatch.setattr(sys, "argv", ["imagefetch.py", "Shenzhen River", str(tmp_path / "river.jpg")])
    with pytest.raises(SystemExit) as code:
        F.main()
    out = capsys.readouterr()
    assert code.value.code == 2, "exit %r — the same code as an empty search" % code.value.code
    assert "no license-clean image found" not in out.out + out.err
    assert "rate-limit" in out.err and "429" in out.err, out.err


def test_a_missing_file_is_skipped_for_the_next_candidate_without_waiting(tmp_path, monkeypatch):
    two = {"query": {"pages": {
        "1": {"title": "File:gone.jpg", "imageinfo": [dict(_SEARCH_ANSWER["query"]["pages"]["1"]["imageinfo"][0],
                                                             thumburl="https://upload.example/gone.jpg")]},
        "2": {"title": "File:here.jpg", "imageinfo": [dict(_SEARCH_ANSWER["query"]["pages"]["1"]["imageinfo"][0],
                                                             thumburl="https://upload.example/here.jpg")]}}}}
    seen = []

    def urlopen(req, timeout=None):
        url = req.full_url
        seen.append(url)
        if "api.php" in url:
            return io.BytesIO(json.dumps(two).encode())
        if url.endswith("gone.jpg"):
            raise _http_error(url, 404)
        return io.BytesIO(_IMAGE_BYTES)
    monkeypatch.setattr(F.urllib.request, "urlopen", urlopen)
    waits = []
    monkeypatch.setattr(F, "_sleep", waits.append, raising=False)
    meta = F.fetch("a river", str(tmp_path / "r.jpg"))
    assert meta and meta["title"] == "File:here.jpg"
    assert waits == [] and seen.count("https://upload.example/gone.jpg") == 1   # a 404 is not retried
