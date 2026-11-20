// geo.js — real geography on a film page: GeoJSON (scripts/geo.py) projected and drawn as SVG paths, sharp at any zoom.
//
//   const P = Geo.fit([113.75, 22.40, 114.65, 22.87], 1920, 1080, {pad: 80});   // a box [W,S,E,N] filling the frame
//   el.innerHTML = Geo.svg([{data: coast, cls: 'coast'}, {data: roads, cls: 'road'}], P, {w: 1920, h: 1080});
//   const [x, y] = P.xy([114.0545, 22.5446]);                                   // a place on the page
//
// Web Mercator (what every street map uses), fitted to a box with its aspect kept. Geo.svg writes one <path> per
// feature with class, data-name (its name, name:en or name:zh) and pathLength="1", so a line draws on with
// stroke-dasharray: 1; stroke-dashoffset: 1 -> 0. Style it in CSS (a coast, a road, a border are a film's own look).
// Each feature's own name stays in its properties: label what the voice names, at a readable size.
// Geo.inside([lon, lat], landOrDistricts) says which polygon a place is in (null: water, or outside the layer): test
// every place before an object stands on it.
// Credit: the data's record (geo/<file>.geojson.json) goes into the film's credits through scripts/geo.py credits.
window.Geo = (() => {
  const R = Math.PI / 180;
  const merc = ([lon, lat]) => [lon * R, Math.log(Math.tan(Math.PI / 4 + Math.max(-85, Math.min(85, lat)) * R / 2))];

  // a projection that puts the box [W,S,E,N] inside w x h less `pad`, centred, its aspect kept
  function fit(bbox, w, h, o) {
    o = o || {}; const pad = o.pad == null ? 40 : o.pad;
    const [x0, y0] = merc([bbox[0], bbox[1]]), [x1, y1] = merc([bbox[2], bbox[3]]);
    const k = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
    const ox = (w - k * (x1 - x0)) / 2, oy = (h - k * (y1 - y0)) / 2;
    const xy = (p) => { const [x, y] = merc(p); return [ox + (x - x0) * k, h - oy - (y - y0) * k]; };
    return {xy, k, bbox, w, h};
  }

  const ring = (pts, P, close) => pts.map((p, i) => { const [x, y] = P.xy(p); return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1); }).join('') + (close ? 'Z' : '');
  // the SVG path data of a GeoJSON geometry (points are left to markers: Geo.svg skips them)
  function d(g, P) {
    if (!g) return '';
    switch (g.type) {
      case 'LineString': return ring(g.coordinates, P, false);
      case 'MultiLineString': return g.coordinates.map((c) => ring(c, P, false)).join('');
      case 'Polygon': return g.coordinates.map((c) => ring(c, P, true)).join('');
      case 'MultiPolygon': return g.coordinates.map((poly) => poly.map((c) => ring(c, P, true)).join('')).join('');
      default: return '';
    }
  }
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const nameOf = (f) => { const p = f.properties || {}; return p.name || p['name:en'] || p.NAME || p.name_en || p['name:zh'] || ''; };

  // layers: [{data: FeatureCollection, cls, filter?: (feature) => bool}] drawn in order; o.w / o.h the viewBox
  function svg(layers, P, o) {
    o = o || {}; const w = o.w || P.w, h = o.h || P.h;
    let body = '';
    for (const L of layers) {
      for (const f of (L.data && L.data.features) || []) {
        if (L.filter && !L.filter(f)) continue;
        const pd = d(f.geometry, P); if (!pd) continue;
        body += '<path class="' + esc(L.cls || '') + '" data-name="' + esc(nameOf(f)) + '" pathLength="1" d="' + pd + '"/>';
      }
    }
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '">' + body + '</svg>';
  }

  // the polygon feature of `fc` that contains the point [lon, lat], or null: test a place before putting anything on
  // it (a land or district layer: a house on land, never over the river; the Shenzhen film floated a factory on it)
  function inPoly(pt, rings) {
    let inside = false;
    for (const ring of rings) {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) inside = !inside;
      }
    }
    return inside;
  }
  function inside(pt, fc) {
    for (const f of (fc && fc.features) || []) {
      const g = f.geometry || {};
      if (g.type === 'Polygon' && inPoly(pt, g.coordinates)) return f;
      if (g.type === 'MultiPolygon' && g.coordinates.some((poly) => inPoly(pt, poly))) return f;
    }
    return null;
  }

  async function load(url) { const r = await fetch(url); if (!r.ok) throw new Error('Geo.load: ' + url + ' ' + r.status); return r.json(); }
  return {fit, d, svg, load, merc, nameOf, inside};
})();
