// SHOT · RestsOn — the phenomenon on top, and what holds it up underneath.
//
// WHY THIS EXISTS. Of the three shapes an explainer film is built from, MECHANISM was the last with no dense
// register: the five that answer "why does this happen" measure a median of 2.4% ink. The reason is
// structural, not laziness — a mechanism is a RELATION, relations are conventionally drawn as boxes and
// arrows, and a line has no area. Measured across this library, text and hairlines barely ink a frame at all.
//
// So the relation has to become a REGION. Here the causal link is LOAD: the phenomenon spans only as wide as
// the reason directly beneath it, each deeper reason is broader still, and the whole thing assembles from the
// BOTTOM UP — which is both the explanatory order (you cannot rest something on a reason you have not given)
// and where the shot's motion comes from. Take a lower block away and everything above it has nothing to
// stand on; that is the claim, and it is the picture.
//
// WHAT MAKES IT NOT `InOrder` WITH A ROTATION. InOrder's axis is TIME and its bands are equal citizens in a
// sequence; this one's axis is DEPTH OF EXPLANATION and its bands are not equal — width is how foundational a
// reason is, and the order is never a chronology. A film that swapped one for the other would be making a
// different claim.
//
// THE HIDE-THE-CAPTION TEST: cover the subtitle and the frame still says "this rests on three reasons, and
// the broad one at the bottom is the deepest".
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, dnaPalette, separated, surfaceOn, readableOn, dimOn, TONE_MIN_STEP} from '../runtime/dna';

export const DURATION = 175; // ~5.8s

const BG_D0 = '#07090f', FG_D0 = '#eef2f8', DIM_D0 = '#6c7788', ACC_D0 = '#4f8cff';

type Cause = {label?: string; note?: string};

const DEFAULT_CAUSES: Cause[] = [
  {label: 'the immediate reason', note: 'what you notice first'},
  {label: 'the one underneath it', note: 'why that is true'},
  {label: 'the root', note: 'where it actually comes from'},
];

export const RestsOn: React.FC<{
  kicker?: string;     // what this frame is about
  effect?: string;     // the phenomenon being explained — it sits on top
  effectNote?: string; // one line with it
  causes?: Cause[];    // immediate first, root LAST — the order is the depth of the explanation
  because?: string;    // the word on the joint between two levels (a language choice, so it is a prop)
}> = ({kicker = '', effect = '', effectNote = '', causes: CAUSES = DEFAULT_CAUSES, because = ''} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? BG_D0;
  const FG = dna?.fg ?? FG_D0;
  const DIM = dna?.dim ?? DIM_D0;
  const mono = dna?.fontMono ?? 'ui-monospace, monospace';
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const disp = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';

  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const base = Math.min(W, H);
  const zoneTop = CONTENT_TOP;
  const zoneBottom = H - captionBand(W, H);
  const zoneH = Math.max(1, zoneBottom - zoneTop);

  const causes = CAUSES.slice(0, 5);
  const n = causes.length;
  const levels = n + 1;                                   // the effect, then each cause below it

  // The effect takes a little more height than a cause — it is what the frame is ABOUT — and the rest split
  // the remainder evenly. The blocks tile the zone exactly, so the density is the claim rather than an
  // addition to it.
  const effShare = n === 0 ? 1 : 0.30;
  const causeShare = n === 0 ? 0 : (1 - effShare) / n;

  // WIDTH IS HOW FOUNDATIONAL A REASON IS. The effect is narrowest; each level below is wider, so the stack
  // reads as something standing on a base rather than as a list that happens to be vertical.
  const widthAt = (i: number) => 0.52 + (0.46 * i) / Math.max(1, levels - 1);   // 0 = effect … n = the root

  const pal = (dna ? dnaPalette(dna, Math.max(3, levels)) : null) ?? [ACC_D0];
  const effFill = dna ? surfaceOn(BG, pal[0], TONE_MIN_STEP * 1.5) : ACC_D0;
  const causeFill = (i: number) => {
    if (!dna) return `rgba(255,255,255,${0.10 + 0.05 * i})`;
    // deeper reasons sit further from the effect's tone, so depth is legible as tone as well as width
    const c = surfaceOn(BG, pal[(i + 1) % pal.length], TONE_MIN_STEP * 1.5);
    return i % 2 === 0 ? c : separated(c, readableOn(c, '#ffffff', '#05070c'), TONE_MIN_STEP * 0.9);
  };

  // BOTTOM UP: the root arrives first, then each level that stands on it, and the effect settles last. You
  // cannot rest something on a reason that has not been given yet.
  const arriveAt = (level: number) => {                    // level 0 = effect, n = the root
    const k = n - level;                                   // the root's k is 0
    return easeOutCubic(clamp01(seg(t, 0.08 + k * 0.13, 0.34 + k * 0.13)));
  };

  const hair = Math.max(2, Math.round(base * 0.004));
  const enter = easeOutCubic(clamp01(seg(t, 0.02, 0.18)));

  const rows = [{cause: null as Cause | null, level: 0, share: effShare},
                ...causes.map((c, i) => ({cause: c, level: i + 1, share: causeShare}))];

  let acc = 0;
  return (
    <AbsoluteFill style={{background: BG, color: FG, overflow: 'hidden'}}>
      {rows.map((r, idx) => {
        const top = zoneTop + acc * zoneH;
        const hgt = r.share * zoneH;
        acc += r.share;
        const on = arriveAt(r.level);
        const wFrac = widthAt(r.level);
        const wpx = W * wFrac;
        const fill = r.level === 0 ? effFill : causeFill(r.level - 1);
        const ink = readableOn(fill, '#ffffff', '#05070c');
        const sub = dimOn(fill, ink);
        const label = r.level === 0 ? effect : (r.cause?.label ?? '');
        const note = r.level === 0 ? effectNote : (r.cause?.note ?? '');
        const tight = hgt < base * 0.10;
        const labelPx = Math.max(14, Math.min(Math.round(base * (r.level === 0 ? 0.048 : 0.036)),
                                              Math.round(hgt * 0.42), Math.round(wpx * 0.055)));
        return (
          <div key={idx} style={{position: 'absolute', left: (W - wpx) / 2, top, width: wpx, height: hgt,
            background: fill, opacity: on,
            // it SETTLES onto what is under it — a small drop, not a fade from nowhere
            transform: `translateY(${((1 - on) * -base * 0.035).toFixed(1)}px)`,
            boxShadow: `inset 0 0 0 ${hair}px ${BG}`,
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
            padding: `0 ${Math.round(base * 0.03)}px`, boxSizing: 'border-box', overflow: 'hidden'}}>
            <div style={{color: ink, font: `${r.level === 0 ? 800 : 700} ${labelPx}px/1.15 ${
              r.level === 0 ? disp : body}`, letterSpacing: r.level === 0 ? '-0.02em' : undefined}}>{label}</div>
            {note && !tight ? (
              <div style={{color: sub, font: `400 ${Math.round(labelPx * 0.6)}px/1.35 ${body}`,
                marginTop: Math.round(base * 0.005)}}>{note}</div>
            ) : null}
          </div>
        );
      })}

      {/* the joint word, on the seam between the effect and its immediate reason — the only line-like mark
          here, and it names the relation the blocks are already showing */}
      {/* A JOINT, not a caption. The blocks tile with no gap, so a word placed "above the seam" lands INSIDE
          the block above it — which is what the first version did, printing the joint across the effect's
          own bottom edge. It rides the seam on its own ground chip instead: a notch between two levels,
          which is also what it means. */}
      {because && n > 0 ? (
        <div style={{position: 'absolute', left: '50%',
          top: zoneTop + effShare * zoneH, transform: 'translate(-50%, -50%)',
          opacity: arriveAt(1) * 0.95, background: BG, color: FG, letterSpacing: '0.18em',
          padding: `${Math.round(base * 0.008)}px ${Math.round(base * 0.020)}px`,
          borderRadius: Math.round(base * 0.006),
          font: `700 ${Math.round(base * 0.022)}px/1 ${mono}`}}>{because}</div>
      ) : null}

      {kicker ? (
        <div style={{position: 'absolute', left: Math.round(W * 0.045), top: Math.round(zoneTop * 0.42),
          opacity: enter, letterSpacing: '0.16em', color: DIM,
          font: `700 ${Math.round(base * 0.024)}px/1.2 ${mono}`}}>{kicker}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default RestsOn;
