// SHOT · Liquid Morph — an ORIGINAL design: one living, iridescent blob of material breathes and MORPHS,
// and the forms the film names fade through on its surface one after another, each with its word under the
// blob. "One thing, many shapes." Dark premium + iridescent gradient. Deterministic (blob vertices = sin of frame).
//
// THE FORMS ARE THE FILM'S. This register took no props at all: every film that reached for it printed
// "Ask. Draft. Analyse. Done." under a chat bubble, a page, a bar chart and a tick — a product's workflow,
// whatever the film was about — and the "analyse" glyph was a three-bar chart with bar heights of 52 / 82 / 36,
// a small invented dataset on every frame it crossed. Now `forms` is the sequence: 2-6 entries, each a label
// or `{label, icon?}` where `icon` is a runtime/icons name the film picks for the role that form plays (the
// icon rule in references/remotion-shot-authoring.md applies). A form with no icon draws no picture — the
// blob and the word carry it. The old four are the standalone default, drawn from the shared icon family;
// "Analyse" takes the magnifier rather than a chart glyph, so the demo draws no bars at all.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {Icon, type IconName} from '../runtime/icons';

export const DURATION = 165; // 5.5s

export type LiquidForm = {
  /** the word under the blob while this form is showing */
  label: string;
  /** the picture on the blob — chosen by the film for the role the form plays, never by position */
  icon?: IconName;
};

export const MIN_LIQUID_FORMS = 2;
export const MAX_LIQUID_FORMS = 6;

const DEFAULT_FORMS: LiquidForm[] = [
  {label: 'Ask.', icon: 'message'}, {label: 'Draft.', icon: 'file'},
  {label: 'Analyse.', icon: 'search'}, {label: 'Done.', icon: 'check'},
];

const normalise = (forms: unknown): LiquidForm[] => {
  if (!Array.isArray(forms) || forms.length < MIN_LIQUID_FORMS || forms.length > MAX_LIQUID_FORMS) {
    throw new Error(
      `LiquidMorph needs ${MIN_LIQUID_FORMS}-${MAX_LIQUID_FORMS} \`forms\` (got ` +
      `${Array.isArray(forms) ? forms.length : typeof forms}). One form has nothing to morph into; past six each ` +
      'form is on screen for under a second — split the sequence across two beats.');
  }
  return forms.map((f: any, i: number) => {
    const o = typeof f === 'string' ? {label: f} : (f ?? {});
    const label = String(o.label ?? '').trim();
    if (!label) throw new Error(`LiquidMorph: form ${i + 1} has no label.`);
    return o.icon == null || o.icon === '' ? {label} : {label, icon: o.icon as IconName};
  });
};

// a smooth closed organic-blob path from N perturbed points
function blobPath(cx: number, cy: number, R: number, frame: number, wob: number): string {
  const N = 12, pts: [number, number][] = [];
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    const r = R + Math.sin(a * 3 + frame * 0.05) * wob + Math.cos(a * 2 - frame * 0.037) * wob * 0.7;
    pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
  }
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < N; i++) {
    const p0 = pts[i], p1 = pts[(i + 1) % N];
    const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2;
    d += ` Q${p0[0]},${p0[1]} ${mx},${my}`;
  }
  return d + 'Z';
}

export const LiquidMorph: React.FC<{forms?: (string | LiquidForm)[]}> = ({forms: FORMS = DEFAULT_FORMS} = {}) => {
  const forms = normalise(FORMS);
  const t = useT();
  const dna = useDNA();
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const cx = W / 2, cy = H / 2 - 20;
  // THE BLOB'S RADIUS IS WHAT YIELDS ON A SHORT FRAME. The form label hangs at the blob's bottom edge and
  // the radius was a flat 300, so at 1:1 the word landed 70px inside the caption band (the sweep at the
  // three aspects nobody had run). Clamping the LABEL alone would have put it on the blob; a blob 60px
  // smaller is the same blob, and the word under it is the whole statement.
  const LABEL_LINE = 64;          // the label's own line box — `800 64px/1`, so exactly its height
  const GLOW = 26;                // the filter bleeds past the path; the word must clear the light too
  const R = Math.min(300, contentBottom(W, H) - LABEL_LINE - GLOW - cy);
  const idx = clamp01(seg(t, 0.06, 0.96)) * (forms.length - 1); // which form (fractional)
  // the old glyphs filled a 210px box on a 300px blob; an icon draws inside ~70% of its 24-grid, so its box is
  // larger to read at the same size, and it keeps that proportion when the blob shrinks
  const iconPx = Math.round(Math.min(260, R * 0.86));
  const labelPx = Math.min(64, ...forms.map((f) => fitTextPx(f.label, W * 0.86, 64)));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('radial-gradient(120% 120% at 50% 42%, #141326, #05060d 72%)')}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="iri" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#4F7BFF" /><stop offset="0.5" stopColor="#B14BFF" /><stop offset="1" stopColor="#FF5C9A" />
          </linearGradient>
          <filter id="glow"><feGaussianBlur stdDeviation="24" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path d={blobPath(cx, cy, R, frame, 34)} fill="url(#iri)" filter="url(#glow)" opacity={0.96} />
      </svg>
      {/* the form's icon fades through on the blob surface — only for a form the film gave an icon */}
      {forms.map((f, i) => f.icon ? (
        <div key={i} style={{position: 'absolute', left: cx - iconPx / 2, top: cy - iconPx / 2, width: iconPx, height: iconPx,
          opacity: clamp01(1 - Math.abs(idx - i))}}>
          <Icon name={f.icon} size={iconPx} ink="#fff" weight={1.45} />
        </div>
      ) : null)}
      {/* current form label */}
      <div style={{position: 'absolute', left: 0, right: 0, top: cy + R + GLOW, height: LABEL_LINE, textAlign: 'center'}}>
        {/* THE WORD IS ON THE FILM'S GROUND, NOT ON THE BLOB. The blob is a saturated iridescent fill and the
            icon riding it keeps its white; the label hangs BELOW the blob, on the page, so it is the film's
            ink — a literal near-white there measured 1.09:1 on a warm-white film with the register's entire
            legible mark count under 3:1 (scripts/ink_contrast_qa.py), which is the word gone. */}
        {forms.map((f, i) => <div key={i} style={{position: 'absolute', left: 0, right: 0, whiteSpace: 'nowrap',
          font: `800 ${labelPx}px/${leading(f.label, 1)} var(--f-display, Inter,system-ui,sans-serif)`,
          color: dna?.fg ?? '#fff', opacity: clamp01(1 - Math.abs(idx - i) * 1.4)}}>{f.label}</div>)}
      </div>
    </AbsoluteFill>
  );
};
export default LiquidMorph;
