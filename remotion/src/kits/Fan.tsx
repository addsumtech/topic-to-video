// HELPER · Fan — the film's one picture of a STEP, drawn as the probability popover a model's readout opens under the
// caret: every candidate for the next slot hangs from the slot on a branch as thick as its chance (the rest of the
// vocabulary a spray of hairlines behind them). One is picked — by taking the top, or by a roll whose light hops
// across the options and lands — and a copy of it rises into the text at the caret while the list stays below as the
// record, the chosen one ringed and the others faded back. Every token, chance and label arrives from the caller.
import React from 'react';
import {clamp01, easeInOutCubic, easeOutCubic, hash01, lerp} from '../runtime/motion';
import {mix} from '../runtime/dna';
import {Tile, tileW, tileH, tintAt, branchW, Spray, MONO, Ink} from './Kit';

export type Cand = {token: string; p: number; label?: string; end?: boolean};

/** The rows of the list: under the slot, most likely first. */
export const listYs = (n: number, top: number, pitch: number) => Array.from({length: n}, (_, k) => top + k * pitch);

/** A branch from the slot (above-left) down to an option's left edge: leaves straight down, arrives level. */
export const dropD = (ox: number, oy: number, x2: number, y2: number) =>
  `M${ox},${oy} C${ox},${oy + (y2 - oy) * 0.75} ${ox + (x2 - ox) * 0.35},${y2} ${x2},${y2}`;

/** Which option the roll's light is on at roll-progress r: hops that slow down and land on `pick`. The hops before
 *  the landing visit options in proportion to their chance — what a weighted roll looks like while it runs. */
export const rollAt = (cands: Cand[], pick: number, r: number, hops = 11, seed = 7): number => {
  if (r >= 1) return pick;
  const j = Math.min(hops - 1, Math.floor((1 - Math.pow(1 - clamp01(r), 0.5)) * hops));
  if (j === hops - 1) return pick;
  const tot = cands.reduce((s, c) => s + Math.max(1.5, c.p), 0);
  // @decor: the hops before the landing are the look of a roll; the landing itself is the film's prop `pick`
  let u = hash01(seed + j * 13) * tot;
  for (let k = 0; k < cands.length; k++) {
    u -= Math.max(1.5, cands[k].p);
    if (u <= 0) return k;
  }
  return cands.length - 1;
};

export const Fan: React.FC<{
  cands: Cand[];
  ox: number; oy: number;          // the slot the branches hang from (just under the caret)
  x2: number; top: number; pitch: number;   // the list column and its first row's centre
  px: number; grow: number; pick: number | null; pickOn: number; travel: number; to: {x: number; y: number};
  wither: number; roll?: number | null; labelPx: number; ink: Ink; U: number; lw: number; tint0?: number;
  keep?: number;                    // how present the options nobody wrote stay, once faded back
  toPx?: number;                    // the type size of the text the pick rises into (it grows to it on the way)
  spray?: {len: number; n: number; t: number; durF: number; fps: number; seed?: number};
}> = ({cands, ox, oy, x2, top, pitch, px, grow, pick, pickOn, travel, to, wither, roll = null, labelPx, ink, U, lw,
  tint0 = 0, keep = 0.5, toPx, spray}) => {
  const ys = listYs(cands.length, top, pitch);
  const lit = roll !== null && roll !== undefined && pick !== null && roll > 0 && pickOn <= 0
    ? rollAt(cands, pick, roll) : null;
  const tr = easeInOutCubic(clamp01(travel));
  const g = easeOutCubic(clamp01(grow));
  const fill = tintAt(tint0);
  const fadeTo = (on: number) => 1 - (1 - keep) * on;
  return (
    <>
      <svg width="100%" height="100%" style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        {spray ? <Spray x={ox} y={oy} len={spray.len} n={spray.n} spread={1.05} dir={0.72} ink={ink.dim} lw={lw}
          grow={g} t={spray.t} durF={spray.durF} fps={spray.fps} seed={spray.seed ?? 3} opacity={fadeTo(wither)} /> : null}
        {cands.map((cd, k) => {
          const chosen = pick === k;
          const on = chosen ? pickOn : 0;
          const col = on > 0 ? mix(mix(ink.fg, ink.bg, 0.2), ink.acc, on) : mix(ink.fg, ink.bg, lit === k ? 0.0 : 0.22);
          const op = g * (chosen ? 1 : fadeTo(wither));
          return <path key={k} d={dropD(ox, oy, x2, ys[k])} fill="none" stroke={col} strokeWidth={branchW(cd.p, U, lw)}
            strokeLinecap="round" opacity={op} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - g} />;
        })}
      </svg>
      {cands.map((cd, k) => {
        const chosen = pick === k;
        const a = clamp01(g * 1.6 - 0.45 - k * 0.07);
        const ring = lit === k ? ink.acc : chosen && pickOn > 0 ? mix(ink.bg, ink.acc, pickOn) : undefined;
        // each option comes OUT of the slot being scored and travels down its branch to its row
        const e = easeOutCubic(clamp01(clamp01(grow) * 1.35 - k * 0.07));
        const x = lerp(ox, x2, e), y = lerp(oy, ys[k], e);
        return <Tile key={k} text={cd.token} x={x} y={y} px={px} fill={cd.end ? ink.fg : fill} moving={(e > 0 && e < 1) || (a > 0 && a < 1)}
          ink={cd.end ? ink.bg : ink.fg} opacity={a * (chosen ? 1 : fadeTo(wither))} scale={0.9 + 0.1 * a} ring={ring} />;
      })}
      {/* the picked piece, rising out of the list into the text */}
      {pick !== null && travel > 0 ? (
        <Tile text={cands[pick].token} x={lerp(x2, to.x, tr)} y={lerp(ys[pick], to.y, tr)} px={lerp(px, toPx ?? px, tr)}
          fill={cands[pick].end ? ink.fg : fill} ink={cands[pick].end ? ink.bg : ink.fg} moving={travel < 1} />
      ) : null}
      {cands.map((cd, k) => {
        if (!cd.label) return null;
        const chosen = pick === k;
        const a = clamp01(g * 1.6 - 0.65 - k * 0.07);
        return <div key={k} style={{position: 'absolute', left: x2 + tileW(cd.token, px) + px * 0.45,
          top: ys[k] - labelPx * 0.62, opacity: a * (chosen ? 1 : fadeTo(wither)), whiteSpace: 'nowrap',
          color: (chosen && pickOn > 0) || lit === k ? ink.acc : ink.dim,
          font: `${chosen ? 600 : 500} ${labelPx}px/1.2 ${MONO}`}}>{cd.label}</div>;
      })}
      <div style={{position: 'absolute', left: x2, top: top - tileH(px) / 2, width: 0, height: 0}} />
    </>
  );
};
