// GEO — offline vector geography for the map registers (GlobeFocus, FlightArcs), projected in code.
//
// THE DATA. Natural Earth 4.1.0 (public domain) as TopoJSON from `world-atlas` 2.0.2 (ISC), at 1:110m and 1:50m,
// decoded with `topojson-client` 3.1.0 (ISC) and projected with `d3-geo` 3.1.1 (ISC). Nothing is fetched at render
// time: the atlas is bundled, so a still renders the same coastline on any machine with no network. Licences and
// versions are recorded in `remotion/THIRD_PARTY.json`.
//
// WHAT A FILM MUST SUPPLY, AND WHAT THE ATLAS MAY. The atlas supplies SHAPES — coastlines and country outlines — and
// nothing else. A coordinate the register draws a mark at is the FILM's (a sourced lon/lat), never a lookup this
// module performs from a name: a gazetteer typed in here would be a table of facts nobody sourced. A region is named
// by the film as Natural Earth names it (`Brazil`, `United States of America`) or by its ISO 3166-1 numeric code; a
// name the atlas does not carry THROWS with the nearest names it does, rather than highlighting nothing.
//
// THE PROJECTION CONVENTION. Centring a view on (lon0, lat0) is d3's `rotate([-lon0, -lat0])`. `viewVec` is the same
// rotation written out in closed form (Snyder's orthographic), so a register can lift a point OFF the surface (a
// flight arc) and still land exactly where d3 puts the surface under it — tests/test_geo.py holds the two to within
// 2 px for known cities at several views and sizes.
import {geoOrthographic, geoEqualEarth, geoPath, geoGraticule10, geoInterpolate, geoDistance, geoCentroid, geoArea,
  geoContains, GeoProjection} from 'd3-geo';
import {feature, mesh} from 'topojson-client';
import C110 from 'world-atlas/countries-110m.json';
import C50 from 'world-atlas/countries-50m.json';
import L110 from 'world-atlas/land-110m.json';
import L50 from 'world-atlas/land-50m.json';

export type LonLat = [number, number];
export type AtlasRes = '110m' | '50m';
export const D2R = Math.PI / 180;

type Atlas = {countries: any[]; borders: any; land: any};
const _atlas: Partial<Record<AtlasRes, Atlas>> = {};

/** The decoded atlas at one resolution — decoded once per process, never per frame. */
export const atlas = (res: AtlasRes): Atlas => {
  const hit = _atlas[res];
  if (hit) return hit;
  const topo: any = res === '50m' ? C50 : C110;
  const land: any = res === '50m' ? L50 : L110;
  const countries = (feature(topo, topo.objects.countries) as any).features;
  const borders = mesh(topo, topo.objects.countries, (a: any, b: any) => a !== b);
  const out = {countries, borders, land: feature(land, land.objects.land)};
  _atlas[res] = out;
  return out;
};

/** The resolution a view needs: 1:50m once the globe is drawn larger than the frame, else 1:110m. Decided ONCE per
 *  shot from its largest radius, so the coastline never changes detail in the middle of a move. */
export const resFor = (maxRadiusPx: number, W: number, H: number): AtlasRes =>
  maxRadiusPx > 0.9 * Math.min(W, H) ? '50m' : '110m';

export const validLonLat = (p: unknown): p is LonLat =>
  Array.isArray(p) && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]) &&
  Math.abs(p[1] as number) <= 90 && Math.abs(p[0] as number) <= 360;

/** A place's coordinates as the film wrote them: `{lon, lat}` or `[lon, lat]`. Missing or out of range THROWS — a
 *  mark without coordinates is a mark the register would have to invent a position for. */
export const lonLatOf = (v: any, what: string, shot: string): LonLat => {
  const p: unknown = Array.isArray(v) ? v : (v && typeof v === 'object' ? [v.lon, v.lat] : null);
  if (!validLonLat(p)) {
    throw new Error(`${shot}: ${what} needs coordinates — \`lon\` (-180..180) and \`lat\` (-90..90) as numbers, got ` +
      `${JSON.stringify(v)}. A place is drawn where the film says it is; pass its sourced longitude and latitude.`);
  }
  return [p[0], p[1]];
};

// ── regions ─────────────────────────────────────────────────────────────────────────────────────────────
export type Region = {id: string; name: string; f50: any; f110: any};
const editDistance = (a: string, b: string): number => {
  const d = Array.from({length: b.length + 1}, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    let prev = d[0]; d[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const cur = d[j];
      d[j] = Math.min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
  }
  return d[b.length];
};
const norm = (s: string) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');

/** A country by its Natural Earth name or ISO 3166-1 numeric code. Unknown THROWS with the nearest names. */
export const findRegion = (q: unknown, shot: string): Region => {
  const s = String(q ?? '').trim();
  if (!s) throw new Error(`${shot}: a region needs a \`name\` (Natural Earth's, e.g. "Brazil") or an ISO numeric \`id\`.`);
  const code = /^\d{1,3}$/.test(s) ? s.padStart(3, '0') : null;
  const key = norm(s);
  const pick = (fs: any[]) => fs.find((f) => (code && String(f.id) === code) || norm(String(f.properties?.name ?? '')) === key);
  const f50 = pick(atlas('50m').countries);
  if (!f50) {
    const names: string[] = atlas('50m').countries.map((f: any) => String(f.properties?.name ?? ''));
    const near = names.map((n) => [n, editDistance(norm(n), key)] as [string, number])
      .filter(([, d]) => d <= Math.max(2, Math.ceil(key.length * 0.4))).sort((a, b) => a[1] - b[1])
      .slice(0, 5).map(([n]) => n);
    throw new Error(`${shot}: the atlas has no region called ${JSON.stringify(s)}. Natural Earth names it` +
      (near.length ? ` perhaps as one of: ${near.map((n) => JSON.stringify(n)).join(', ')}` : ' differently') +
      ' — or pass its ISO 3166-1 numeric code as the name.');
  }
  // the 110m outline of the SAME country: by code where it has one, by name where it does not (Kosovo, N. Cyprus)
  const f110 = atlas('110m').countries.find((f: any) => (f50.id != null && f.id === f50.id) ||
    norm(String(f.properties?.name ?? '')) === norm(String(f50.properties?.name ?? ''))) ?? f50;
  return {id: String(f50.id ?? ''), name: String(f50.properties?.name ?? s), f50, f110};
};

/** The polygons of a (multi)polygon feature, each as its own Polygon geometry. */
const polygonsOf = (f: any): any[] => {
  const g = f?.geometry ?? f;
  if (!g) return [];
  if (g.type === 'Polygon') return [g];
  if (g.type === 'MultiPolygon') return g.coordinates.map((c: any) => ({type: 'Polygon', coordinates: c}));
  return [];
};

/** Where to aim at a set of regions, and how far they reach from that aim (degrees of arc). The aim is the centroid of
 *  the LARGEST polygon (France's centroid is otherwise pulled into the Atlantic by French Guiana), and the reach
 *  counts every part within `nearDeg` of it — an overseas territory is still highlighted, the frame does not chase it. */
export const regionFrame = (features: any[], nearDeg = 30): {center: LonLat; reach: number} => {
  // each region keeps its main body and the substantial parts NEAR it; a far-off part (French Guiana for France) or an
  // outlying speck stays lit but out of the framing — per region, so three neighbours still frame as three neighbours
  const kept: any[] = [], mains: any[] = [];
  for (const f of features) {
    const polys = polygonsOf(f);
    if (!polys.length) continue;
    const main = polys.reduce((a, b) => (geoArea(b) > geoArea(a) ? b : a));
    const mc = geoCentroid(main) as LonLat;
    mains.push(main);
    // a part is framed when it is NEAR the main body and not a speck: the Canaries (17° from Spain's centre) and the
    // Ryukyu chain set the reach of their countries and shrank the main body to a third of the view
    const mainA = geoArea(main);
    for (const p of polys) {
      if (p === main || (geoDistance(geoCentroid(p) as LonLat, mc) / D2R <= nearDeg && geoArea(p) >= 0.05 * mainA)) kept.push(p);
    }
  }
  if (!mains.length) throw new Error('regionFrame: no polygons to frame');
  const center = (mains.length === 1 ? geoCentroid(mains[0])
    : geoCentroid({type: 'GeometryCollection', geometries: mains} as any)) as LonLat;
  let reach = 0;
  for (const p of kept) for (const ring of p.coordinates) for (const v of ring) reach = Math.max(reach, geoDistance(v, center) / D2R);
  return {center, reach: Math.max(reach, 0.5)};
};

// ── projection, closed form ─────────────────────────────────────────────────────────────────────────────
/** A point's unit vector in the frame of a view centred on (lon0, lat0): x right, y up, z toward the viewer. This IS
 *  d3's rotate([-lon0, -lat0]) followed by its orthographic, written out (z > 0 is the visible hemisphere). */
export const viewVec = (lon: number, lat: number, lon0: number, lat0: number): [number, number, number] => {
  const l = (lon - lon0) * D2R, p = lat * D2R, p0 = lat0 * D2R;
  const cp = Math.cos(p);
  return [cp * Math.sin(l), Math.cos(p0) * Math.sin(p) - Math.sin(p0) * cp * Math.cos(l),
    Math.sin(p0) * Math.sin(p) + Math.cos(p0) * cp * Math.cos(l)];
};

export type GlobeView = {lon0: number; lat0: number; R: number; cx: number; cy: number};
/** Screen position of (lon, lat) raised `alt` globe radii above the surface; `vis` is whether the eye sees it (in
 *  front of the globe, or behind it but outside the disc the globe covers). */
export const orthoXY = (lon: number, lat: number, v: GlobeView, alt = 0) => {
  const [x, y, z] = viewVec(lon, lat, v.lon0, v.lat0);
  const k = v.R * (1 + alt);
  const px = v.cx + k * x, py = v.cy - k * y;
  const vis = z >= 0 || Math.hypot(k * x, k * y) > v.R;
  return {x: px, y: py, z, vis};
};

export const orthoProjection = (v: GlobeView, W: number, H: number): GeoProjection => {
  const m = Math.max(W, H) * 0.25;
  return geoOrthographic().rotate([-v.lon0, -v.lat0, 0]).scale(v.R).translate([v.cx, v.cy]).clipAngle(90)
    .clipExtent([[-m, -m], [W + m, H + m]]).precision(0.4);
};

/** The shortest way round from one longitude to another: `a + wrapDelta(a, b)` reaches b without crossing the long side. */
export const wrapDelta = (a: number, b: number) => ((((b - a) % 360) + 540) % 360) - 180;

/** A view interpolated between two, longitude the short way round. */
export const lerpView = (a: GlobeView, b: GlobeView, p: number): GlobeView => ({
  lon0: a.lon0 + wrapDelta(a.lon0, b.lon0) * p, lat0: a.lat0 + (b.lat0 - a.lat0) * p,
  // the radius moves EXPONENTIALLY so a zoom reads at a constant rate (motion-research §2, zoom-through)
  R: a.R * Math.pow(b.R / a.R, p), cx: a.cx + (b.cx - a.cx) * p, cy: a.cy + (b.cy - a.cy) * p,
});

/** The globe radius that puts a reach of `reachDeg` (arc from the aim) at `halfPx` from the centre, floored at `minR`. */
export const radiusFor = (reachDeg: number, halfPx: number, minR: number, maxR: number) => {
  const r = Math.min(85, Math.max(0.5, reachDeg)) * D2R;
  return Math.max(minR, Math.min(maxR, halfPx / Math.sin(r)));
};

// ── great circles ───────────────────────────────────────────────────────────────────────────────────────
export const arcDeg = (a: LonLat, b: LonLat) => geoDistance(a, b) / D2R;
export const greatCircle = (a: LonLat, b: LonLat) => geoInterpolate(a, b);

/** The spherical centre of a set of points and the largest arc from it to any of them. */
export const pointsFrame = (pts: LonLat[]): {center: LonLat; reach: number} => {
  const center = pts.length === 1 ? pts[0]
    : geoCentroid({type: 'MultiPoint', coordinates: pts} as any) as LonLat;
  // also count each route's MIDPOINT: a great circle bulges poleward, and its apex must be in view too
  return {center, reach: Math.max(0.5, ...pts.map((p) => arcDeg(p, center)))};
};

/** The circular mean of longitudes — the central meridian a flat map should sit on, so a route across the
 *  antimeridian (Tokyo to San Francisco) stays one continuous line instead of leaving one edge and entering the other. */
export const meanLon = (lons: number[]) => {
  const s = lons.reduce((a, l) => a + Math.sin(l * D2R), 0), c = lons.reduce((a, l) => a + Math.cos(l * D2R), 0);
  return Math.atan2(s, c) / D2R;
};

export const flatProjection = (lon0: number): GeoProjection => geoEqualEarth().rotate([-lon0, 0, 0]).precision(0.4);

export {geoPath, geoGraticule10, geoDistance, geoInterpolate, geoCentroid, geoContains};
