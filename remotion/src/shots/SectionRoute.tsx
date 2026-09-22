// SHOT · SectionRoute — a load travels a ROUTE through a layered cross-section — the indirect route climbs
// and drops through levels it did not need, the direct route cuts straight through / why a shortcut was
// worth digging.
//
// THE ARGUMENT SHAPE: some processes are expensive not because any step is hard but because the route
// crosses levels it has no business crossing. Drawing the section makes the waste legible — you can SEE
// the climbs — and drawing the direct route on the same section shows exactly what the shortcut removed.
// The topic arrives entirely through props: name the levels, give the waypoints, and any film with a
// "why did they bother digging/rerouting/flattening this" beat can reach for it.
//
// Reads as a measured drawing rather than a diagram: the levels are ruled lines with a leader label, the
// route is a drawn polyline with a load riding it, and every LIFT (a vertical run) is called out with its
// own tick, because the lift is the thing being argued about.
//
// THE ROUTE IS THE FILM'S OR THERE IS NO ROUTE. `levels` and `route` used to default independently, so a
// film that named its own levels but no route got the demo's route drawn through them — climb from the
// bottom level to the top and back down, "start" to "end" — which is exactly the claim this register exists
// to make ("it crossed levels it had no business crossing"), made about the film's section by nobody. A
// route of fewer than two stops was silently replaced by a flat line across level 0, and a stop naming a
// level the section does not have was clamped onto the nearest one. Now `levels` and `route` come together
// or not at all (neither is the standalone demo), a route needs at least two stops, and every stop needs an
// integer `level` inside the section and an `x` in 0..1, or the shot throws saying which.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP, wrapLines} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s

// D0 — the no-DNA fallbacks, kept as named constants so a literal can never be written into an expression
// that also reads a DNA token.
const BG_D0 = '#0a0f16', FG_D0 = '#e8eef6', DIM_D0 = '#93a1b4';
const ACC_D0 = '#e2603f', ACC2_D0 = '#5fa8a0', LINE_D0 = '#22303f';

type Stop = {level: number; x: number; label?: string};

// The standalone demo's section. Module constants so the shot can tell "the film passed neither" (identity)
// from "the film passed one of the two", which it refuses.
const DEFAULT_LEVELS: string[] = ['Upper level', 'Middle level', 'Lower level'];
const DEFAULT_ROUTE: Stop[] = [{level: 2, x: 0.06, label: 'start'}, {level: 0, x: 0.34}, {level: 0, x: 0.66},
                               {level: 2, x: 0.94, label: 'end'}];

export const SectionRoute: React.FC<{
  kicker?: string;
  levels?: string[];          // top → bottom; the section's bands
  route?: Stop[];             // waypoints, in travel order; x is 0..1 across the section
  verdict?: string;           // what the route costs / saves — lands at the end
  note?: string;
  markLifts?: boolean;        // call out each vertical run (the point of the indirect case)
}> = ({
  kicker = 'THE ROUTE',
  levels: LEVELS = DEFAULT_LEVELS,
  route: ROUTE = DEFAULT_ROUTE,
  verdict = '',
  note = '',
  markLifts = true} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();

  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, system-ui, sans-serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';

  // ── the section and its route, from the film or not at all (see the header).
  if ((LEVELS === DEFAULT_LEVELS) !== (ROUTE === DEFAULT_ROUTE)) {
    throw new Error(LEVELS === DEFAULT_LEVELS
      ? 'SectionRoute got a `route` but no `levels`: its stops name level indices, and without the film\'s ' +
        'levels they would be drawn on the demo\'s "Upper / Middle / Lower level". Pass `levels` (top → bottom).'
      : 'SectionRoute got `levels` but no `route`, so it would draw the demo\'s climb-and-drop through the ' +
        'film\'s section — the very claim this register makes, made by nobody. Pass `route: [{level, x, label?}]` ' +
        'in travel order.');
  }
  if (!Array.isArray(LEVELS) || LEVELS.length < 2) {
    throw new Error(`SectionRoute needs at least 2 \`levels\` (got ${Array.isArray(LEVELS) ? LEVELS.length : typeof LEVELS}) — a section with one level has nothing to climb.`);
  }
  if (!Array.isArray(ROUTE) || ROUTE.length < 2) {
    throw new Error(`SectionRoute needs a \`route\` of at least 2 stops (got ${Array.isArray(ROUTE) ? ROUTE.length : typeof ROUTE}) — ` +
      'a start and an end. It no longer draws a stand-in flat line in place of a route it was not given.');
  }
  ROUTE.forEach((st, i) => {
    const lv = (st as any)?.level, x = (st as any)?.x;
    if (!(Number.isInteger(lv) && lv >= 0 && lv < LEVELS.length)) {
      throw new Error(`SectionRoute: stop ${i + 1} has level ${JSON.stringify(lv)}; it must be an integer index into ` +
        `\`levels\` (0 = "${LEVELS[0]}" … ${LEVELS.length - 1} = "${LEVELS[LEVELS.length - 1]}"). A stop off the ` +
        'section would otherwise be clamped onto a level the route never visited.');
    }
    if (!(typeof x === 'number' && x >= 0 && x <= 1)) {
      throw new Error(`SectionRoute: stop ${i + 1} needs \`x\` in 0..1 across the section, got ${JSON.stringify(x)}.`);
    }
  });

  // ── geometry. The section fills the content zone; every measure is a FRACTION of the frame so the shot
  // reflows at 9:16 / 1:1 / 4:5 instead of running off the edge.
  const top = CONTENT_TOP + H * 0.06;
  const labelW = Math.min(W * 0.20, 300);
  const x0 = labelW + W * 0.05, x1 = W - W * 0.06;
  // THE FOOT IS RESERVED FROM THE TYPE THAT GOES IN IT. `H * 0.09` was sized for the VERDICT alone
  // ("leave room for the verdict under the section"); the `note` was added under it later and the
  // reserve never grew, so a film that passed both printed the note 33px INSIDE the caption band and
  // the burned subtitle drew straight over it — measured on a delivered 30-beat film, beat 2.
  // And "one line each" is a LATIN assumption: a Han glyph is a full em, so the same note wraps in a
  // column where the English one did not. Both blocks are measured in the column they actually wrap
  // in, and the section yields by what they need, floored at the original H*0.09 so every film that
  // fits in one line lays out exactly as before. `x0` depends only on W, so there is no loop here.
  const footW = x1 - x0;
  const VERDICT_PX = Math.round(W * 0.0225), NOTE_PX = Math.round(W * 0.0125);
  const FOOT_GAP = H * 0.035;                         // the section's foot to the verdict's top
  const vH = verdict ? wrapLines(String(verdict), VERDICT_PX, footW) * VERDICT_PX * 1.25 : 0;
  const nH = note ? wrapLines(String(note), NOTE_PX, footW) * NOTE_PX * 1.4 : 0;
  // the note used to be pinned W*0.030 below the verdict's TOP, which a verdict of two lines runs
  // through. It now clears the verdict's real height, never closer than the original spacing.
  const noteOff = note ? Math.max(Math.round(W * 0.030), vH + Math.round(H * 0.010)) : 0;
  const footH = FOOT_GAP + (note ? noteOff + nH : vH) + H * 0.012;
  const bottom = H - captionBand(W, H) - Math.max(H * 0.09, footH);
  const nL = LEVELS.length;
  const bandH = (bottom - top) / (nL - 1);
  const yOf = (lv: number) => top + Math.max(0, Math.min(nL - 1, lv)) * bandH;
  const xOf = (f: number) => x0 + clamp01(f) * (x1 - x0);

  const stops = ROUTE;
  const pts = stops.map((s) => ({x: xOf(s.x), y: yOf(s.level), label: s.label, level: s.level}));

  // path length per segment, so the load moves at a CONSTANT speed rather than one segment per beat
  const segLen = pts.slice(1).map((p, i) => Math.hypot(p.x - pts[i].x, p.y - pts[i].y));
  const total = segLen.reduce((a, b) => a + b, 0) || 1;
  const cum: number[] = [0];
  segLen.forEach((l) => cum.push(cum[cum.length - 1] + l));

  // ── timing: rules draw → route travels → verdict lands
  const rules = easeOutCubic(clamp01(seg(t, 0.04, 0.26)));
  const travel = easeOutCubic(clamp01(seg(t, 0.30, 0.80)));
  const settled = easeOutExpo(clamp01(seg(t, 0.80, 0.94)));

  const walked = travel * total;
  // the load's position along the polyline
  let li = 0;
  while (li < segLen.length - 1 && cum[li + 1] < walked) li++;
  const inSeg = segLen[li] > 0 ? clamp01((walked - cum[li]) / segLen[li]) : 1;
  const loadX = pts[li].x + (pts[li + 1].x - pts[li].x) * inSeg;
  const loadY = pts[li].y + (pts[li + 1].y - pts[li].y) * inSeg;

  const drawn = pts.map((p, i) => ({...p, on: clamp01((walked - cum[i]) / Math.max(1e-6, segLen[i] || 1))}));
  const dot = Math.max(5, Math.round(W * 0.005));
  const stroke = Math.max(2, Math.round(W * 0.0022));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {/* kicker */}
      <div style={{position: 'absolute', top: CONTENT_TOP - H * 0.055, left: W * 0.05,
        font: `600 ${Math.round(W * 0.0125)}px/1.2 ${mono}`, letterSpacing: dna?.labelSpacing ?? '0.14em',
        color: ACC, opacity: rules,
        textTransform: (dna?.uppercaseLabels ?? true) ? 'uppercase' : 'none'}}>{kicker}</div>

      {/* the section: one ruled line per level, labelled at the left */}
      {LEVELS.map((name, i) => {
        const y = yOf(i);
        const on = clamp01((rules * nL) - i);
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: x0, top: y, width: (x1 - x0) * on, height: stroke,
              background: LINE}} />
            <div style={{position: 'absolute', left: W * 0.05, top: y - Math.round(W * 0.016),
              width: labelW, textAlign: 'right', opacity: on,
              font: `500 ${Math.round(W * 0.0135)}px/1.25 ${disp}`, color: DIM}}>{name}</div>
          </React.Fragment>
        );
      })}

      {/* the route, drawing segment by segment */}
      {drawn.slice(0, -1).map((p, i) => {
        const q = drawn[i + 1];
        const on = p.on;
        if (on <= 0) return null;
        const isLift = Math.abs(q.y - p.y) > 1;
        const ex = p.x + (q.x - p.x) * on, ey = p.y + (q.y - p.y) * on;
        const len = Math.hypot(ex - p.x, ey - p.y);
        const ang = Math.atan2(ey - p.y, ex - p.x) * 180 / Math.PI;
        return (
          <div key={i} style={{position: 'absolute', left: p.x, top: p.y - stroke / 2,
            width: len, height: stroke, transformOrigin: '0 50%', transform: `rotate(${ang}deg)`,
            background: isLift && markLifts ? ACC2 : ACC}} />
        );
      })}

      {/* every LIFT gets its own tick — the vertical runs are what the beat is arguing about */}
      {markLifts && drawn.slice(0, -1).map((p, i) => {
        const q = drawn[i + 1];
        // `on` for the LAST segment is (total - cum[i]) / segLen[i], which floating point lands at 0.9999… —
        // so the final lift of every route never got its tick, and the frame called out one climb and not the
        // other. Every lift is marked the same way once it has been travelled.
        if (Math.abs(q.y - p.y) < 2 || p.on < 1 - 1e-6) return null;
        // ON the run it marks, not at the segment's start: a diagonal run's start is nowhere near it
        const mx = (p.x + q.x) / 2, my = (p.y + q.y) / 2;
        return (
          <div key={'lift' + i} style={{position: 'absolute', left: mx + Math.round(W * 0.010),
            top: my - Math.round(W * 0.011),
            font: `600 ${Math.round(W * 0.0105)}px/1.2 ${mono}`, letterSpacing: '0.08em', color: ACC2,
            opacity: 1}}>&#8593;&#8595;</div>
        );
      })}

      {/* the load riding the route */}
      <div style={{position: 'absolute', left: loadX - dot, top: loadY - dot, width: dot * 2,
        height: dot * 2, borderRadius: dna?.radius ? Math.min(dot, dna.radius) : 2,
        background: ACC, boxShadow: `0 0 0 ${Math.max(2, Math.round(stroke * 1.6))}px ${dna?.bg ?? BG_D0}`}} />

      {/* waypoint labels */}
      {/* A label under a point on the BOTTOM rule lands in the verdict's line — put those ABOVE the point
          instead. Nothing about the shot's meaning depends on which side the label sits. */}
      {drawn.map((p, i) => {
        if (!p.label) return null;
        const below = p.level < nL - 1;
        const off = Math.round(W * 0.012);
        // AWAY from the route. The label used to be centred on the waypoint, so it sat directly on the
        // diagonal leaving it. The route departs (or arrives) horizontally in a known direction; put the
        // label on the other side and it can never cross the line whatever the waypoints are.
        // the FINAL waypoint is reached exactly when walked === total, so a "distance travelled past it"
        // fade is 0 forever and the end label never appeared. It arrives with the settle instead.
        const arrive = i === drawn.length - 1
          ? settled : clamp01((walked - cum[i]) / Math.max(1e-6, total * 0.05));
        const nb = i < drawn.length - 1 ? drawn[i + 1] : drawn[i - 1];
        const goesRight = (nb.x - p.x) >= 0;
        const boxW = W * 0.16, gap = Math.round(W * 0.010);
        return (
          <div key={'lb' + i} style={{position: 'absolute',
            left: goesRight ? p.x - boxW - gap : p.x + gap, width: boxW,
            // above-the-line labels clear the level's own leader label, which sits just above its rule
            top: below ? p.y + off : p.y - off * 2 - Math.round(W * 0.016),
            textAlign: goesRight ? 'right' : 'left',
            opacity: arrive,
            font: `500 ${Math.round(W * 0.0115)}px/1.3 ${mono}`, letterSpacing: '0.06em',
            color: DIM}}>{p.label}</div>
        );
      })}

      {/* the verdict — what this route cost, or what the shortcut removed.
          Both foot blocks are laid out against the SAME numbers the reserve above was computed from
          (`FOOT_GAP`, `VERDICT_PX`, `NOTE_PX`, `noteOff`), so the arithmetic and the layout cannot
          drift apart — which is how the note came to sit inside the caption band in the first place. */}
      {verdict ? (
        <div style={{position: 'absolute', left: x0, top: bottom + FOOT_GAP, width: footW,
          opacity: settled, transform: `translateY(${(1 - settled) * 10}px)`,
          font: `700 ${VERDICT_PX}px/1.25 ${disp}`, color: FG}}>{verdict}</div>
      ) : null}
      {note ? (
        <div style={{position: 'absolute', left: x0, top: bottom + FOOT_GAP + noteOff, width: footW,
          opacity: settled * 0.9,
          font: `400 ${NOTE_PX}px/1.4 var(--f-body, system-ui, sans-serif)`,
          color: DIM}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default SectionRoute;
