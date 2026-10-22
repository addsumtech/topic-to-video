// SHOT · WeightedWheel — the pick as a weighted roll. The options for one slot become the slices of a wheel, each as
// wide as its chance, with one grey slice for every other token; a blue pointer stands at the top.
//   `roll`        the wheel is spun again and again; each spin lands where it lands — usually on the big slice, not
//                 always — and the landed piece is written after the text so far, one line per roll, so the real
//                 outcomes stack up beside the wheel.
//   `temperature` the same slot's slices reshape as the temperature setting steps along its scale: a low setting
//                 swells the top slice toward the whole wheel, a high one flattens the field and fattens the grey; the
//                 names on the wheel never change. The setting keeps stepping, so the reshaping keeps happening.
//   `menu`        the same reshaping held as a statement on a full-bleed accent ground: more variety, never a new
//                 token on the wheel.
//
// THE ARGUMENT SHAPE: unequal odds, one outcome per roll; odds reshaped, menu unchanged. Hide the caption and the
// frame still says "a loaded wheel decides the next piece" (or "the dial bends the odds of the same pieces"). Every
// slice, chance, roll outcome and word arrives as a prop; a slice's share is its own number, never invented.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, lerp, radians, ReducedMotionContext} from '../runtime/motion';
import {fitTextPx} from '../runtime/layout';
import {useGlide} from '../runtime/glide';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {rows} from '../runtime/rows';
import {inkOf, frameOf, groundOf, flow, tileW, tileH, tintAt, Tile, TileRow, Caret, Title, Source, MONO, BODY,
  DISPLAY, TitleAt} from '../kits/Kit';

export const DURATION = 180;

type Slice = {token: string; p: number};
type Step = {temp: string; slices: Slice[]; label?: string};

const TAU = Math.PI * 2;
const arc = (cx: number, cy: number, r: number, a0: number, a1: number) => {
  // a pie slice from angle a0 to a1 (radians, 0 = up, clockwise)
  if (a1 - a0 >= TAU - 1e-4) return `M${cx},${cy - r} A${r},${r} 0 1 1 ${cx - 0.01},${cy - r} Z`;
  const p0 = {x: cx + r * Math.sin(a0), y: cy - r * Math.cos(a0)};
  const p1 = {x: cx + r * Math.sin(a1), y: cy - r * Math.cos(a1)};
  return `M${cx},${cy} L${p0.x},${p0.y} A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${p1.x},${p1.y} Z`;
};

export const WeightedWheel: React.FC<{
  mode?: 'roll' | 'temperature' | 'menu';
  question?: string;       // the question the slot answers
  context?: string[];      // the text so far (roll mode writes each landed piece after it)
  slices?: Slice[];        // roll mode: the options and their chances (the grey slice is whatever they leave)
  rolls?: number[];        // roll mode: which slice each real roll landed on, in order
  rest?: string;           // the grey slice's name
  steps?: Step[];          // temperature/menu: the same slot at each setting
  dial?: string;           // the setting's name, e.g. "temperature"
  note?: string;           // a line set under the wheel
  bleed?: boolean;         // menu: the flood reaches every edge (set by OddsStatement, whose GROUND is the accent)
  title?: string; kicker?: string; titleAt?: TitleAt;
  source?: string; sourceAt?: 'bl' | 'br' | 'tl' | 'tr';
}> = ({mode = 'roll', question = '', context: ctxIn, slices: slIn, rolls: rollsIn, rest = '', steps: stIn, dial = '',
  note = '', bleed = false, title = '', kicker = '', titleAt: titleAtIn, source = '', sourceAt: sourceAtIn}) => {
  // a title or kicker that was given is drawn: unplaced, it takes the top left (an unset spot used to draw nothing)
  const titleAt: TitleAt = titleAtIn ?? (title || kicker ? 'tl' : 'none');
  const sourceAt = sourceAtIn ?? 'br';
  const context = rows<string>(ctxIn ?? [], 'context', 'WeightedWheel');
  const slices0 = rows<Slice>(slIn ?? [], 'slices', 'WeightedWheel');
  const rolls = rows<number>(rollsIn ?? [], 'rolls', 'WeightedWheel');
  const steps = rows<Step>(stIn ?? [], 'steps', 'WeightedWheel');
  rolls.forEach((r, i) => {
    if (!(r >= 0 && r < slices0.length)) throw new Error(`WeightedWheel: rolls.${i} = ${r} is not one of ${slices0.length} slices`);
  });
  if (rolls.length > 6) throw new Error(`WeightedWheel: at most 6 rolls fit beside the wheel — got ${rolls.length}`);
  steps.forEach((s, i) => rows<Slice>(s.slices ?? [], `steps.${i}.slices`, 'WeightedWheel'));
  const dna = useDNA();
  const ink = inkOf(dna);
  const t = useT();
  const cue = useCues();
  const reduced = React.useContext(ReducedMotionContext);
  const glide = useGlide();
  const {width: W, height: H, fps, durationInFrames: durF} = useVideoConfig();
  const f = frameOf(W, H);
  const {U, sx, lw} = f;
  const menu = mode === 'menu';
  const temp = mode === 'temperature' || menu;
  // `menu` floods the frame with the accent. `bleed` takes the flood edge to edge, caption band included — only for
  // a shot whose declared GROUND is the accent (OddsStatement), so the burned caption picks its ink for the flood;
  // without it the caption band stays on the page, because this shot's GROUND says 'bg'.
  const flood = menu ? ink.acc : null;
  const onFlood = menu ? ink.on : ink.fg;
  const dimFlood = menu ? mix(ink.on, ink.acc, 0.28) : ink.dim;
  const floodC = flood ?? ink.acc;

  const kOn = easeOutCubic(clamp01(seg(t, ...cue.win('kicker', 0.03, 0.14, REACH_CUBIC))));
  const tOn = easeOutCubic(clamp01(seg(t, ...cue.win('title', 0.05, 0.17, REACH_CUBIC))));
  const wOn = easeOutCubic(clamp01(seg(t, 0.1, 0.26)));
  const sOn = easeOutCubic(clamp01(seg(t, 0.3, 0.42)));
  const secs = (t * durF) / fps;

  // ── which shares the wheel shows now ──
  let shares: Slice[] = slices0;
  let stepIx = 0, stepMix = 0;
  let dialAt: number | null = null;
  if (temp && steps.length) {
    // the setting steps along its scale and back, one hold-and-move per ~1.6 s, for as long as the beat runs
    const seq = steps.length > 1 ? [...steps.keys(), ...[...steps.keys()].reverse().slice(1, -1)] : [0];
    const per = 1.7, move = 0.55;
    const start = 0.2 * durF / fps;
    const k = reduced ? 0 : Math.max(0, secs - start);
    const idx = Math.floor(k / per);
    const within = k - idx * per;
    // @cycles: the setting walks its scale and back for as long as the beat lasts — a repeat of the same steps, in time
    const a = seq[idx % seq.length], b = seq[(idx + 1) % seq.length];
    const m = within > per - move ? easeInOutCubic((within - (per - move)) / move) : 0;
    stepIx = m > 0.5 ? b : a;
    stepMix = m;
    const A = rows<Slice>(steps[a].slices, `steps.${a}.slices`, 'WeightedWheel');
    const B = rows<Slice>(steps[b].slices, `steps.${b}.slices`, 'WeightedWheel');
    shares = A.map((s, i) => ({token: s.token, p: lerp(s.p, B[i]?.p ?? s.p, m)}));
    dialAt = lerp(parseFloat(steps[a].temp), parseFloat(steps[b].temp), m);
  }
  const used = shares.reduce((s, x) => s + Math.max(0, x.p), 0);
  if (used > 100.5) throw new Error(`WeightedWheel: the slices add up to ${used.toFixed(1)}% — more than the whole wheel`);
  const restP = Math.max(0, 100 - used);

  // ── geometry: the wheel on one side, the text (or the dial) on the other ──
  const row = titleAt[0];
  const titled = titleAt !== 'none' && !!(title || kicker);
  const zTop = f.zTop, zBot = titled && row === 'b' ? f.zBot - U * 0.2 : f.zBot - U * 0.07;
  const R = Math.min((zBot - zTop) * 0.45, W * 0.19);
  const cx = menu ? W * 0.72 : mode === 'roll' ? sx + R * 1.25 + W * 0.04 : W * 0.3;
  const cy = (zTop + zBot) / 2 + (menu ? 0 : U * 0.01);
  // slices start at the pointer and run clockwise; the wheel's rotation brings a landed slice under the pointer
  const bounds: {a0: number; a1: number}[] = [];
  let acc = 0;
  [...shares.map((s) => s.p), restP].forEach((p) => {
    const a0 = (acc / 100) * TAU;
    acc += p;
    bounds.push({a0, a1: (acc / 100) * TAU});
  });
  const mid = (i: number) => (bounds[i].a0 + bounds[i].a1) / 2;
  let rot = 0;
  let landed = -1;
  // roll mode: spin k runs over its own window, landing its slice's middle under the pointer
  const n = rolls.length;
  const rollWin = (k: number): [number, number] => {
    const a = 0.2 + (0.6 * k) / Math.max(1, n), b = a + (0.6 / Math.max(1, n)) * 0.76;
    return [a, b];
  };
  let shown = 0;
  if (mode === 'roll') {
    let prev = 0;
    for (let k = 0; k < n; k++) {
      const [a, b] = rollWin(k);
      // @decor: the extra turns a spin makes before it lands are the look of a roll; where it lands is the prop
      const target = -mid(rolls[k]) - TAU * (3 + (k % 2));
      const q = clamp01(seg(t, a, b));
      const p = 1 - (1 - q) * (1 - q);      // a spin decelerates to its landing
      if (t >= a) { rot = lerp(prev, target, p); }
      if (p >= 1) { shown = k + 1; landed = rolls[k]; }
      else if (t >= a) landed = -1;
      prev = target;   // the next spin starts from where this one stopped
    }
    if (t < rollWin(0)[0]) rot = 0;
  } else if (!reduced) {
    // at every setting the wheel is still a roll: it keeps turning; no landing is shown, so none is claimed
    rot = menu ? radians(t, durF, fps, 14, 0) : radians(t, durF, fps, 4.2, 0);
  }

  // the text and its rolls (roll mode): each roll's line is the context with the landed piece written after it
  const px = Math.round(U * 0.038);
  const th = tileH(px);
  const textX = cx + R * 1.35;
  const qPx = f.label;
  const linesTop = zTop + (question ? qPx * 2.6 : 0) + th * 0.6;
  const pitch = n ? Math.min(th * 1.35, (zBot - linesTop - th * 0.4) / Math.max(1, n)) : th;
  const ctxW = context.reduce((s, k) => s + tileW(k, px), 0);

  const labelPx = f.label;
  const sliceLabel = (i: number, name: string, r: number) => {
    const a = mid(i) + rot;
    const span = bounds[i].a1 - bounds[i].a0;
    const lp = Math.round(Math.min(U * 0.044, Math.max(labelPx, R * 0.15)));
    const chord = span * R * r;
    if (span < 0.42 || [...name].length * 0.6 * lp > R * 0.9 || chord < lp * 1.6) return null;
    const lx = cx + Math.sin(a) * R * r, ly = cy - Math.cos(a) * R * r;
    return <div key={`l${i}`} style={{position: 'absolute', left: 0, top: 0,
      transform: glide(`translate(${lx}px, ${ly}px) translate(-50%, -50%)`, true), background: ink.surface, borderRadius: lp * 0.25,
      padding: `${lp * 0.12}px ${lp * 0.3}px`, color: ink.fg, whiteSpace: 'pre', font: `600 ${lp}px/1 ${MONO}`,
      opacity: wOn}}>{name}</div>;
  };

  const step = temp && steps.length ? steps[stepIx] : null;
  const ground = flood && bleed ? flood
    : flood ? `linear-gradient(180deg, ${flood} 0%, ${flood} ${(zBot / H) * 100 - 6}%, ${ink.bg} ${(f.zBot / H) * 100 + 2}%)`
    : groundOf(dna, ink);
  return (
    <AbsoluteFill style={{background: ground}}>
      {menu ? (title ? <div style={{position: 'absolute', left: sx, top: zTop + U * 0.02, width: W * 0.46, color: onFlood,
        opacity: tOn, font: `600 ${fitTextPx(title, W * 0.46 * 2.6, Math.round(U * 0.1), {adv: 0.5, usable: 1})}px/1.08 ${DISPLAY}`}}>{title}</div> : null)
        : <Title title={title} kicker={kicker} at={titleAt} W={W} H={H} on={tOn} kOn={kOn} ink={onFlood} dim={dimFlood}
          maxW={row === 'm' ? W * 0.3 : W * 0.56} lines={2} />}
      {question && !menu ? <div style={{position: 'absolute', left: mode === 'roll' ? textX : sx, top: zTop,
        opacity: wOn, color: ink.fg, padding: `${qPx * 0.3}px ${qPx * 0.6}px`, background: ink.surface,
        border: `1px solid ${ink.border}`, borderRadius: qPx * 0.7, font: `400 ${qPx}px/1.2 ${BODY}`,
        whiteSpace: 'nowrap'}}>{question}</div> : null}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`rotate(${(rot * 180) / Math.PI} ${cx} ${cy})`} opacity={wOn}>
          {[...shares, {token: rest, p: restP}].map((s, i) => {
            const isRest = i === shares.length;
            if (!(bounds[i].a1 - bounds[i].a0 > 1e-4)) return null;
            const fill = isRest ? mix(menu ? onFlood : ink.dim, menu ? floodC : ink.bg, 0.72) : tintAt(i);
            const lit = landed === i && !isRest;
            return <path key={i} d={arc(cx, cy, lit ? R * 1.04 : R, bounds[i].a0, bounds[i].a1)} fill={fill}
              stroke={menu ? floodC : mix(ink.fg, ink.bg, 0.55)} strokeWidth={Math.max(3, U * 0.0035)} />;
          })}
          <circle cx={cx} cy={cy} r={R * 0.08} fill={menu ? floodC : ink.surface} stroke={menu ? onFlood : ink.border}
            strokeWidth={2} />
        </g>
        {/* the pointer */}
        <path d={`M${cx - R * 0.09},${cy - R - R * 0.2} L${cx + R * 0.09},${cy - R - R * 0.2} L${cx},${cy - R + R * 0.06} Z`}
          fill={menu ? onFlood : ink.acc2} opacity={wOn} />
      </svg>
      {[...shares.map((s) => s.token), rest].map((name, i) => (name ? sliceLabel(i, name, 0.64) : null))}

      {/* roll mode: the text so far, and each roll's outcome written after it */}
      {mode === 'roll' ? (
        <>
          {rolls.map((r, k) => {
            const y = linesTop + k * pitch;
            const [a, b] = rollWin(k);
            const lineOn = easeOutCubic(clamp01(seg(t, a - 0.02, a + 0.04)));
            const add = easeOutCubic(clamp01(seg(t, b, b + 0.05)));
            const fl = flow(context, px, textX, y, W, th);
            return (
              <React.Fragment key={k}>
                <TileRow tokens={context} pos={fl.pos} px={px} on={lineOn} ink={ink.fg} opacity={k === shown - 1 || (k === shown && t >= a) ? 1 : 0.55} />
                {add > 0 ? <Tile text={slices0[r].token} x={textX + ctxW} y={y} px={px} fill={tintAt(r)} ink={ink.fg}
                  opacity={add} scale={0.9 + 0.1 * add} moving={add > 0 && add < 1} ring={k === shown - 1 ? ink.acc : undefined} /> : null}
                {add <= 0 && lineOn > 0 ? <Caret x={textX + ctxW + px * 0.12} y={y} h={th * 0.9} color={ink.acc2} on={lineOn} U={U} /> : null}
              </React.Fragment>
            );
          })}
        </>
      ) : null}

      {/* temperature / menu: the setting's scale, and the top slice's printed chance at this setting */}
      {temp && step ? (() => {
        const sx0 = menu ? sx : W * 0.55, sx1 = menu ? W * 0.5 : W - sx;
        const sy = menu ? zBot - U * 0.08 : cy - U * 0.05;
        const temps = steps.map((s) => parseFloat(s.temp));
        const lo = Math.min(0, ...temps), hi = Math.max(2, ...temps);
        const xOf = (v: number) => lerp(sx0, sx1, (v - lo) / (hi - lo));
        const knob = xOf(dialAt ?? temps[0]);
        const big = Math.round(U * 0.075);
        return (
          <>
            <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
              <line x1={sx0} x2={sx1} y1={sy} y2={sy} stroke={menu ? mix(onFlood, floodC, 0.5) : ink.border}
                strokeWidth={Math.max(3, U * 0.004)} strokeLinecap="round" opacity={wOn} />
              {steps.map((s, i) => <line key={i} x1={xOf(temps[i])} x2={xOf(temps[i])} y1={sy - U * 0.016} y2={sy + U * 0.016}
                stroke={menu ? onFlood : ink.dim} strokeWidth={2} opacity={wOn} />)}
              <circle cx={knob} cy={sy} r={U * 0.019} fill={menu ? onFlood : ink.acc2} opacity={wOn} />
            </svg>
            {steps.map((s, i) => <div key={i} style={{position: 'absolute', left: xOf(temps[i]), top: sy + U * 0.03,
              transform: 'translateX(-50%)', color: i === stepIx ? onFlood : dimFlood, opacity: wOn,
              font: `${i === stepIx ? 600 : 500} ${labelPx}px/1.2 ${MONO}`}}>{s.temp}</div>)}
            {dial ? <div style={{position: 'absolute', left: sx0, top: sy - U * 0.075, color: dimFlood, opacity: wOn,
              font: `500 ${labelPx}px/1.2 ${BODY}`}}>{dial}</div> : null}
            {!menu && step.label ? <div style={{position: 'absolute', left: sx0, top: sy + U * 0.1, opacity: wOn * (1 - 0.6 * Math.sin(stepMix * Math.PI)),
              color: ink.fg, font: `600 ${big}px/1.1 ${DISPLAY}`, whiteSpace: 'nowrap'}}>{step.label}</div> : null}
          </>
        );
      })() : null}
      {note ? <div style={{position: 'absolute', left: menu ? sx : cx - R, top: menu ? zBot - U * 0.23 : cy + R + U * 0.04,
        width: menu ? W * 0.44 : R * 2, textAlign: menu ? 'left' : 'center', opacity: sOn, color: dimFlood,
        font: `500 ${labelPx}px/1.25 ${BODY}`}}>{note}</div> : null}
      <Source text={source} at={sourceAt} W={W} H={H} on={sOn} ink={menu ? dimFlood : ink.dim} />
    </AbsoluteFill>
  );
};
