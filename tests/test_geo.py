"""geo: real geography as GeoJSON with its credit (Natural Earth cut to a box, OpenStreetMap through Overpass with
servers tried in turn), and geo.js drawing it projected; nothing here reaches the network."""
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common  # noqa: E402
import geo  # noqa: E402

OSM = {"elements": [
    {"type": "way", "tags": {"natural": "coastline"}, "geometry": [{"lon": 114.0, "lat": 22.5}, {"lon": 114.1, "lat": 22.52}]},
    {"type": "way", "tags": {"natural": "water", "name": "Lake"},
     "geometry": [{"lon": 114.0, "lat": 22.6}, {"lon": 114.01, "lat": 22.6}, {"lon": 114.01, "lat": 22.61}, {"lon": 114.0, "lat": 22.6}]},
    {"type": "way", "tags": {"highway": "primary", "name": "Shennan Blvd"},
     "geometry": [{"lon": 113.9, "lat": 22.54}, {"lon": 114.1, "lat": 22.54}]},
    {"type": "relation", "tags": {"boundary": "administrative", "admin_level": "6", "name": "Futian"},
     "members": [{"role": "outer", "geometry": [{"lon": 114.0, "lat": 22.5}, {"lon": 114.1, "lat": 22.6}]}]},
]}


def test_overpass_ways_and_relations_become_lines_and_polygons():
    fc = geo.to_geojson(OSM)
    kinds = [(f["properties"].get("name"), f["geometry"]["type"]) for f in fc["features"]]
    assert kinds == [(None, "LineString"), ("Lake", "Polygon"), ("Shennan Blvd", "LineString"), ("Futian", "MultiLineString")]


def test_a_busy_server_is_passed_over_and_the_credit_is_recorded(tmp_path, monkeypatch):
    tried = []

    def get(url, data=None, timeout=60):
        tried.append(url)
        if "busy" in url:
            raise OSError("502 at capacity")
        return json.dumps(OSM).encode()
    monkeypatch.setattr(geo, "_get", get)
    out, n = geo.osm(str(tmp_path), "coast", "coast", (113.8, 22.4, 114.2, 22.7), servers=("https://busy/api", "https://ok/api"))
    assert n == 4 and tried == ["https://busy/api", "https://ok/api"]
    rec = json.loads(open(out + ".json").read())
    assert rec["licence"] == "ODbL 1.0" and rec["server"] == "https://ok/api"
    assert geo.credit_lines(str(tmp_path)) == ["Map data: © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)"]


def test_no_server_answering_is_said_not_taken_for_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(geo, "_get", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    monkeypatch.setattr(geo.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as e:
        geo.osm(str(tmp_path), "w", "water", (113.8, 22.4, 114.2, 22.7), servers=("https://a/api",), tries=2)
    assert "not 'nothing there'" in str(e.value)


def test_a_province_sized_box_is_refused_for_roads(tmp_path):
    with pytest.raises(SystemExit):
        geo.osm(str(tmp_path), "r", "roads", (112.0, 21.0, 116.0, 24.0))


def test_natural_earth_is_cut_to_the_box_and_credited(tmp_path, monkeypatch):
    monkeypatch.setattr(geo, "CACHE", str(tmp_path / "cache"))
    layer = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "Guangdong"}, "geometry": {"type": "Polygon", "coordinates": [[[113, 22], [115, 22], [115, 24], [113, 22]]]}},
        {"type": "Feature", "properties": {"name": "Far away"}, "geometry": {"type": "Polygon", "coordinates": [[[10, 50], [11, 50], [11, 51], [10, 50]]]}}]}
    monkeypatch.setattr(geo, "_get", lambda *a, **k: json.dumps(layer).encode())
    film = tmp_path / "film"
    film.mkdir()
    out, n = geo.ne(str(film), "admin_1_states_provinces", "10m", (112.5, 21.5, 115.5, 23.5))
    assert n == 1 and json.load(open(out))["features"][0]["properties"]["name"] == "Guangdong"
    assert "Natural Earth" in geo.credit_lines(str(film))[0]


def test_a_layer_named_like_its_kind_is_still_a_name(tmp_path, monkeypatch):
    # `osm <dir> coast --what coast`: the name equals the flag's value and must not be lost
    monkeypatch.setattr(geo, "osm", lambda d, name, what, bb: (os.path.join(d, "geo", name + ".geojson"), 1))
    assert geo.main(["osm", str(tmp_path), "coast", "--what", "coast", "--bbox", "113.8,22.4,114.2,22.7"]) == 0


@pytest.mark.skipif(not _common.find_chrome(), reason="Chrome not installed")
def test_geo_js_projects_a_box_onto_the_frame_and_draws_each_feature(tmp_path):
    import _filmpage as fp
    shutil.copy(os.path.join(ROOT, "assets", "html", "geo.js"), tmp_path)
    fc = geo.to_geojson(OSM)
    (tmp_path / "p.html").write_text("""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<script src="geo.js"></script><script>
window.filmReady = (async () => { const fc = %s; const P = Geo.fit([113.9, 22.5, 114.1, 22.61], 1920, 1080, {pad: 40});
  document.body.innerHTML = Geo.svg([{data: fc, cls: 'x'}], P);
  const [x0, y0] = P.xy([113.9, 22.5]), [x1, y1] = P.xy([114.1, 22.61]);
  window.__r = {n: document.querySelectorAll('path.x[pathLength="1"]').length, names: [...document.querySelectorAll('path')].map((p) => p.dataset.name),
    corners: [x0, y0, x1, y1].map(Math.round)}; return 'ok'; })();
window.seek = () => {};</script></body></html>""" % json.dumps(fc))
    port, srv = fp.serve(str(tmp_path))
    try:
        p = fp.FilmPage(port, "p.html")
        try:
            r = p.ev("window.__r")
        finally:
            p.close()
    finally:
        srv.shutdown()
    assert r["n"] == 4 and "Shennan Blvd" in r["names"], r
    x0, y0, x1, y1 = r["corners"]
    assert y0 > y1, "north is up"
    assert (x0 == 40 or y1 == 40) and abs((x0 + x1) / 2 - 960) <= 1 and abs((y0 + y1) / 2 - 540) <= 1, r
