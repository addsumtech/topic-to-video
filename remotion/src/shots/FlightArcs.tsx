// SHOT · Flight Arcs — ROUTE: the film's places on the Earth, and the routes between them flown as great circles — each
// arc lifts off the surface, draws from its origin with a bright head travelling it, and lands with a ring; then a
// marker keeps flying every route so the frame stays a network in use, not a diagram of one.
//
// WHAT IT ARGUES. That these places are connected, and HOW FAR APART they really are: a great circle is the shortest
// path on the sphere, so the arc's length and its poleward bulge are the geometry itself (London to Tokyo crosses
// Siberia, not the Indian Ocean). Not for abstract connections with no geography (a network register such as
// KnowledgeGraph or MapRoutes), nor a single place (GlobeFocus).
//
// WHAT COMES FROM WHERE. Places are the film's: a label and a sourced lon/lat each. Routes name two places. The Earth is
// Natural Earth's (runtime/geo.ts). Nothing is looked up by name; a route to a place the film did not give throws.
//
// THE VIEW. `globe` (orthographic) centres on the places' spherical centre and fits them — every endpoint AND every
// route's midpoint, because a great circle bulges poleward and its apex has to be in view. When they span more than a
// hemisphere can show, `auto` switches to `flat`: Equal Earth, its central meridian on the places' circular-mean
// longitude, so a route across the antimeridian (Tokyo to San Francisco) stays one continuous line — d3 still cuts
// any line that does cross the map's edge, so nothing is ever drawn across the whole map.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, easeOutBack, radians} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, TITLE_Y} from '../runtime/layout';
import {useDNA, readableOn, dimOn, mix} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {hasCJK} from '../runtime/cjkType';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {Earth} from '../runtime/earth';
import {lonLatOf, LonLat, GlobeView, radiusFor, resFor, orthoXY, arcDeg, greatCircle, pointsFrame, meanLon,
  flatProjection, geoPath} from '../runtime/geo';
import {placeLabels, Rect} from '../runtime/labelPlace';
import {useGlide} from '../runtime/glide';
import {useLabelWidths} from '../runtime/labelWidths';

export const DURATION = 210; // 7s
export const MAX_PLACES = 10, MAX_ROUTES = 8;
type PlaceIn = {id?: string; label?: string; lon?: number; lat?: number};
type RouteIn = {from?: string; to?: string};

const BG_D0 = '#05080f', FG_D0 = '#eef2f8', DIM_D0 = '#8d97aa', ACC_D0 = '#5aa9ff', ACC2_D0 = '#ffcf5a';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

// Placeholder copy: three places named only by their role; the coordinates are arbitrary points chosen to show the
// register's geometry (a long arc and a short one), not a claim about anywhere.
const DEMO_PLACES: PlaceIn[] = [{id: 'a', label: 'origin', lon: -0.13, lat: 51.5}, {id: 'b', label: 'stop', lon: 55.3, lat: 25.3},
  {id: 'c', label: 'destination', lon: 139.7, lat: 35.7}];
const DEMO_ROUTES: RouteIn[] = [{from: 'a', to: 'b'}, {from: 'b', to: 'c'}];

const SAMPLES = 96;

export const FlightArcs: React.FC<{
  title?: string;
  /** 2-10 places: `label`, sourced `lon`/`lat`, optional `id` for routes to name */
  places?: PlaceIn[];
  /** 1-8 routes, each `{from, to}` naming two places by id or label */
  routes?: RouteIn[];
  /** `globe`, `flat`, or `auto` (globe when one hemisphere holds every place and route) */
  view?: 'auto' | 'globe' | 'flat';
  note?: string;
  accent?: string;
}> = ({title = '', places: placesIn = DEMO_PLACES, routes: routesIn = DEMO_ROUTES, view: viewIn = 'auto', note = '', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const glide = useGlide();
  const {width: W, height: H, durationInFrames: DUR, fps} = useVideoConfig();
  const S = 'FlightArcs';

  if ((placesIn === DEMO_PLACES) !== (routesIn === DEMO_ROUTES)) {
    throw new Error(`FlightArcs: pass \`places\` and \`routes\` together — one without the other would be drawn against the demo's.`);
  }
  const PL = rows<PlaceIn>(placesIn, 'places', S);
  const RT = rows<RouteIn>(routesIn, 'routes', S);
  if (PL.length < 2 || PL.length > MAX_PLACES) throw new Error(`${S}: needs 2-${MAX_PLACES} \`places\` (got ${PL.length}).`);
  if (RT.length < 1 || RT.length > MAX_ROUTES) throw new Error(`${S}: needs 1-${MAX_ROUTES} \`routes\` (got ${RT.length}); a route list longer than that is a timetable.`);
  const places = PL.map((p, i) => {
    const label = String(p?.label ?? '').trim();
    if (!label) throw new Error(`${S}: place ${i + 1} has no \`label\`.`);
    return {id: String(p?.id ?? label), label, ll: lonLatOf(p, `place ${i + 1} ("${label}")`, S)};
  });
  const find = (k: unknown, i: number, end: string) => {
    const key = String(k ?? '').trim();
    const hit = places.find((p) => p.id === key) ?? places.find((p) => p.label === key);
    if (!hit) throw new Error(`${S}: route ${i + 1}'s \`${end}\` names ${JSON.stringify(key)}, which is not one of the places ` +
      `(${places.map((p) => p.id).join(', ')}). A route is drawn between places the film gave.`);
    return hit;
  };
  const routes = RT.map((r, i) => {
    const a = find(r?.from, i, 'from'), b = find(r?.to, i, 'to');
    if (a === b) throw new Error(`${S}: route ${i + 1} starts and ends at ${a.label}.`);
    const len = arcDeg(a.ll, b.ll);
    if (len < 0.05) throw new Error(`${S}: route ${i + 1} (${a.label} → ${b.label}) has no length at this scale.`);
    if (len > 179) throw new Error(`${S}: ${a.label} and ${b.label} are antipodal — no single great circle joins them.`);
    return {a, b, len, interp: greatCircle(a.ll, b.ll)};
  });

  // ── palette ──────────────────────────────────────────────────────────────────────────────────────────
  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);
  const ACC = accIn ?? dna?.accent ?? ACC_D0;
  const HEAD = dna?.accent2 ?? ACC2_D0;
  const CHIP = mix(BG, '#000000', 0.25);
  const CHIP_INK = readableOn(CHIP, FG, '#ffffff', '#0b0f17');

  // ── the view, decided once ───────────────────────────────────────────────────────────────────────────
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const noteH = note ? Math.round(U * 0.05) : 0;
  const cx = W / 2, cy = (zTop + zBot - noteH) / 2;
  const zoneW = W * 0.9, zoneH = zBot - zTop - noteH;
  const zoneMin = Math.min(zoneW, zoneH);
  const keyPts: LonLat[] = [...places.map((p) => p.ll), ...routes.map((r) => r.interp(0.5) as LonLat)];
  const pf = pointsFrame(keyPts);
  const mode: 'globe' | 'flat' = viewIn === 'globe' || viewIn === 'flat' ? viewIn : (pf.reach <= 70 ? 'globe' : 'flat');
  if (mode === 'globe' && pf.reach > 80) {
    throw new Error(`${S}: these places span ${pf.reach.toFixed(0)}° from their centre — more than one side of a globe ` +
      'shows. Use `view: "flat"` (or `auto`).');
  }
  const rFull = 0.47 * zoneMin;
  const R = mode === 'globe' ? radiusFor(pf.reach * 1.1, 0.42 * zoneMin, rFull, rFull * 40) : 0;
  const gv: GlobeView = {lon0: pf.center[0], lat0: pf.center[1], R, cx, cy};
  const flat = mode === 'flat' ? (() => {
    const lon0 = meanLon(places.map((p) => p.ll[0]));
    const pad = U * 0.08;
    const proj = flatProjection(lon0);
    const target = {type: 'FeatureCollection', features: routes.map((r) => ({type: 'Feature', properties: {},
      geometry: {type: 'LineString', coordinates: Array.from({length: 17}, (_, k) => r.interp(k / 16))}}))};
    proj.fitExtent([[W / 2 - zoneW / 2 + pad, zTop + pad], [W / 2 + zoneW / 2 - pad, zBot - noteH - pad]], target as any);
    return proj;
  })() : undefined;
  // the radius the flat map is drawn at, in globe terms, for choosing the coastline's resolution
  const res = resFor(mode === 'globe' ? R : (flat!.scale() as number), W, H);
  const fpath = flat ? geoPath(flat) : null;

  // a point at fraction s along route r, lifted (globe) or on the surface (flat)
  const lift = (len: number) => 0.04 + 0.16 * (len / 180);
  const at = (r: typeof routes[number], s: number, lifted = true) => {
    const ll = r.interp(s) as LonLat;
    if (mode === 'globe') return orthoXY(ll[0], ll[1], gv, lifted ? lift(r.len) * Math.sin(Math.PI * s) : 0);
    const xy = flat!(ll)!;
    return {x: xy[0], y: xy[1], z: 1, vis: true};
  };

  // ── timing: routes draw one after another, overlapping ───────────────────────────────────────────────
  const n = routes.length;
  const DRAW_A = 0.14, DRAW_B = 0.7;
  const step = n > 1 ? Math.min(0.12, (DRAW_B - DRAW_A - 0.22) / (n - 1)) : 0;
  const winOf = (i: number): [number, number] => [DRAW_A + i * step, DRAW_A + i * step + Math.max(0.22, DRAW_B - DRAW_A - step * (n - 1))];

  // the drawn part of a route: visible runs only (an arc can pass behind the globe)
  const runs = (r: typeof routes[number], s0: number, s1: number, lifted = true): string => {
    if (mode === 'flat') {
      const k = Math.max(2, Math.ceil(SAMPLES * (s1 - s0)));
      return fpath!({type: 'LineString', coordinates: Array.from({length: k + 1}, (_, j) => r.interp(s0 + (s1 - s0) * j / k))} as any) ?? '';
    }
    const k = Math.max(2, Math.ceil(SAMPLES * (s1 - s0)));
    let d = '', pen = false;
    for (let j = 0; j <= k; j++) {
      const p = at(r, s0 + (s1 - s0) * j / k, lifted);
      if (!p.vis || (!lifted && p.z < 0)) { pen = false; continue; }
      d += `${pen ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
      pen = true;
    }
    return d;
  };

  // ── labels at the settled view ───────────────────────────────────────────────────────────────────────
  const lblPx = Math.round(U * 0.025);
  const padX = Math.round(U * 0.012), padY = Math.round(U * 0.007);
  const lw = useLabelWidths(places.map((p) => p.label), BODY, 600, lblPx);
  const dotR = Math.round(U * 0.008);
  const ends = places.map((p) => (mode === 'globe' ? orthoXY(p.ll[0], p.ll[1], gv) : (() => {
    const xy = flat!(p.ll)!; return {x: xy[0], y: xy[1], z: 1, vis: true};
  })()));
  const box: Rect = {x0: W * 0.04, y0: zTop, x1: W * 0.96, y1: zBot - noteH};
  const placed = lw.widths ? placeLabels(places.map((p, i) => ({x: ends[i].x, y: ends[i].y,
    w: Math.ceil(lw.widths![i] * 1.04) + padX * 2, h: Math.round(lblPx * 1.2) + padY * 2, text: p.label, r: dotR * 1.6})),
  box, Math.round(U * 0.014), [], S) : [];
  // a place lands when the first route that touches it arrives there (or leaves it)
  const landT = places.map((p) => {
    const ts = routes.flatMap((r, i) => (r.a === p ? [winOf(i)[0]] : r.b === p ? [winOf(i)[1] - 0.04] : []));
    return ts.length ? Math.min(...ts) : DRAW_A;
  });

  const titleK = useKinetic({text: title || ' ', w: Math.round(W * 0.84), nowrap: true, fit: 'box',
    font: {family: DISPLAY, weight: 640, size: Math.round(U * 0.046), minSize: Math.round(U * 0.03), lineHeight: 1.1,
      tracking: hasCJK(title) ? 0 : -0.015}});
  const noteK = useKinetic({text: note || ' ', w: Math.round(W * 0.84), fit: 'box', maxLines: 2, h: noteH,
    font: {family: MONO, weight: 500, size: Math.round(U * 0.021), minSize: Math.round(U * 0.017), lineHeight: 1.3}});

  const show = easeOutCubic(seg(t, 0, 0.12));
  const strokeW = Math.max(2.5, U * 0.0034);
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? `radial-gradient(120% 110% at 50% 40%, ${mix(BG, ACC, 0.06)}, ${BG} 70%)`}}>
      <Earth uid="flightarcs" W={W} H={H} res={res} view={mode === 'globe' ? gv : undefined} flat={flat} show={show}
        ink={{bg: BG, fg: FG, accent: ACC}} />
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="fa-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={U * 0.005} result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {routes.map((r, i) => {
          const [a, b] = winOf(i);
          const p = easeInOutCubic(seg(t, a, b));
          if (p <= 0) return null;
          const tail = Math.max(0, p - 0.16);
          const head = at(r, p);
          // after it lands, a marker keeps flying the route one way, origin to destination, on a loop whose period is
          // in seconds (runtime/motion radians — never a vibration); a 0→1→0 modulator would shuttle it back and forth
          const cyc = radians(t, DUR, fps, 3 + r.len / 60, i * 0.37) / (2 * Math.PI);
          const loop = p >= 1 ? cyc - Math.floor(cyc) : -1;
          const lp = loop >= 0 ? at(r, loop) : null;
          return (
            <g key={i}>
              {/* the ground track under a lifted arc is what makes its height read as height */}
              {mode === 'globe' ? <path d={runs(r, 0, p, false)} fill="none" stroke={ACC} strokeOpacity={0.22} strokeWidth={strokeW * 0.7}
                strokeDasharray={`${strokeW * 1.5} ${strokeW * 2.5}`} strokeLinecap="round" /> : null}
              <path d={runs(r, 0, p)} fill="none" stroke={ACC} strokeOpacity={0.92} strokeWidth={strokeW} strokeLinecap="round" filter="url(#fa-glow)" />
              {p < 1 ? <path d={runs(r, tail, p)} fill="none" stroke={HEAD} strokeWidth={strokeW * 1.6} strokeLinecap="round" filter="url(#fa-glow)" /> : null}
              {p < 1 && head.vis ? <circle cx={head.x} cy={head.y} r={strokeW * 2.2} fill={HEAD} filter="url(#fa-glow)" /> : null}
              {lp && lp.vis ? <circle cx={lp.x} cy={lp.y} r={strokeW * 1.6} fill={HEAD} opacity={Math.sin(Math.PI * loop) * 0.9} filter="url(#fa-glow)" /> : null}
            </g>
          );
        })}
        {places.map((p, i) => {
          const e = ends[i];
          if (!e.vis || e.z < 0) return null;
          const a = easeOutBack(seg(t, landT[i], landT[i] + 0.1));
          const ring = clamp01(seg(t, landT[i], landT[i] + 0.2));
          return (
            <g key={i} opacity={clamp01(a)}>
              <circle cx={e.x} cy={e.y} r={dotR * (1.2 + 2.4 * ring)} fill="none" stroke={HEAD} strokeOpacity={0.6 * (1 - ring)} strokeWidth={2} />
              <circle cx={e.x} cy={e.y} r={dotR * Math.max(0, a)} fill={FG} stroke={ACC} strokeWidth={2.5} />
            </g>
          );
        })}
        {placed.map((q, i) => {
          const a = easeOutCubic(seg(t, landT[i] + 0.04, landT[i] + 0.14));
          const lx = Math.max(q.x0, Math.min(q.ax, q.x1)), ly = Math.max(q.y0, Math.min(q.ay, q.y1));
          return q.leader ? <line key={i} x1={q.ax} y1={q.ay} x2={q.ax + (lx - q.ax) * a} y2={q.ay + (ly - q.ay) * a}
            stroke={FG} strokeOpacity={0.5} strokeWidth={1.3} /> : null;
        })}
      </svg>
      {lw.anchor}
      {placed.map((q, i) => {
        const a = easeOutCubic(seg(t, landT[i] + 0.04, landT[i] + 0.14));
        return (
          <div key={i} style={{position: 'absolute', left: 0, top: 0, width: q.x1 - q.x0, height: q.y1 - q.y0,
            transform: glide(`translate(${q.x0}px, ${q.y0}px)`, true), opacity: a, boxSizing: 'border-box',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: `${padY}px ${padX}px`,
            borderRadius: Math.round(lblPx * 0.35), background: `${CHIP}d9`, border: `1px solid ${mix(CHIP, FG, 0.22)}`,
            color: CHIP_INK, whiteSpace: 'nowrap', font: `600 ${lblPx}px/1.2 ${BODY}`}}>{places[i].label}</div>
        );
      })}
      {title ? (
        <KineticText k={titleK} x={Math.round(W * 0.08)} y={TITLE_Y} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.04}, enter: {by: 'line', at: 0.03, stagger: 0.1, dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.4}}} />
      ) : titleK.anchor}
      {note ? (
        <KineticText k={noteK} x={Math.round(W * 0.08)} y={zBot - noteH} color={DIM} id="note"
          motion={{from: {opacity: 0, y: 0.4}, enter: {by: 'word', at: 0.7, stagger: 0.03, dur: 0.5, ease: 'power3', cueKeys: ['note'], until: 0.86}}} />
      ) : noteK.anchor}
    </AbsoluteFill>
  );
};
export default FlightArcs;
