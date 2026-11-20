#!/usr/bin/env python3
"""geo — real geography for a film: places, borders, coasts, rivers and city streets as GeoJSON, with their credit.

    python3 scripts/geo.py place "Shenzhen"                                   # where it is: lat, lon, bounding box
    python3 scripts/geo.py ne <film_dir> <layer> [--scale 10m|50m|110m] [--bbox W,S,E,N]
    python3 scripts/geo.py osm <film_dir> <name> --what coast|roads|water|rail|admin|parks --bbox W,S,E,N
    python3 scripts/geo.py credits <film_dir>

place    Nominatim (OpenStreetMap's geocoder; at most one request a second, as its policy asks).
ne       a Natural Earth layer (public domain), e.g. admin_0_countries, admin_1_states_provinces, coastline, rivers_lake_centerlines,
         populated_places, land, ocean; downloaded once per machine (a 10m layer can be tens of MB, minutes) and cached
         under ~/.cache/topic-to-video/natural-earth, cut to --bbox, written
         to <film_dir>/geo/<layer>.geojson. Country and province level; for streets use osm.
osm      OpenStreetMap features inside --bbox through the Overpass API (tried on several public servers with backoff:
         the main one turns queries away when it is busy), as LineStrings and Polygons in <film_dir>/geo/<name>.geojson.
         A box over 0.6 degrees on a side is refused for roads (a city's streets, not a province's).
credits  the lines the film's map data is owed: "© OpenStreetMap contributors (ODbL)" and Natural Earth (public domain,
         credit appreciated); film_deliver adds them to <stem>.credits.txt.
Every file written gets a record beside it (<file>.json: source, licence, credit, query), as imagefetch does for
pictures. Draw it with assets/html/geo.js (Geo.fit / Geo.svg: projected SVG paths, sharp at any zoom).

WHY. Geography is content for a large class of films (a city growing, a route, a migration, a river's delta, a
war's front) and the director path had nothing for it: a map was drawn by hand, from memory, with no data and no
credit. Real borders and coastlines come from public data, and its licence travels with the film.
Exit 0 done, 1 nothing found or a check failed, 2 usage error or no server answered.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

UA = "topic-to-video/3.0 (https://github.com/addsumtech/topic-to-video)"   # never the person running it
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_%s_%s.geojson"
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "topic-to-video", "natural-earth")
OSM_CREDIT = {"source": "OpenStreetMap", "licence": "ODbL 1.0", "licence_url": "https://www.openstreetmap.org/copyright",
              "credit": "© OpenStreetMap contributors"}
NE_CREDIT = {"source": "Natural Earth", "licence": "Public domain", "licence_url": "https://www.naturalearthdata.com/about/terms-of-use/",
             "credit": "Made with Natural Earth"}
WHAT = {   # Overpass filters: what a film asks for by name
    "coast": ['way["natural"="coastline"]'],
    "roads": ['way["highway"~"^(motorway|trunk|primary|secondary)$"]'],
    "water": ['way["natural"="water"]', 'way["waterway"~"^(river|canal)$"]', 'relation["natural"="water"]'],
    "rail": ['way["railway"~"^(rail|subway|light_rail)$"]'],
    "admin": ['relation["boundary"="administrative"]["admin_level"~"^(4|5|6)$"]'],
    "parks": ['way["leisure"="park"]', 'way["landuse"="forest"]'],
}
_USAGE = "\n".join(l.strip() for l in __doc__.strip().splitlines()[2:6])


def _get(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _bbox(s):
    try:
        w, so, e, n = (float(x) for x in s.split(","))
    except (AttributeError, ValueError):
        raise SystemExit("geo: --bbox takes W,S,E,N in degrees (e.g. 113.75,22.40,114.65,22.87)")
    if not (-180 <= w < e <= 180 and -90 <= so < n <= 90):
        raise SystemExit("geo: --bbox %s is not west<east, south<north" % s)
    return w, so, e, n


def _record(path, meta):
    with open(path + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


def place(name):
    """{name, lat, lon, bbox: [W,S,E,N]} from Nominatim, or None."""
    time.sleep(1.0)                                  # Nominatim's usage policy: one request a second at most
    r = json.loads(_get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": name, "format": "json", "limit": 1}), timeout=30))
    if not r:
        return None
    b = [float(x) for x in r[0]["boundingbox"]]       # S, N, W, E
    return {"name": r[0].get("display_name", name), "lat": float(r[0]["lat"]), "lon": float(r[0]["lon"]),
            "bbox": [b[2], b[0], b[3], b[1]]}


def _coords(g):
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point":
        yield c
    elif t in ("LineString", "MultiPoint"):
        yield from c
    elif t in ("Polygon", "MultiLineString"):
        for ring in c:
            yield from ring
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                yield from ring


def _touches(g, bb):
    w, s, e, n = bb
    return any(w <= x <= e and s <= y <= n for x, y, *_ in _coords(g or {}))


def ne(film_dir, layer, scale="50m", bbox=None):
    os.makedirs(CACHE, exist_ok=True)
    cached = os.path.join(CACHE, "ne_%s_%s.geojson" % (scale, layer))
    url = NE_BASE % (scale, layer)
    if not os.path.isfile(cached):
        # once per machine: the 10m layers are tens of MB (admin_1 at 10m took ~7 min from GitHub, 2026-11-20)
        print("[geo] downloading Natural Earth %s %s once (cached in %s)…" % (scale, layer, CACHE), flush=True)
        data = _get(url, timeout=900)
        with open(cached + ".tmp", "wb") as f:
            f.write(data)
        os.replace(cached + ".tmp", cached)
    gj = json.load(open(cached, encoding="utf-8"))
    feats = gj.get("features") or []
    if bbox:
        feats = [f for f in feats if _touches(f.get("geometry"), bbox)]
    out_dir = os.path.join(film_dir, "geo")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, layer + ".geojson")
    json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    _record(out, dict(NE_CREDIT, url=url, layer=layer, scale=scale, bbox=list(bbox) if bbox else None, features=len(feats)))
    return out, len(feats)


def overpass_query(what, bbox):
    w, s, e, n = bbox
    box = "(%f,%f,%f,%f)" % (s, w, n, e)
    return "[out:json][timeout:60];(" + "".join(f + box + ";" for f in WHAT[what]) + ");out geom;"


def to_geojson(osm):
    """Overpass `out geom` -> GeoJSON features: a closed way is a Polygon, an open one a LineString; a relation's
    outer members become one MultiLineString (its rings drawn as lines: enough for a boundary or a lake's shore)."""
    feats = []
    for el in osm.get("elements") or []:
        tags = el.get("tags") or {}
        props = {k: tags[k] for k in ("name", "name:en", "name:zh", "highway", "railway", "waterway", "natural",
                                      "admin_level", "leisure", "landuse") if k in tags}
        if el.get("type") == "way" and el.get("geometry"):
            pts = [[round(p["lon"], 5), round(p["lat"], 5)] for p in el["geometry"]]
            closed = len(pts) > 3 and pts[0] == pts[-1] and "highway" not in tags and "railway" not in tags \
                and tags.get("natural") != "coastline"
            feats.append({"type": "Feature", "properties": props,
                          "geometry": {"type": "Polygon", "coordinates": [pts]} if closed else {"type": "LineString", "coordinates": pts}})
        elif el.get("type") == "relation":
            lines = [[[round(p["lon"], 5), round(p["lat"], 5)] for p in m["geometry"]]
                     for m in el.get("members") or [] if m.get("geometry") and m.get("role") in ("outer", "")]
            if lines:
                feats.append({"type": "Feature", "properties": props, "geometry": {"type": "MultiLineString", "coordinates": lines}})
    return {"type": "FeatureCollection", "features": feats}


def osm(film_dir, name, what, bbox, servers=OVERPASS, tries=3):
    if what not in WHAT:
        raise SystemExit("geo: --what takes %s" % "|".join(WHAT))
    w, s, e, n = bbox
    if what == "roads" and (e - w > 0.6 or n - s > 0.6):
        raise SystemExit("geo: a %.2f x %.2f degree box is too big for roads (a city's streets: 0.6 degrees a side at most)" % (e - w, n - s))
    q = overpass_query(what, bbox).encode()
    last, wait = None, 2.0
    for k in range(tries):
        for srv in servers:
            try:
                data = json.loads(_get(srv, data=urllib.parse.urlencode({"data": q}).encode(), timeout=90))
                gj = to_geojson(data)
                out_dir = os.path.join(film_dir, "geo")
                os.makedirs(out_dir, exist_ok=True)
                out = os.path.join(out_dir, name + ".geojson")
                json.dump(gj, open(out, "w", encoding="utf-8"), ensure_ascii=False)
                _record(out, dict(OSM_CREDIT, what=what, bbox=list(bbox), server=srv, features=len(gj["features"]),
                                  retrieved=time.strftime("%Y-%m-%d")))
                return out, len(gj["features"])
            except Exception as e:            # a busy or unreachable server: the next one, then all again after a wait
                last = "%s: %s" % (srv, e)
        time.sleep(wait)
        wait *= 2
    raise SystemExit("geo: no Overpass server answered (%s); this is not 'nothing there' — try again later" % last)


def credit_lines(film_dir):
    """The credits a film's map data is owed, each source once."""
    out, seen = [], set()
    folder = os.path.join(film_dir, "geo")
    for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not f.endswith(".geojson.json"):
            continue
        r = json.load(open(os.path.join(folder, f), encoding="utf-8"))
        if r.get("source") in seen:
            continue
        seen.add(r.get("source"))
        out.append("Map data: %s, %s (%s)" % (r.get("credit"), r.get("licence"), r.get("licence_url")))
    return out


def main(argv):
    if not argv or argv[0] not in ("place", "ne", "osm", "credits"):
        print(_USAGE, file=sys.stderr)
        return 2
    sub, rest = argv[0], argv[1:]
    _c.refuse_unknown(rest, valued=("scale", "bbox", "what"), usage=_USAGE)
    vals = {k: _c.argflag(rest, k, None) for k in ("scale", "bbox", "what")}
    args, skip = [], False                      # positionals by place: a name may equal a flag's value ("coast")
    for a in rest:
        if skip:
            skip = False
        elif a.startswith("--"):
            skip = "=" not in a
        else:
            args.append(a)
    if sub == "place":
        if len(args) != 1:
            print(_USAGE, file=sys.stderr)
            return 2
        p = place(args[0])
        if not p:
            print("geo: no place found for %r" % args[0])
            return 1
        print("%s\n  lat %.5f lon %.5f  bbox %s" % (p["name"], p["lat"], p["lon"], ",".join("%.4f" % x for x in p["bbox"])))
        return 0
    if not args or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    if sub == "credits":
        print("\n".join(credit_lines(d)))
        return 0
    if len(args) != 2:
        print(_USAGE, file=sys.stderr)
        return 2
    if sub == "ne":
        out, k = ne(d, args[1], vals["scale"] or "50m", _bbox(vals["bbox"]) if vals["bbox"] else None)
    else:
        if not (vals["what"] and vals["bbox"]):
            print("geo: osm needs --what and --bbox", file=sys.stderr)
            return 2
        out, k = osm(d, args[1], vals["what"], _bbox(vals["bbox"]))
    print("[geo] %s  %d feature(s), credit on record (%s.json)" % (os.path.relpath(out, d), k, os.path.relpath(out, d)))
    return 0 if k else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
