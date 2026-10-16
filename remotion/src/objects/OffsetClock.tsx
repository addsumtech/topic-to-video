// OBJECT · OffsetClock — a clock read against a reference: the reference hand, the clock's own hand, and the
// offset between them drawn as signed, named wedges.
//
// WHAT IT ENCODES. GPS turns every clock error into a distance, so the film's recurring question is never "what
// time is it" but "how far has THIS clock run from THAT one". The dial answers it the way a clock comparison
// does: a thin reference hand (true time, or the ground's clock) and the clock's own hand, and between them the
// offset as a wedge. Several causes stack: each wedge is laid from where the last one ended, on its own band
// (outer first), signed — a positive one sweeps clockwise, a negative one sweeps back — so "+ a big one, − a small
// one" reads as arithmetic, and the own hand lands where the sum says. The hand is PLACED by the sum
// (against + Σ wedges); it is never given separately, so the picture cannot disagree with its own parts. A wedge of
// unknown size (`tone: 'unknown'`) is drawn hatched and outlined dashed: an offset that exists and is not known.
//
// Colour is semantic for this film: 'satellite' paints in the DNA accent (the satellites' gold), 'ground' in
// accent2 (the limb's blue — the Earth, the phone and the ground's clocks), 'neutral' in the ink. It draws no
// numerals — a clock face's twelve hours are not this film's claim — and every word is a prop. It sizes to its box.
// Reveal: face and ticks draw on, the reference hand lands, then the wedges sweep in order. Idle: a small
// bead steps round the rim once a second — the clock keeps running; nothing that carries a figure moves.
import React from 'react';
import type {ObjectProps, ObjectMeta} from '../runtime/objectSlot';
import {clamp01, seg, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {drawOn} from '../runtime/draw';
import {mix} from '../runtime/dna';
import {fitsBox} from '../runtime/layout';

export const META: ObjectMeta = {aspect: 1, provenance: 'scientific'};

type Tone = 'satellite' | 'ground' | 'neutral';
type Wedge = {turns: number; tone: Tone | 'unknown'; label?: string};

const FG_D0 = '#e8eef8', DIM_D0 = '#8a96ad', ACC_D0 = '#f2c46b', ACC2_D0 = '#5db6ff', SURF_D0 = '#0a1020', BG_D0 = '#04060c';

export const OffsetClock: React.FC<ObjectProps & {
  tone?: Tone;          // the clock's own hand and rim
  reading?: number;     // where its own hand points, in turns from twelve o'clock — used only with no `against`
  against?: number | null;  // the reference hand, in turns from twelve o'clock; null = no reference drawn
  againstTone?: Tone;   // the reference hand's colour
  wedges?: Wedge[];     // the offset's parts, stacked from the reference, in turns (signed); the hand lands at their sum
  sweep?: boolean;      // a bead that keeps stepping round the rim on the idle clock (the clock is running)
  run?: number;         // turns per second both hands turn together on the idle clock — the clocks keep time; the offset between them holds
}> = ({w, h, t, dna, idle = 0, tone = 'satellite', reading = 0, against = null, againstTone = 'neutral', wedges = [],
  sweep = true, run = 0}) => {
  if (!Array.isArray(wedges)) throw new Error(`OffsetClock: \`wedges\` is a list — got ${JSON.stringify(wedges)}`);
  if (wedges.length && (against === null || against === undefined)) {
    throw new Error('OffsetClock: wedges are laid from the reference hand — give `against` (turns from twelve o\'clock)');
  }
  if (wedges.length > 4) throw new Error(`OffsetClock: at most 4 wedges (one band each) — got ${wedges.length}`);
  wedges.forEach((wd, i) => {
    if (!(wd && Number.isFinite(wd.turns) && Math.abs(wd.turns) > 0 && Math.abs(wd.turns) < 1)) {
      throw new Error(`OffsetClock: wedges[${i}].turns is a signed fraction of a turn, 0 < |turns| < 1 — got ${JSON.stringify(wd)}`);
    }
    if (!['satellite', 'ground', 'neutral', 'unknown'].includes(wd.tone)) {
      throw new Error(`OffsetClock: wedges[${i}].tone is satellite | ground | neutral | unknown — got ${JSON.stringify(wd.tone)}`);
    }
  });
  if (!(Number.isFinite(run) && run >= 0 && run <= 0.1)) throw new Error(`OffsetClock: \`run\` is 0-0.1 turns per second — got ${JSON.stringify(run)}`);
  if (run > 0 && wedges.some((wd) => wd.label)) {
    throw new Error('OffsetClock: a running clock cannot carry its own wedge labels — they would travel with the wedges; let the host name them');
  }
  for (const [k, v] of [['reading', reading], ['against', against ?? 0]] as const) {
    if (!Number.isFinite(v)) throw new Error(`OffsetClock: \`${k}\` must be a finite number of turns — got ${JSON.stringify(v)}`);
  }
  const uid = React.useId().replace(/[^A-Za-z0-9]/g, '');
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0, BG = dna?.bg ?? BG_D0;
  const ACC = dna?.accent ?? ACC_D0, ACC2 = dna?.accent2 ?? ACC2_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const ink = (tn: Tone | 'unknown') => (tn === 'satellite' ? ACC : tn === 'ground' ? ACC2 : FG);
  const own = ink(tone);
  const body = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';

  const S = Math.min(w, h);
    const R = S * 0.36;                            // one size whether or not it is labelled, so two dials compare fairly
  const cx = w / 2, cy = h / 2;
  const lw = Math.max(1, S * 0.004);
  const at = (turns: number, r: number) => ({x: cx + r * Math.sin(turns * 2 * Math.PI), y: cy - r * Math.cos(turns * 2 * Math.PI)});

  // ── the reveal ──
  const faceOn = easeOutCubic(clamp01(seg(t, 0, 0.32)));
  const refOn = easeOutCubic(clamp01(seg(t, 0.22, 0.4)));
  const n = wedges.length;
  const wWin = (i: number): [number, number] => {
    const a = 0.4 + (i * 0.5) / Math.max(1, n), b = 0.4 + ((i + 1) * 0.5) / Math.max(1, n);
    return [a, b - 0.04];
  };
  const grow = wedges.map((_, i) => easeInOutCubic(clamp01(seg(t, ...wWin(i)))));
  const spin = run * idle;                       // the clocks keep running: both hands, and every wedge, turn together
  const base = (against ?? reading) + spin;
  let hand = against === null || against === undefined ? reading + spin : base;
  const starts: number[] = [];
  let acc = base;
  wedges.forEach((wd, i) => {
    starts.push(acc);
    acc += wd.turns;
    hand += wd.turns * grow[i];
  });
  const handOn = against === null || against === undefined ? faceOn : refOn;

  // ── the face ──
  const ticks: React.ReactNode[] = [];
  for (let k = 0; k < 60; k++) {
    // @positional: every fifth minute mark is an hour mark — the form of a clock face, not a reading about anything
    const major = k % 5 === 0;
    const p0 = at(k / 60, R * (major ? 0.86 : 0.91)), p1 = at(k / 60, R * 0.97);
    ticks.push(<line key={k} x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y} stroke={major ? FG : DIM}
      strokeWidth={lw * (major ? 1.6 : 0.8)} opacity={(major ? 0.9 : 0.6) * clamp01(faceOn * 1.4 - (k / 60) * 0.4)} />);
  }

  // ── a wedge: an annular sector on its own band, from `a` turns to `b` turns ──
  // one wedge is the whole slice between the two hands; several stack on bands, outermost first
  const band = (i: number): [number, number] => (n === 1 ? [R * 0.14, R * 0.82]
    : [R * (0.8 - i * 0.13), R * (0.8 - i * 0.13 + 0.11)]);
  const sector = (a: number, b: number, r0: number, r1: number) => {
    const lo = Math.min(a, b), hi = Math.max(a, b);
    if (hi - lo < 1e-5) return '';
    const large = hi - lo > 0.5 ? 1 : 0;
    const p0 = at(lo, r1), p1 = at(hi, r1), p2 = at(hi, r0), p3 = at(lo, r0);
    return `M${p0.x} ${p0.y} A${r1} ${r1} 0 ${large} 1 ${p1.x} ${p1.y} L${p2.x} ${p2.y} A${r0} ${r0} 0 ${large} 0 ${p3.x} ${p3.y} Z`;
  };
  const labPx = Math.round(S * 0.075);

  // ── the running bead, stepping once a second on the idle clock ──
  const step = Math.floor(idle);
  const frac = idle - step;
  const sec = sweep ? (step + easeOutCubic(clamp01(frac / 0.18))) / 60 : 0;
  const secOn = sweep ? clamp01(idle * 2) : 0;

  return (
    <div style={{position: 'relative', width: w, height: h}}>
      <svg width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs>
          <radialGradient id={`${uid}face`} cx={cx - R * 0.3} cy={cy - R * 0.35} r={R * 1.3} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={mix(SURF, FG, 0.07)} />
            <stop offset="1" stopColor={mix(SURF, BG, 0.4)} />
          </radialGradient>
          <pattern id={`${uid}hatch`} width={S * 0.018} height={S * 0.018} patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)">
            <line x1={0} y1={0} x2={0} y2={S * 0.018} stroke={FG} strokeWidth={lw * 1.1} opacity={0.75} />
          </pattern>
        </defs>
        <circle cx={cx} cy={cy} r={R} fill={`url(#${uid}face)`} opacity={faceOn} />
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={own} strokeWidth={lw * 2.4} {...drawOn(faceOn)} />
        <circle cx={cx} cy={cy} r={R * 1.035} fill="none" stroke={own} strokeWidth={lw * 0.7} opacity={0.45 * faceOn} />
        {ticks}
        {/* the wedges, each on its own band, laid from where the last one ended */}
        {wedges.map((wd, i) => {
          const [r0, r1] = band(i);
          const a = starts[i], b = starts[i] + wd.turns * grow[i];
          const d = sector(a, b, r0, r1);
          if (!d) return null;
          const unknown = wd.tone === 'unknown';
          const tint = unknown ? FG : ink(wd.tone);
          return (
            <g key={i}>
              <path d={d} fill={unknown ? `url(#${uid}hatch)` : tint} opacity={unknown ? 0.9 : 0.42} />
              <path d={d} fill="none" stroke={tint} strokeWidth={lw * 1.4}
                strokeDasharray={unknown ? `${lw * 4} ${lw * 3}` : undefined} opacity={0.95} />
            </g>
          );
        })}
        {/* the net offset: a faint slice from the reference to the hand, under the hands */}
        {wedges.length > 1 ? (
          <path d={sector(base, hand, R * 0.1, R * 0.8 - (wedges.length - 1) * 0.13 * R - R * 0.02)} fill={FG}
            opacity={0.1 * grow[grow.length - 1]} />
        ) : null}
        {/* the reference hand: thin, the time the clock is read against */}
        {against !== null && against !== undefined ? (() => {
          const tip = at(base, R * 0.95), tail = at(base + 0.5, R * 0.12);
          return <line x1={tail.x} y1={tail.y} x2={tip.x} y2={tip.y} stroke={ink(againstTone)} strokeWidth={lw * 1.3}
            strokeDasharray={`${lw * 5} ${lw * 3}`} opacity={0.9 * refOn} strokeLinecap="round" />;
        })() : null}
        {/* the clock's own hand */}
        {(() => {
          const tip = at(hand, R * 0.84), tail = at(hand + 0.5, R * 0.16);
          return <line x1={tail.x} y1={tail.y} x2={tip.x} y2={tip.y} stroke={own} strokeWidth={lw * 4.2}
            strokeLinecap="round" opacity={handOn} />;
        })()}
        {/* the clock is running: a bead steps round the rim once a second — not a hand, so it cannot be read as one */}
        {secOn > 0 ? (() => {
          const p = at(sec, R * 1.0);
          return <circle cx={p.x} cy={p.y} r={lw * 3.2} fill={mix(own, '#ffffff', 0.4)} opacity={0.9 * secOn} />;
        })() : null}
        <circle cx={cx} cy={cy} r={lw * 5} fill={own} opacity={faceOn} />
        <circle cx={cx} cy={cy} r={lw * 2} fill={BG} opacity={faceOn} />
      </svg>
      {/* each wedge's name, outside the dial at the wedge's middle, once it has swept in */}
      {wedges.map((wd, i) => {
        if (!wd.label) return null;
        const mid = starts[i] + wd.turns / 2;
        const p = at(mid, R * 1.16);
        const right = Math.sin(mid * 2 * Math.PI) >= -0.15;
        const boxW = Math.min(w * 0.5, Math.max(R * 0.9, (right ? w - p.x : p.x) - S * 0.01));
        if (!fitsBox(wd.label, labPx, boxW, labPx * 2.8)) return null;
        const tint = wd.tone === 'unknown' ? FG : ink(wd.tone);
        const on = clamp01(grow[i] * 1.6 - 0.6);
        return (
          <div key={i} style={{position: 'absolute', top: p.y - labPx * 0.65,
            ...(right ? {left: p.x} : {left: p.x - boxW, textAlign: 'right' as const}), width: boxW,
            color: tint, font: `600 ${labPx}px/1.25 ${body}`, opacity: on}}>{wd.label}</div>
        );
      })}
    </div>
  );
};
