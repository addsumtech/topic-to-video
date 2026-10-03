// SHOT · ObjectPath — a thing the film drew travels a route through named stations and changes as it goes: its own
// clock IS its progress along the route, so it can be beans at the first station and a cup at the last. Family I
// (process / section).
//
// THE ARGUMENT SHAPE: "it goes through these, in this order, and becomes this." ConveyorBelt and InOrder carry a
// sequence of LABELS; neither carries one THING whose state changes from station to station. Here the object's t
// runs 0 → 1 from the first station to the last — (k-1)/(n-1) while it dwells at station k — so a film's object can
// draw what it looks like at every stage (pathProgress, exported for its test and for an author to read).
//
// The route is a straight track or a gentle arc (`route`), across the frame when it is wide and down it when it is
// tall; stations sit at equal arc length along it (runtime/alongPath) and are named under — or, tall, beside —
// their marks. The station the object is at is set in the accent; those passed stay ink; those ahead wait dim.
// Standalone it carries its own preview form past three unnamed stations: no words to leak.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitTextPx, wrapLines} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {rows} from '../runtime/rows';
import {pointAt} from '../runtime/alongPath';
import {drawOn} from '../runtime/draw';
import {ObjectSlot, useObjectEntry, fitAspect, type ObjectRef} from '../runtime/objectSlot';
import {DEMO_ID} from '../objects/DemoForm';

export const DURATION = 180;
export const MAX_STATIONS = 5;
export const REQUIRED_IN_FILM = ['object', 'stations'] as const;
const BG_D0 = '#eef0f3', FG_D0 = '#1b1f27', DIM_D0 = '#5d6573', ACC_D0 = '#2f5bd8', LINE_D0 = '#c9ced6';
const DEMO_OBJECT: ObjectRef = {id: DEMO_ID};
const DEMO_STATIONS = ['', '', ''];        // the preview's three unnamed stops — no words to leak
const TRAVEL_A = 0.22, TRAVEL_B = 0.84, DWELL = 0.4;

/** Progress along the route (0 → 1) at the beat's t: a dwell at each station, an eased move between them. */
export const pathProgress = (t: number, n: number): number => {
  if (n < 2) return 1;
  const move = 1 - DWELL;
  const u = clamp01(seg(t, TRAVEL_A, TRAVEL_B)) * (n * DWELL + (n - 1) * move);
  let acc = 0;
  for (let k = 0; k < n; k++) {
    if (u <= acc + DWELL) return k / (n - 1);
    acc += DWELL;
    if (k === n - 1) return 1;
    if (u <= acc + move) return (k + easeInOutCubic((u - acc) / move)) / (n - 1);
    acc += move;
  }
  return 1;
};

export const ObjectPath: React.FC<{
  object?: ObjectRef;         // the thing the film drew (runtime/objectSlot); its t is its progress along the route
  stations?: string[];        // 2-5 station names, in order
  route?: 'line' | 'arc';     // the track's shape
  title?: string;             // one line over the route
  kicker?: string;            // a spaced label in the title band
}> = ({object: OBJECT = DEMO_OBJECT, stations: STATIONS_IN = DEMO_STATIONS, route = 'line', title = '', kicker = ''} = {}) => {
  const STATIONS = rows<string>(STATIONS_IN, 'stations', 'ObjectPath');
  const n = STATIONS.length;
  if (n < 2 || n > MAX_STATIONS) {
    throw new Error(`ObjectPath takes 2-${MAX_STATIONS} \`stations\` (got ${n}) — one station is not a route, and past ` +
      'five each stop is too brief to be seen.');
  }
  if (STATIONS_IN !== DEMO_STATIONS) {
    STATIONS.forEach((s, i) => {
      if (typeof s !== 'string' || !s.trim()) {
        throw new Error(`ObjectPath: station ${i + 1} has no name (got ${JSON.stringify(s)}).`);
      }
    });
  }
  if (route !== 'line' && route !== 'arc') {
    throw new Error(`ObjectPath: \`route\` is 'line' or 'arc' — got ${JSON.stringify(route)}`);
  }
  const entry = useObjectEntry(OBJECT);
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Inter, system-ui, sans-serif)';
  const bodyF = 'var(--f-body, Inter, system-ui, sans-serif)';
  const mono = 'var(--f-mono, "JetBrains Mono", ui-monospace, monospace)';
  const U = Math.min(W, H);
  const zTop = CONTENT_TOP, zBot = contentBottom(W, H), zH = zBot - zTop;
  const wide = W >= H;

  const titleLead = leading(title, 1.12);
  const titlePx = title ? fitTextPx(title, W * 0.84, Math.round(U * 0.042), {usable: 1}) : 0;
  const titleH = title ? titlePx * titleLead + U * 0.03 : 0;
  const lblPx = Math.round(U * 0.022);
  const sw = Math.max(2, Math.round(U * 0.004));

  // THE ROUTE, THE OBJECT'S ROOM AND THE NAMES, per orientation
  let d: string, ob: number, lblW: number, place: (p: {x: number; y: number}) => {x: number; y: number};
  let labelAt: (p: {x: number; y: number}) => {left: number; top: number; align: 'center' | 'left'};
  if (wide) {
    const x0 = W * 0.1, x1 = W * 0.9, spacing = (x1 - x0) / (n - 1);
    lblW = Math.min(spacing * 0.9, W * 0.24);
    const lblH = Math.max(lblPx * 1.3, ...STATIONS.map((s) => (s ? wrapLines(s, lblPx, lblW) * lblPx * leading(s, 1.3) : 0)));
    const lift = route === 'arc' ? zH * 0.22 : 0;              // the arc's control offset; its apex rises lift / 2
    const yTrack = zBot - lblH - U * 0.045;
    // The first and last stations sit AT the track's own endpoints (x0, x1) — both routes start and end there,
    // an arc only bows the ones in between — so the object centred on either one only has `x0` of clear frame
    // left on its far side. Capped only by the room ABOVE the track, the object at a short route (few stations,
    // so little station-spacing room to shrink it) ran wider than that margin and rode off the frame's own edge
    // at the first and last stop — not merely close to it: past it, the far part of the object never drawn.
    // The 0.9 leaves it the same clearance `lblW` already keeps from a station's own neighbour, above.
    ob = Math.max(U * 0.1, Math.min(zH * 0.46, spacing * 0.95, W * 0.26, 2 * x0 * 0.9,
      yTrack - lift / 2 - zTop - titleH));
    d = route === 'arc' ? `M ${x0} ${yTrack} Q ${W / 2} ${yTrack - lift} ${x1} ${yTrack}` : `M ${x0} ${yTrack} L ${x1} ${yTrack}`;
    place = (p) => ({x: p.x, y: p.y - ob / 2 - sw});          // the object stands on the track
    labelAt = (p) => ({left: p.x - lblW / 2, top: p.y + U * 0.025, align: 'center'});
  } else {
    const xT = W * 0.3;
    ob = Math.max(U * 0.1, Math.min(W * 0.34, (zH - titleH - U * 0.04) / (n + 0.4)));
    const yA = zTop + titleH + ob / 2 + U * 0.01, yB = zBot - ob / 2 - U * 0.01;
    d = route === 'arc' ? `M ${xT} ${yA} Q ${xT - W * 0.12} ${(yA + yB) / 2} ${xT} ${yB}` : `M ${xT} ${yA} L ${xT} ${yB}`;
    const lx = xT + ob / 2 + U * 0.035;
    lblW = W * 0.94 - lx;
    place = (p) => p;                                          // the object rides centred on the track
    labelAt = (p) => ({left: lx, top: p.y - lblPx * 0.68, align: 'left'});
  }
  const drawn = fitAspect({x: 0, y: 0, w: ob, h: ob}, entry.meta?.aspect);
  const stops = STATIONS.map((_, k) => pointAt(d, k / (n - 1)));
  const trackIn = easeOutCubic(clamp01(seg(t, 0.04, 0.2)));
  const p = pathProgress(t, n);
  const here = place(pointAt(d, p));
  const box = {x: here.x - drawn.w / 2, y: here.y - drawn.h / 2, w: drawn.w, h: drawn.h};
  const cur = p * (n - 1);                                      // stations reached: k <= cur
  const kicked = easeOutCubic(clamp01(seg(t, 0.03, 0.18)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', opacity: kicked,
          font: `600 ${Math.round(U * 0.018)}px/1.2 ${mono}`, color: ACC, letterSpacing: dna?.labelSpacing ?? '0.14em',
          textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>
      ) : null}
      {title ? (
        <div style={{position: 'absolute', left: W * 0.08, top: zTop, width: W * 0.84, textAlign: 'center',
          opacity: kicked, font: `700 ${titlePx}px/${titleLead} ${disp}`, color: FG, whiteSpace: 'nowrap'}}>{title}</div>
      ) : null}
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <path d={d} fill="none" stroke={LINE} strokeWidth={sw} strokeLinecap="round" {...drawOn(trackIn)} />
        {stops.map((s, k) => {
          const shown = trackIn >= k / (n - 1) - 1e-6;
          const reached = k <= cur + 1e-6;
          return shown ? <circle key={k} cx={s.x} cy={s.y} r={Math.max(4, U * 0.008)} fill={reached ? ACC : 'none'}
            stroke={reached ? ACC : LINE} strokeWidth={sw} /> : null;
        })}
      </svg>
      <ObjectSlot object={OBJECT} box={box} t={p} />
      {STATIONS.map((s, k) => {
        if (!s) return null;
        const at = labelAt(stops[k]);
        const on = easeOutCubic(clamp01(seg(trackIn, k / (n - 1) - 0.25, k / (n - 1))));
        const isHere = Math.abs(cur - k) < 0.02;                  // dwelling at this station
        const passed = !isHere && k < cur;
        return (
          <div key={k} style={{position: 'absolute', left: at.left, top: at.top, width: lblW, textAlign: at.align,
            opacity: on, font: `${isHere ? 700 : 500} ${lblPx}px/${leading(s, 1.3)} ${bodyF}`,
            color: isHere ? ACC : passed ? FG : DIM, textWrap: 'balance'}}>{s}</div>
        );
      })}
    </AbsoluteFill>
  );
};
export default ObjectPath;
