"""The data-flow and geography runtime: projection accuracy, the antimeridian, conservation, labels that never collide.

Pure functions only, run in node against the REAL runtime modules (tests/_tsprobe.py) — nothing here renders a frame.

WHAT IS HELD, AND THE MUTATION EACH ONE CATCHES (engineering-case-law E7):
  * runtime/geo.ts `viewVec`/`orthoXY` — the closed-form orthographic the flight arcs are lifted with — lands every
    known city within 2 px of d3-geo's own projection at several views and sizes. A sign slip in the latitude term
    (the mutation) moves cities by hundreds of px.
  * A route across the antimeridian (Tokyo to San Francisco) is ONE line: on a flat map recentred on the places'
    circular-mean meridian the path has exactly one subpath; the CONTROL is the same route on an un-recentred map,
    where d3 cuts it in two — so the test can tell the difference it claims to.
  * runtime/sankey.ts refuses a node whose inflow and outflow differ, and when it accepts, every node's ribbons stack
    to exactly its height (the width IS the quantity).
  * runtime/labelPlace.ts never returns two overlapping labels, and throws rather than overlap.
"""
import json

import pytest

import _tsprobe as tp

pytestmark = pytest.mark.skipif(not tp.available(), reason="needs node + npx + remotion/node_modules")

GEO = "import {orthoXY, orthoProjection, findRegion, regionFrame, meanLon, flatProjection, geoPath, greatCircle, " \
      "pointsFrame, wrapDelta, lonLatOf} from %s;" % tp.mod("geo.ts")

# (name, lon, lat) — well-known city-centre coordinates; the test is about the projection agreeing with itself
CITIES = [("Tokyo", 139.6917, 35.6895), ("London", -0.1276, 51.5072), ("Sydney", 151.2093, -33.8688),
          ("Sao Paulo", -46.6333, -23.5505), ("Reykjavik", -21.94, 64.15), ("Honolulu", -157.8583, 21.3069),
          ("Cape Town", 18.4241, -33.9249), ("Anchorage", -149.9003, 61.2181), ("Suva", 178.4419, -18.1416)]


def test_known_cities_project_within_two_px_of_d3():
    out = tp.run_ts(GEO, """
const cities = %s;
const views = [{lon0:0,lat0:0,R:400,cx:960,cy:540},{lon0:140,lat0:30,R:900,cx:960,cy:600},
  {lon0:-170,lat0:-20,R:3000,cx:540,cy:960},{lon0:-30,lat0:60,R:250,cx:500,cy:500},{lon0:179,lat0:-15,R:5000,cx:960,cy:540}];
out.max = 0; out.n = 0;
for (const v of views) { const p = orthoProjection(v, 1920, 1920);
  for (const [n, lo, la] of cities) { const a = orthoXY(lo, la, v); if (a.z <= 0.02) continue;
    const b = p([lo, la]); out.n++; out.max = Math.max(out.max, Math.hypot(a.x - b[0], a.y - b[1])); } }
""" % json.dumps(CITIES))
    assert out["n"] >= 15, "too few visible city/view pairs were compared: %r" % out
    assert out["max"] < 2.0, "closed-form orthographic disagrees with d3-geo by %.3f px" % out["max"]


def test_a_route_across_the_antimeridian_is_one_line():
    out = tp.run_ts(GEO, """
const tyo: [number, number] = [139.6917, 35.6895], sfo: [number, number] = [-122.4194, 37.7749];
const gc = greatCircle(tyo, sfo);
const line = {type: 'LineString', coordinates: Array.from({length: 65}, (_, k) => gc(k / 64))};
const count = (proj: any) => { const d = geoPath(proj)(line as any) || ''; return (d.match(/M/g) || []).length; };
out.recentred = count(flatProjection(meanLon([tyo[0], sfo[0]])).scale(300).translate([960, 540]));
out.control = count(flatProjection(0).scale(300).translate([960, 540]));
// on the globe centred on the two places, consecutive samples never jump: the arc is continuous
const pf = pointsFrame([tyo, sfo, gc(0.5) as [number, number]]);
const v = {lon0: pf.center[0], lat0: pf.center[1], R: 400, cx: 960, cy: 540};
let jump = 0, hidden = 0, prev: any = null;
for (let k = 0; k <= 200; k++) { const ll = gc(k / 200); const p = orthoXY(ll[0], ll[1], v); if (p.z < 0) hidden++;
  if (prev) jump = Math.max(jump, Math.hypot(p.x - prev.x, p.y - prev.y)); prev = p; }
out.jump = jump; out.hidden = hidden;
out.wrap = [wrapDelta(170, -170), wrapDelta(-170, 170), wrapDelta(10, 350)];
""")
    assert out["recentred"] == 1, "the recentred flat map cut the trans-Pacific route into %d pieces" % out["recentred"]
    assert out["control"] == 2, "control failed: an un-recentred map should cut the route at 180°, got %r" % out
    assert out["hidden"] == 0 and out["jump"] < 12, out
    assert out["wrap"] == [20, -20, -20], out["wrap"]


def test_regions_are_found_by_name_or_code_and_unknown_names_throw_with_suggestions():
    out = tp.run_ts(GEO, """
out.br = findRegion('Brazil', 't').id; out.code = findRegion('76', 't').name;
try { findRegion('Brasil', 't'); out.err = ''; } catch (e) { out.err = String((e as Error).message); }
// a far territory is lit but not framed: France frames on its mainland, not on French Guiana
out.fr = regionFrame([findRegion('France', 't').f50]).reach;
try { lonLatOf({lon: 10}, 'mark 1', 't'); out.ll = ''; } catch (e) { out.ll = String((e as Error).message); }
""")
    assert out["br"] == "076" and out["code"] == "Brazil"
    assert "Brazil" in out["err"], out["err"]
    assert out["fr"] < 12, "France's framing reach %.1f° — the overseas departments are being chased" % out["fr"]
    assert "lat" in out["ll"]


SANKEY = "import {layoutSankey, validateSankey, stackLabels} from %s;" % tp.mod("sankey.ts")


def test_sankey_refuses_a_node_that_does_not_conserve():
    out = tp.run_ts(SANKEY, """
const nodes = [{id:'a',label:'A'},{id:'b',label:'B'},{id:'m',label:'M'},{id:'x',label:'X'}];
try { validateSankey(nodes, [{from:'a',to:'m',value:60},{from:'b',to:'m',value:40},{from:'m',to:'x',value:90}], 't'); out.unbal = ''; }
catch (e) { out.unbal = String((e as Error).message); }
// float noise is not a violation: 0.1 + 0.2 in, 0.3 out
try { validateSankey(nodes, [{from:'a',to:'m',value:0.1},{from:'b',to:'m',value:0.2},{from:'m',to:'x',value:0.3}], 't'); out.fl = 'ok'; }
catch (e) { out.fl = String((e as Error).message); }
try { validateSankey(nodes, [{from:'a',to:'m',value:1},{from:'m',to:'a',value:1},{from:'b',to:'x',value:1}], 't'); out.loop = ''; }
catch (e) { out.loop = String((e as Error).message); }
""")
    assert "receives 100 and sends on 90" in out["unbal"], out["unbal"]
    assert out["fl"] == "ok", out["fl"]
    assert "loop" in out["loop"], out["loop"]


def test_sankey_ribbons_stack_to_their_node_and_widths_share_one_scale():
    out = tp.run_ts(SANKEY, """
const nodes = [{id:'a',label:'A'},{id:'b',label:'B'},{id:'c',label:'C'},{id:'n',label:'N'},{id:'h',label:'H'},{id:'i',label:'I'},{id:'l',label:'L'}];
const links = [{from:'a',to:'n',value:30},{from:'b',to:'n',value:20},{from:'c',to:'n',value:50},{from:'n',to:'h',value:45},
  {from:'n',to:'i',value:35},{from:'n',to:'l',value:20},{from:'a',to:'h',value:5}];
// a's 5 straight to h makes a's outflow 35 and h's inflow 50: still conserved at every interior node
const L = layoutSankey(nodes, links, {x0: 100, x1: 1800, y0: 200, y1: 900}, 20, 16, 't');
out.err = 0; out.scale = 0; out.overlap = 0; out.inside = true;
for (const n of L.nodes) {
  const outs = L.links.filter(l => l.source === n), ins = L.links.filter(l => l.target === n);
  const h = n.y1 - n.y0;
  if (outs.length) out.err = Math.max(out.err, Math.abs(outs.reduce((a, l) => a + l.width, 0) - h * (n.outV / n.value)));
  if (ins.length) out.err = Math.max(out.err, Math.abs(ins.reduce((a, l) => a + l.width, 0) - h * (n.inV / n.value)));
  if (n.y0 < 200 - 1e-6 || n.y1 > 900 + 1e-6) out.inside = false;
}
for (const l of L.links) out.scale = Math.max(out.scale, Math.abs(l.width / l.value - L.k));
for (let c = 0; c < L.cols; c++) { const ns = L.nodes.filter(n => n.col === c).sort((a, b) => a.y0 - b.y0);
  for (let j = 1; j < ns.length; j++) out.overlap = Math.max(out.overlap, ns[j - 1].y1 + 16 - ns[j].y0); }
out.cols = L.cols;
const tops = stackLabels([{cy: 300, h: 60}, {cy: 310, h: 60}, {cy: 320, h: 60}], 200, 900, 8)!;
const s = [...tops].sort((a, b) => a - b); out.lgap = Math.min(s[1] - s[0], s[2] - s[1]);
out.full = stackLabels([{cy: 300, h: 300}, {cy: 310, h: 300}, {cy: 320, h: 300}], 200, 900, 8);
""")
    assert out["err"] < 1e-6, "ribbons do not stack to their node's height: %r" % out
    assert out["scale"] < 1e-9, "one link is drawn at a different scale: %r" % out
    assert out["overlap"] < 1e-6 and out["inside"], out
    assert out["cols"] == 3
    assert out["lgap"] >= 68 - 1e-6, "stacked labels overlap: %r" % out
    assert out["full"] is None, "labels that cannot fit must be refused, not overlapped"


def test_label_placement_never_overlaps_and_refuses_when_it_must():
    out = tp.run_ts("import {placeLabels, overlaps} from %s;" % tp.mod("labelPlace.ts"), """
// eight points crowded round one spot: every label must find its own clear place
const reqs = Array.from({length: 8}, (_, i) => ({x: 900 + 30 * Math.cos(i), y: 500 + 30 * Math.sin(i), w: 140, h: 40, text: 'P' + i, r: 6}));
const P = placeLabels(reqs, {x0: 0, y0: 0, x1: 1920, y1: 1080}, 14);
out.pairs = 0; out.hit = 0;
for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) { out.pairs++; if (overlaps(P[i], P[j])) out.hit++; }
try { placeLabels(reqs, {x0: 850, y0: 450, x1: 1000, y1: 560}, 14); out.err = ''; } catch (e) { out.err = String((e as Error).message); }
""")
    assert out["pairs"] == 28 and out["hit"] == 0, out
    assert "no room to label" in out["err"], out["err"]


def test_relational_fixtures_keep_the_structure_and_change_only_the_copy():
    """scripts/cjk_type_qa.relational_props: the sidecar's ids, references, numbers, coordinates and atlas names reach
    the register untouched (each register refuses a broken relation, so a fixture that rewrote one would measure a
    refusal), and only the named copy paths carry the fixture's Chinese — different words at a different offset."""
    import glob
    import os
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "scripts"))
    import cjk_type_qa as c
    side = sorted(glob.glob(os.path.join(root, "remotion", "fixtures", "relational", "*.json")))
    assert {os.path.basename(p)[:-5] for p in side} >= {"FlowSankey", "GlobeFocus", "FlightArcs", "RankRace"}

    def leaves(v, path=""):
        if isinstance(v, dict):
            for k, x in v.items():
                yield from leaves(x, path + "." + k)
        elif isinstance(v, list):
            for x in v:
                yield from leaves(x, path + "[]")
        else:
            yield path, v

    for p in side:
        name = os.path.basename(p)[:-5]
        assert os.path.exists(os.path.join(root, "remotion", "src", "shots", name + ".tsx")), name
        spec = json.load(open(p, encoding="utf-8"))
        copy_paths = {"." + q for q in spec["copy"]}   # the same spelling leaves() produces: .nodes[].label, .periods[]
        a, _ = c.cjk_props(name, 0)
        b, _ = c.cjk_props(name, 2)
        orig = list(leaves(spec["props"]))
        got_a, got_b = list(leaves(a)), list(leaves(b))
        assert [k for k, _ in orig] == [k for k, _ in got_a], name
        for (k, v0), (_, va), (_, vb) in zip(orig, got_a, got_b):
            if k in copy_paths:
                assert va != v0 and isinstance(va, str), (name, k)
            else:
                assert va == v0 == vb, "%s: %s is structure and was changed (%r -> %r)" % (name, k, v0, va)
        assert a != b, "%s: two offsets gave the same words" % name
