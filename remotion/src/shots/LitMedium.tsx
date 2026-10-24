// SHOT · LitMedium — a statement set on the topic's own MEDIUM, under one slow light: a letter's paper, a coast's
// water, a machine's brushed metal, a potter's clay. Family X (material surfaces).
//
// WHAT IT ARGUES. The ground is the claim's substance. A beat about what something is MADE of, or WHERE it lives —
// "it all started on paper", "the harbour decides", "milled from one block", "shaped by hand" — is said on that
// material, and the material is shown the way you know it: by how it answers light. The surface never moves (it is
// one sheet, one pour, one plate); a single light drifts across it over the beat, so the tooth, the glints, the
// brushing, the relief read as a real object in a real room (runtime/material.tsx). Hide the type and the frame
// still says the medium; hide the light's motion and it is a texture swatch.
//
// THE MEDIUM IS THE FILM'S. `material` comes from the beat, else the film's DNA (`dna.material.kind`); the base
// colour from `base`, else the medium's own. The type is set ON the material, so its ink is picked against the
// material's MEASURED shade span (MATERIAL_SPAN: the 2nd and 98th percentile of the lit ground, rendered), not its
// base colour alone — a lit ground is a range, and a reader sees its worst end.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic} from '../runtime/motion';
import {useDNA, readableOnAll, contrastOf, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitBlockPx} from '../runtime/layout';
import {LitGround, isMaterial, MATERIALS, MATERIAL_BASE, materialShades, type MaterialKind} from '../runtime/material';
import {dnaLight} from '../runtime/optics';

export const DURATION = 165; // 5.5s — long enough for the light to be seen to travel

const DISPLAY = 'var(--f-display, "Playfair Display", "Noto Serif SC", Georgia, serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';
const INK_DARK = '#15120f', INK_LIGHT = '#fbf8f2';
// THE LIGHT TRAVELS ON THE FAR SIDE OF THE WORDS. A specular medium's glints cluster under its low point light; the
// type column is on the left at 16:9, so the light rides the top edge across the right of the frame. In portrait the
// column is the full width and centred in the content zone, so the light rides the top edge across the middle —
// the glints stay near the top, above the words. MATERIAL_SPAN is measured over the type column ON THESE PATHS.
export const LIGHT_TRAVEL = (portrait: boolean): [number, number] => (portrait ? [0.3, 0.7] : [0.66, 0.96]);

export const LitMedium: React.FC<{
  /** the medium: paper | water | metal | clay — the film's, else the DNA's `material.kind` */
  material?: MaterialKind;
  /** the medium's colour (#rrggbb); default the medium's own */
  base?: string;
  kicker?: string;
  title?: string;
  note?: string;
}> = ({material: matIn, base: baseIn, kicker = 'THE MEDIUM', title = 'Said on its own surface',
       note = 'one light, moving slowly across it'} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const material = matIn ?? dna?.material?.kind ?? 'paper';
  if (!isMaterial(material)) {
    throw new Error(`LitMedium: material must be one of ${MATERIALS.join(', ')} (got ${JSON.stringify(material)}).`);
  }
  const base = baseIn ?? MATERIAL_BASE[material];
  if (!String(title ?? '').trim()) throw new Error('LitMedium needs a title — the statement the medium carries.');
  // THE INK, against the lit ground's measured span — the worst end decides
  const span = materialShades(material, base);
  const INK = readableOnAll(span, INK_DARK, INK_LIGHT);
  const worst = Math.min(...span.map((g) => contrastOf(INK, g)));
  // a quieter ink for the kicker and note, but never under body contrast on the worst end of the span
  let DIM = INK;
  for (let f = 0.08; f <= 0.4 + 1e-9; f += 0.04) {
    const c = mix(INK, base, f);
    if (Math.min(...span.map((g) => contrastOf(c, g))) < 4.5) break;
    DIM = c;
  }
  if (worst < 4.5) {
    throw new Error(`LitMedium: no ink reads on ${material} ${base} across its lit span (best ${worst.toFixed(2)}:1, ` +
      'needs 4.5:1 for the note) — pass a lighter or darker `base`.');
  }
  const U = Math.min(W, H), portrait = W < H;
  const x0 = Math.round(W * (portrait ? 0.08 : 0.09)), colW = Math.round(W * (portrait ? 0.84 : 0.62));
  const top = CONTENT_TOP, bot = contentBottom(W, H), zoneH = bot - top;
  const KICK = Math.round(U * 0.026), NOTE = Math.round(U * 0.036);
  const titlePx = fitBlockPx(title, colW, zoneH * 0.55, Math.round(U * 0.12), {usable: 1, adv: 0.56, leading: 1.08,
    min: Math.round(U * 0.05)});
  const kin = easeOutCubic(seg(t, 0.08, 0.3)), tin = easeOutCubic(seg(t, 0.14, 0.4)), nin = easeOutCubic(seg(t, 0.3, 0.52));
  return (
    <AbsoluteFill style={{background: base, overflow: 'hidden'}}>
      <LitGround material={material} base={base} light={dnaLight(dna)} travel={LIGHT_TRAVEL(portrait)} />
      <div style={{position: 'absolute', left: x0, top, width: colW, height: zoneH, display: 'flex',
        flexDirection: 'column', justifyContent: 'center', gap: Math.round(U * 0.028)}}>
        {kicker ? (
          <div style={{opacity: kin, color: DIM, font: `600 ${KICK}px/1.2 ${MONO}`, letterSpacing: '0.18em',
            textTransform: 'uppercase'}}>{kicker}</div>
        ) : null}
        <div style={{opacity: tin, transform: `translateY(${Math.round((1 - tin) * U * 0.02)}px)`, color: INK,
          font: `700 ${titlePx}px/1.08 ${DISPLAY}`, letterSpacing: '-0.01em'}}>{title}</div>
        {note ? (
          <div style={{opacity: nin, color: DIM, font: `500 ${NOTE}px/1.35 ${BODY}`, maxWidth: colW}}>{note}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export default LitMedium;
