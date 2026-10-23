// SHOT · Cropped Type — one word set far larger than the windows it moves through: two bands across the frame, each
// a clip the word is too big for, so a viewer sees it cropped top and bottom and sliding past — one band solid, the
// other in outline, drifting in opposite directions — over the plain sentence the word stands for.
//
// WHAT IT ARGUES. Scale. A word bigger than its frame says "this is the big thing" before it is read, and the crop
// is what makes it read as BIG rather than as merely large type: the eye completes the letter past the edge. The
// statement underneath is the one line that must be read; the word is its emphasis, not its content. Not for a
// headline (HeadlineReveal), not for a word that has to be read whole and still (VariableTypeMorph).
//
// THE CROP IS A WINDOW, and that is what the type gates accept. Each band is an overflow clip that does NOT cover the
// frame, so text_safe_qa reads the cut as the author's (runtime/textSafe.tsx: "text clipped by an ancestor with
// overflow: hidden is INTENDED"); a word cut by the FRAME edge with no window around it would be a finding, and is.
//
// HOW IT MOVES. The letters rise into each band from below its edge, staggered, then the word keeps drifting — a
// constant, slow travel the whole shot, the type unlock on (runtime/glide) so it glides instead of stepping a pixel
// at a time. The statement rises line by line through its own masks.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, contrastOf, mix} from '../runtime/dna';
import {hasCJK} from '../runtime/cjkType';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {graphemes} from '../runtime/kineticCore';

export const DURATION = 165; // 5.5s

const BG_D0 = '#0c0d10', FG_D0 = '#f2f2f0', ACC_D0 = '#ff5a3c', LINE_D0 = '#2a2d33';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

export const CroppedType: React.FC<{
  kicker?: string;
  /** the one word (or two) set larger than its windows */
  word?: string;
  /** the sentence it stands for — the line that must be read */
  statement?: string;
  /** which way the solid band drifts; the outline band goes the other way */
  direction?: 'left' | 'right';
  accent?: string;
}> = ({kicker = 'AT SCALE', word = 'BIGGER', statement = 'Too large for its window',
       direction = 'left', accent: accIn} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H, fps} = useVideoConfig();
  const spanF = useAnimSpan();
  const WORD = String(word ?? '').trim();
  if (!WORD) throw new Error('CroppedType needs a `word` — the band is empty without one.');
  if (graphemes(WORD).length > 18) {
    throw new Error(`CroppedType's word is ${graphemes(WORD).length} characters; past 18 it is a phrase, and a ` +
      'cropped phrase cannot be read by its crop. Put the phrase in `statement` and give the band its one word.');
  }
  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const LINE = dna?.line ?? LINE_D0;

  const U = Math.min(W, H);
  const portrait = W < H;
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H), zoneH = zoneBot - zoneTop;
  const mx = Math.round(W * 0.07);
  const KICK = Math.ceil(U * 0.028);
  const gap = Math.round(U * 0.028);
  const cjk = hasCJK(WORD);

  // ── the windows ─────────────────────────────────────────────────────────────────────────────────────────
  const kickH = kicker ? Math.round(KICK * 1.25) + gap : 0;
  const stmtMax = Math.round(zoneH * (portrait ? 0.28 : 0.26));
  const bandH = Math.round(Math.min((zoneH - kickH - stmtMax - gap * 3) / 2, W * (portrait ? 0.24 : 0.2)));
  // the word's size against its band: Latin capitals stand ~0.73 em tall, a Han glyph ~0.9 em — each is set so a
  // fifth or so of it is past EACH of the band's edges, a crop the eye completes rather than a word cut in half.
  // (1.62 was the first number: the capitals just filled the band, 9% a side, and it read as large type in a box.)
  const size = Math.round(bandH * (cjk ? 1.5 : 1.95));
  // enough copies to cover the band and the drift with room to spare — an over-estimate only costs glyphs
  const perEm = cjk ? 1.0 : 0.62;
  const copies = Math.max(2, Math.ceil((W * 1.6) / Math.max(1, graphemes(WORD).length * perEm * size + size)) + 1);
  const run = Array.from({length: copies}, () => WORD).join(cjk ? '　' : '  ');
  // one handle per band (each KineticText resolves its face off its own anchor); the second is a cache hit
  const bigSpec = {text: run, w: Math.round(W * 3), nowrap: true, fit: 'none' as const, align: 'left' as const,
    font: {family: DISPLAY, weight: 760, size, lineHeight: 1.0, tracking: cjk ? 0 : -0.035}};
  const big = useKinetic(bigSpec);
  const big2 = useKinetic(bigSpec);
  const stmt = useKinetic({text: statement || ' ', w: W - 2 * mx, h: stmtMax, fit: 'box', maxLines: 3, align: 'left',
    wrap: 'balance', fitTiers: [{maxLines: 2, minSize: Math.round(U * 0.05)}],
    font: {family: DISPLAY, weight: 560, size: Math.round(U * (portrait ? 0.07 : 0.066)), minSize: Math.ceil(U * 0.04),
      lineHeight: 1.08, tracking: -0.015}});
  const kick = useKinetic({text: kicker || ' ', w: W - 2 * mx, nowrap: true, fit: 'box', align: 'left',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});

  const stmtH = statement ? (stmt.layout?.height ?? stmtMax) : 0;
  const blockH = kickH + bandH * 2 + gap + (statement ? gap * 1.4 + stmtH : 0);
  const top = Math.round(zoneTop + Math.max(0, (zoneH - blockH) / 2));
  const yBand1 = top + kickH, yBand2 = yBand1 + bandH + gap, yStmt = yBand2 + bandH + Math.round(gap * 1.4);

  // the drift: a tenth of the frame over the shot, as em per second, in opposite directions
  const spanS = Math.max(0.5, spanF / fps);
  const v = (W * 0.1) / (size * spanS);
  const dir = direction === 'right' ? 1 : -1;
  // the word's own height inside the band: centred on the glyphs' content box
  const glyphH = (big.layout?.lh ?? size);
  const yIn = Math.round((bandH - glyphH) / 2);
  const runW = big.layout?.width ?? W * 2;
  // start each run so the drift keeps it covering the band the whole shot
  const x1 = dir < 0 ? -Math.round(W * 0.12) : -Math.round(runW - W * 1.12);
  const x2 = dir < 0 ? -Math.round(runW - W * 1.12) : -Math.round(W * 0.12);
  const frameIn = easeOutCubic(clamp01(seg(t, 0.06, 0.24)));
  const hair = Math.max(1, Math.round(U * 0.0016));

  // A CROP LEAVES SLIVERS. Where a stroke ends a pixel or two inside the band's edge — 「更」's top bar did — the
  // sliver reads as a rule drawn along the edge, not as part of a letter. The band's edges fade over a few pixels, so
  // a sliver thinner than the fade disappears and a stroke cut through its body still reads as cut.
  const fade = Math.max(3, Math.round(bandH * 0.035));
  const edge = `linear-gradient(to bottom, transparent 0px, #000 ${fade}px, #000 ${bandH - fade}px, transparent ${bandH}px)`;
  const band = (y: number, children: React.ReactNode) => (
    <div style={{position: 'absolute', left: 0, top: y, width: W, height: bandH, overflow: 'hidden',
      WebkitMaskImage: edge, maskImage: edge}}>{children}</div>
  );
  const rules = (y: number) => (
    <>
      <div style={{position: 'absolute', left: 0, top: y - hair, width: W, height: hair, background: LINE,
        transformOrigin: '0 50%', transform: `scaleX(${frameIn})`}} />
      <div style={{position: 'absolute', left: 0, top: y + bandH, width: W, height: hair, background: LINE,
        transformOrigin: '100% 50%', transform: `scaleX(${frameIn})`}} />
    </>
  );
  const enter = (at: number) => ({from: {y: 0.85, opacity: 0}, enter: {by: 'grapheme' as const, at, stagger: 0.045,
    dur: 0.9, ease: 'expo' as const, until: 0.5}});
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={mx} y={top} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.06, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.36}}} />
      ) : kick.anchor}
      {rules(yBand1)}
      {rules(yBand2)}
      {band(yBand1, (
        <KineticText k={big} x={x1} y={yIn} color={ACC} read={false} id="band-solid"
          motion={{...enter(0.1), drift: {x: dir * v}}} />
      ))}
      {band(yBand2, (
        // THE OUTLINE IS A STROKE UNDER A GROUND-COLOURED FILL. A variable face keeps its overlapping contours, and a
        // plain text stroke draws every one of them — the first render had lines through the middle of E and R.
        // Painted stroke-first, the fill covers the inner half of the stroke and every overlap with it, so what is
        // left is the letter's outer edge alone (the stroke is doubled to keep its visible width).
        <KineticText k={big2} x={x2} y={yIn} color={BG} read={false} id="band-outline"
          style={{WebkitTextStroke: `${(Math.max(1.5, size * 0.011) * 2).toFixed(2)}px ${mix(FG, BG, 0.12)}`,
            paintOrder: 'stroke fill'} as React.CSSProperties}
          motion={{...enter(0.16), drift: {x: -dir * v}}} />
      ))}
      {statement ? (
        <KineticText k={stmt} x={mx} y={yStmt} color={FG} id="statement"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.03}, enter: {by: 'line', at: 0.2, stagger: 0.14,
            dur: 0.9, ease: 'expo', cueKeys: ['statement'], until: 0.72}}} />
      ) : stmt.anchor}
    </AbsoluteFill>
  );
};
export default CroppedType;
