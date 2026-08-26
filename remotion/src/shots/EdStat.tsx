// SHOT · EdStat — an EDITORIAL pull-stat (the editorial analogue of TermCounter): a kicker + a HUGE serif figure
// + a caption, ruled like a magazine feature. The 'metric/hero-stat' idea rebuilt in the editorial DNA, not a
// terminal counter reskinned. Deterministic (count = fn of t; lands ~35% then holds — see ROLL below).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {measureText, fitTextOnNLines} from '@remotion/layout-utils';
import {useT, seg, clamp01, easeOutCubic, lerp} from '../runtime/motion';
import {useDNA, EdFrame} from '../runtime/dna';
import {Figure} from '../runtime/atoms';
import {CONTENT_TOP, captionBand} from '../runtime/layout';

export const DURATION = 155;

// D0 — the no-DNA fallbacks. Kept as named constants so a colour/face literal can never be written into an
// expression that also reads a DNA token (the defect that dropped an off-system tile into a themed film).
const FG_D0 = '#efe9df', DIM_D0 = '#9a9084', ACC_D0 = '#e2603f';
const BG_D0 = 'radial-gradient(120% 120% at 50% -6%, #1c1815, #0d0b09 74%)';

// The figure's line box is TIGHTER than its glyphs (every `Figure` form sets a sub-1 line-height), so a ','
// or a '(' hangs BELOW the box and lands on whatever line follows — "31,000" over 「个测试套件（约）」 put the
// comma between 「件」 and 「（约）」 in a delivered film. Reserve this fraction of the figure size under the
// figure line, ALWAYS (not only when the string happens to contain a comma), so no glyph of any value at any
// length can touch the line beneath it. 0.26em clears the deepest descender of the faces the DNA presets use
// (~0.20em below the line box for both the 0.86-leading serif and the 0.9-leading mono form).
const DESCENDER_RESERVE = 0.26;

export const EdStat: React.FC<{kicker?: string; value?: string; unit?: string; caption?: string;
  framed?: boolean; roll?: boolean}> = ({
  kicker = 'BY THE NUMBERS', value = '100', unit = '', caption = '', framed = false, roll = true} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const body = dna?.fontBody ?? 'Inter, system-ui, sans-serif';
  const disp = dna?.fontDisplay ?? '"Playfair Display", Georgia, serif';
  const mono = dna?.fontMono ?? 'ui-monospace, SFMono-Regular, Menlo, monospace';
  const fg = dna?.fg ?? FG_D0, dim = dna?.dim ?? DIM_D0, acc = dna?.accent ?? ACC_D0;

  // ── the number ────────────────────────────────────────────────────────────────────────────────────────
  const raw = String(value ?? '');
  // SIGNED DATA RENDERS SIGNED: stripping everything but digits turned "-12" into 12, i.e. silently flipped
  // the claim. Parse the sign separately and carry it through the roll and the formatter.
  const sign = /^\s*-/.test(raw) ? -1 : 1;
  const num = sign * (parseFloat(raw.replace(/[^\d.]/g, '')) || 0);
  const decimals = (raw.split('.')[1]?.replace(/[^\d]/g, '') || '').length;
  const fmt = (v: number) => (Math.abs(num) >= 1000
    ? (Math.round(v) || 0).toLocaleString('en-US')   // `|| 0` so a rolling negative never prints "-0"
    : v.toFixed(decimals));

  // ROLL — the count-up. Two things were wrong in a delivered film and both are fixed here:
  //  • `roll={false}` renders the figure STATIC, correct from the very first frame. A beat that is ABOUT a
  //    number ("we could not source this one") must never parade invented intermediate digits: the screen
  //    showed 17%, then 56%, and only reached the narrated 60% past the halfway mark, so for ~2.8s of a 5.1s
  //    beat the frame displayed figures that appear in no source.
  //  • the DEFAULT roll now SETTLES BY t≈0.32 (was 0.7). The figure is therefore correct for two thirds of
  //    the beat instead of one third — and, decisively, correct at the mid-scene frame the delivery gate
  //    captures. Default is still "it rolls", so films that chose this register are unchanged in kind.
  const g = roll ? easeOutCubic(clamp01(seg(t, 0.04, 0.32))) : 1;
  const shown = fmt(roll ? lerp(0, num, g) : num);

  // ── sizing: measured, not assumed ─────────────────────────────────────────────────────────────────────
  // WIDTH-AWARE: size the figure by its FINAL string length so a big number ("5,000,000") stays inside the
  // frame (a fixed 260px overflowed the surface + ran the unit off-screen). Sizing off the landed value keeps
  // it stable (no reflow jitter as it counts up — intermediate strings are shorter, so they always fit).
  const finalStr = fmt(num);
  const heurSize = Math.max(108, Math.min(260, Math.floor(1120 / (finalStr.length * 0.6))));
  // The heuristic assumes a 0.6em advance — true for the mono forms, wrong for a proportional display face,
  // and blind to the UNIT entirely (a CJK unit is 1em per glyph). So MEASURE, and only ever shrink from the
  // heuristic: a film that fitted before is untouched, one that would have overflowed now fits.
  const figForm = dna?.atoms?.figure ?? 'serif';                     // mirrors atoms.formOf(dna,'figure','serif')
  const figFace = figForm === 'mono' || figForm === 'segment' ? mono : disp;
  const figWeight = figForm === 'serif' ? 900 : figForm === 'segment' ? 700 : 800;
  const figTrack = figForm === 'serif' ? '-0.02em' : figForm === 'mono' ? '-0.018em'
    : figForm === 'segment' ? '0.06em' : '-0.03em';
  const figLine = figForm === 'segment' ? 1 : figForm === 'serif' ? 0.86 : 0.9;
  // The unit: the `serif` form gives it its own 700; every other form lets it inherit the figure's weight.
  const unitWeight = figForm === 'serif' ? 700 : figWeight;
  const unitFace = figForm === 'serif' ? disp : figFace;
  // EdFrame's own column is `min(84vw, 1300px)`, plus 72px side padding + 1px border when framed. Mirrored
  // here because the figure has to be sized BEFORE it is handed to the frame.
  const availW = Math.max(200, Math.min(W * 0.84, 1300) - (framed ? 146 : 0));
  // width of `text` per 1px of font-size (letter-spacing is in em, so this scales linearly and one measure
  // serves every candidate size).
  const perPx = React.useCallback((text: string, family: string, weight: number, track: string) =>
    (text ? measureText({text, fontFamily: family, fontSize: 100, fontWeight: weight, letterSpacing: track}).width / 100 : 0),
  []);
  const figPer = perPx(finalStr, figFace, figWeight, figTrack);
  const unitPer = perPx(unit, unitFace, unitWeight, figTrack);
  const widthFit = figPer > 0 ? Math.floor(availW / figPer) : heurSize;
  const size0 = Math.min(heurSize, widthFit);
  // Figure's `serif` form defaults its unit to 0.28 of the FIGURE size unclamped — before atoms, EdStat
  // clamped that ratio's OUTPUT to [32,64]px so the unit never got comically large on a short number or
  // vanishingly small on a long one. Passing the ratio (not the px value) reproduces that clamp exactly.
  const unitPxAt = (s: number) => Math.max(32, Math.min(64, Math.round(s * 0.28)));

  // INLINE vs STACKED unit. "60" + "%" belongs on one baseline; "31,000" + 「个测试套件（约）」 does not fit one
  // and used to WRAP inside the figure's own flex row — which is exactly where the comma landed on top of the
  // unit. Decide it by measurement instead: if the pair does not fit the column, the unit becomes its own
  // line under the reserved descender space, where nothing can collide with it.
  const GAP = 22;
  const inlineUnit = !unit || figPer * size0 + GAP + unitPer * unitPxAt(size0) <= availW * 0.98;

  // HEIGHT-AWARE too: the block is centred in the CONTENT ZONE, so a tall stack (kicker + figure + unit line
  // + a 3-line CJK caption) must fit that zone or it grows into the burned-caption band. Reserve the parts we
  // can measure and give the figure what is left.
  const capW = Math.min(900, availW);
  // ceil(total width / column width) under-counts a ragged (word-wrapped) break, hence the 6% allowance.
  const capLines = caption ? Math.min(4, Math.max(1, Math.ceil(perPx(caption, body, 400, 'normal') * 36 * 1.06 / capW))) : 0;
  const capH = caption ? 30 + capLines * 50 : 0;                    // marginTop + 36px/1.4 lines
  const uFit = inlineUnit ? null : fitTextOnNLines({text: unit, maxLines: 2, maxBoxWidth: availW,
    fontFamily: unitFace, fontWeight: unitWeight, maxFontSize: unitPxAt(size0)});
  const stackUnitPx = uFit ? Math.max(20, Math.round(uFit.fontSize)) : 0;
  const stackLines = stackUnitPx ? Math.min(2, Math.max(1, Math.ceil(unitPer * stackUnitPx * 1.02 / availW))) : 0;
  const stackH = stackLines ? 16 + stackLines * stackUnitPx * 1.25 : 0;
  const headH = (kicker ? 48 : 0) + 42;                             // EdFrame: kicker 26px + 22 gap, rule 2 + 40
  const zoneH = H - captionBand(W, H) - CONTENT_TOP;
  const heightFit = Math.floor(Math.max(0, zoneH - headH - stackH - capH) / (figLine + DESCENDER_RESERVE));
  const numSize = Math.max(48, Math.min(size0, heightFit));
  const unitScale = unitPxAt(numSize) / numSize;
  const descPad = Math.round(numSize * DESCENDER_RESERVE);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0,
      // FULL-BLEED ground (the padding is border-box, so it only moves the flex CENTRE — it never insets the
      // background). Centring on the raw frame put a tall pull-stat's caption into the burned-caption band at
      // narrow aspects; centre it in the CONTENT ZONE instead.
      boxSizing: 'border-box', paddingTop: CONTENT_TOP, paddingBottom: captionBand(W, H),
      display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <EdFrame dna={dna} kicker={kicker} t={t} framed={framed} align="left">
        <div style={{display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', maxWidth: '100%',
          paddingBottom: descPad}}>
          <Figure value={shown} unit={inlineUnit ? unit : undefined} ink={fg} tone={acc} size={numSize}
            unitScale={unitScale} gap={GAP} fallbackForm="serif" fallbackFamily={disp} />
        </div>
        {inlineUnit || !unit ? null : (
          <div style={{color: acc, font: `${unitWeight} ${stackUnitPx}px/1.25 ${unitFace}`,
            letterSpacing: '0.01em', maxWidth: '100%', marginTop: 16}}>{unit}</div>
        )}
        {caption ? <div style={{marginTop: 30, color: dim, font: `400 36px/1.4 ${body}`, maxWidth: capW}}>{caption}</div> : null}
      </EdFrame>
    </AbsoluteFill>
  );
};
export default EdStat;
