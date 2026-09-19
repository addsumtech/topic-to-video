// CompressedSensingEq — the concept AS ITS EQUATION, not an abstract ridgeline. Compressed sensing is literally a
// constrained optimisation: minimise the L1 norm of the image in a sparse transform, subject to consistency with
// the measured (undersampled) k-space. Showing the formula + annotating each term teaches it precisely; a typeset
// equation is a legitimate, high-craft design, not only diagrams. Deterministic (terms reveal in order).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {fitText} from '@remotion/layout-utils';

// The equation as PLAIN TEXT, for measurement only — the same glyphs and gaps the JSX below sets, so what
// is measured is what is drawn. Keep the two in step: a measurement of a different string is a fit for a
// different line.
const EQ_TEXT = 'min\u00a0\u00a0‖Ψx‖1\u00a0\u00a0\u00a0subject\u00a0to\u00a0\u00a0\u00a0‖Fx−y‖2\u00a0≤\u00a0ε';

export const DURATION = 180; // 6s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  'L1 favors the fewest coefficients',
  'consistent with the measured k-space',
  'random undersampling → noise-like aliasing',
  'sparse in a transform',
];
const SERIF = "var(--f-display, 'Source Serif 4', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif)";

export const CompressedSensingEq: React.FC<{accent?: string; accent2?: string; label?: string}> = ({
  accent = '#22d3ee', accent2 = '#a78bfa', label = 'Compressed sensing',
} = {}) => {
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const t = useT();
  const eqY = H * 0.46;
  // FIT BY TYPE SIZE, NOT BY TRANSFORM, AND MEASURE THE FACE THAT ACTUALLY RENDERS.
  //
  // Two mistakes, both made here, both worth keeping written down. First: `transform: scale()` does not
  // change LAYOUT. The line still lays out at its full width inside a narrower frame, so it overflows its
  // box, `text-align: center` centres a box the glyphs have already spilled out of, and the type gate reads
  // rects nowhere near the ink — measured, a 9:16 render put the equation 198px from the left edge and 24px
  // from the right. Setting the font SIZE makes the line genuinely narrower: it fits, it centres, and every
  // rect is where its glyph is.
  //
  // Second, and the reason there is no constant here any more: I replaced the guessed natural width with one
  // MEASURED off a still — and measured it under the wrong typeface. `SERIF` resolves to `var(--f-display)`,
  // so the face is the FILM'S, and a plain `remotion still` renders the fallback serif while the sweep runs
  // the product DNA's Space Grotesk, which is wider. A fixed natural width is wrong by construction for any
  // register whose face comes from the DNA. `fitText` measures the real one — read from the DNA in JS, not
  // through the CSS var, because it measures in a detached node outside `.dna-film` where the var is
  // undefined (the same trap NeonGrid documents).
  //
  // The small runs (the subscripts and the italic "subject to") are measured at the FULL size, which
  // over-counts them and lands the line a little inside its budget. That is the safe direction: the cost is
  // a few percent of width, the alternative is a glyph over the edge.
  const eqFace = dna?.fontDisplay ?? "'Source Serif 4', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif";
  const EQ_PX = Math.min(92, fitText({
    text: EQ_TEXT, withinWidth: W * 0.94, fontFamily: eqFace, fontWeight: 400, letterSpacing: '0.01em',
  }).fontSize);
  const SUB_PX = Math.round(EQ_PX * (44 / 92));
  const app = clamp01(seg(t, 0.08, 0.4));                   // the equation writes in
  const a1 = clamp01(seg(t, 0.42, 0.62));                   // annotate the sparse term
  const a2 = clamp01(seg(t, 0.6, 0.82));                    // annotate the data-consistency term

  const span = (txt: string, color: string, o = 1) => <span style={{color, opacity: o}}>{txt}</span>;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 44%, #0b1120, #05060a)')}}>
      {/* the equation */}
      {/* THE LINE IS ITS OWN BOX. It used to be laid out inside a full-width div, and a line wider than the
          div does not wrap here (every gap is an &nbsp;) — it OVERFLOWS. Two things followed. The composition
          was off-centre: measured on a 9:16 render the ink sat 198px from the left edge and 24px from the
          right, because what `text-align: center` centred was a box the glyphs had already spilled out of.
          And the type-safety gate reported the ε cut off by 75px when the painted glyph was 24px INSIDE the
          frame — a client rect on an inline box inside an overflowing, transformed line is not where the ink
          is. An inline-block shrink-wraps to the line's true width, so the centring is真 and the rect is honest.

          NATURAL WIDTH, MEASURED: 1352px. The old 1600 was a guess that scaled the equation down to 79% of
          the width it was given — the frame budget is 94%, and at 1352 it uses it. (Measured off the ink
          extent of a 16:9 still, where the scale is 1: x=284..1635.) */}
      <div style={{position: 'absolute', left: 0, right: 0, top: eqY, textAlign: 'center', opacity: app,
        font: `400 ${EQ_PX}px/1.1 ${SERIF}`, color: '#eef4fb', letterSpacing: '0.01em'}}>
        <span style={{display: 'inline-block', whiteSpace: 'nowrap'}}>
        {span('min', '#9fb4cc')}&nbsp;&nbsp;
        {span('‖', '#cfe0f2')}{span('Ψx', accent)}{span('‖', '#cfe0f2')}<span style={{fontSize: SUB_PX, verticalAlign: 'sub', color: '#cfe0f2'}}>1</span>
        &nbsp;&nbsp;&nbsp;<span style={{font: `italic 400 ${SUB_PX}px/1 ${SERIF}`, color: '#9fb4cc'}}>subject&nbsp;to</span>&nbsp;&nbsp;&nbsp;
        {span('‖', '#cfe0f2')}{span('Fx−y', accent2)}{span('‖', '#cfe0f2')}<span style={{fontSize: SUB_PX, verticalAlign: 'sub', color: '#cfe0f2'}}>2</span>
        &nbsp;{span('≤', '#9fb4cc')}&nbsp;{span('ε', '#9fb4cc')}
        </span>
      </div>

      {/* annotation: the sparse transform term */}
      <div style={{position: 'absolute', left: W * 0.2, top: eqY - 120, width: 300, textAlign: 'center', opacity: a1}}>
        <div style={{color: accent, font: "700 24px/1.2 var(--f-body, Inter, sans-serif)"}}>sparse in a transform</div>
        <div style={{color: '#8aa', font: "400 18px/1.3 var(--f-body, Inter, sans-serif)", marginTop: 4}}>L1 favors the fewest coefficients</div>
        <div style={{position: 'absolute', left: 150, top: 62, width: 2, height: 46, background: `${accent}88`}} />
      </div>
      {/* annotation: the data-consistency term */}
      <div style={{position: 'absolute', left: W * 0.5, top: eqY + 120, width: 360, textAlign: 'center', opacity: a2}}>
        <div style={{position: 'absolute', left: 180, top: -48, width: 2, height: 46, background: `${accent2}88`}} />
        <div style={{color: accent2, font: "700 24px/1.2 var(--f-body, Inter, sans-serif)"}}>consistent with the measured k-space</div>
        <div style={{color: '#8aa', font: "400 18px/1.3 var(--f-body, Inter, sans-serif)", marginTop: 4}}>random undersampling → noise-like aliasing</div>
      </div>

      <div style={{position: 'absolute', left: 0, right: 0, top: 92, textAlign: 'center',
        color: '#dfe8f5', font: '700 40px/1.1 var(--f-body, Inter, system-ui, sans-serif)', letterSpacing: '-0.01em',
        opacity: lerp(0.4, 1, clamp01(t * 4))}}>{label}</div>
    </AbsoluteFill>
  );
};
export default CompressedSensingEq;
