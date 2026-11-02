// SHOT · Photo to Diagram — a REAL photograph turns into its own line drawing, and the drawing is then labelled: the
// beat moves from "this is the real thing" to "this is how it works" without ever leaving the thing. The photograph
// greys and dims, its OWN outlines draw on over it in the film's accent (scripts/photo_lines.py computes them from the
// photograph's edges — nobody drew them), the photograph fades to a ghost under the drawing, and the film's marks pin
// labels to the points it names.
//
// This is the skill's own move: an evidence register shows a photograph and points at it, a diagram register draws
// an idea; nothing carried one into the other in a single picture.
//
// The photograph is evidence (runtime/evidence: no `src`, no beat) and keeps its credit line. `lines`, `imageAspect`
// and `imageW` are filled by render_remotion from the file (photo_lines.ensure traces it once and caches by content).
// The plate is never drawn past the photograph's own pixels (media_res_qa's 1.25x is the ceiling, 1.15x the target).
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {requireEvidence} from '../runtime/evidence';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {useDNA, mix} from '../runtime/dna';

export const DURATION = 210; // 7 s
export const MAX_MARKS = 5;
const MAX_UPSCALE = 1.15;

export type DiagramMark = {x: number; y: number; label: string};

export const PhotoToDiagram: React.FC<{src?: string; lines?: string; imageAspect?: number; imageW?: number;
  marks?: DiagramMark[]; title?: string; credit?: string}> = ({src, lines, imageAspect, imageW, marks = [], title = '',
  credit = ''} = {}) => {
  const photo = requireEvidence('PhotoToDiagram', 'src', src, 'the real photograph the beat turns into a diagram');
  if (!lines) {
    throw new Error('PhotoToDiagram needs `lines` — the photograph\'s traced outlines. render_remotion fills it ' +
      '(scripts/photo_lines.py); a standalone still must pass it: python3 scripts/photo_lines.py <photo>');
  }
  if (!Array.isArray(marks) || marks.length > MAX_MARKS) throw new Error(`PhotoToDiagram takes 0-${MAX_MARKS} marks`);
  marks.forEach((m, i) => {
    if (!(m && m.x >= 0 && m.x <= 1 && m.y >= 0 && m.y <= 1)) {
      throw new Error(`PhotoToDiagram: mark ${i + 1} needs x and y in 0..1 (fractions of the photograph) — a label on a ` +
        'real photograph says "here", so "here" must be the film\'s');
    }
    if (!String(m.label ?? '').trim()) throw new Error(`PhotoToDiagram: mark ${i + 1} has no label`);
  });
  const dna = useDNA();
  const t = useT();
  const cue = useCues();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const BG = dna?.bg ?? '#0b0e13', FG = dna?.fg ?? '#f1f3f7', DIM = dna?.dim ?? '#8a92a2', ACC = dna?.accent ?? '#7cc4ff';
  const DISPLAY = 'var(--f-display, Inter, system-ui, sans-serif)';
  const MONO = dna?.fontMono ?? 'var(--f-mono, "JetBrains Mono", monospace)';

  // ---- the plate: fitted to the zone, never past the photograph's own pixels ----
  const aspect = imageAspect && isFinite(imageAspect) && imageAspect > 0 ? imageAspect : 4 / 3;
  const top = Math.max(CONTENT_TOP, Math.round(U * 0.07)) + (title ? Math.round(U * 0.06) : 0);
  const creditPx = Math.round(U * 0.019);
  const bottom = contentBottom(W, H) - (credit ? Math.round(creditPx * 2) : 0) - Math.round(U * 0.015);
  let pw = Math.min(W * 0.62, (bottom - top) * aspect);
  if (imageW && isFinite(imageW)) pw = Math.min(pw, imageW * MAX_UPSCALE);
  const ph = pw / aspect;
  const px0 = Math.round((W - pw) / 2), py0 = Math.round(top + (bottom - top - ph) / 2);

  // ---- the turn: photograph -> grey -> its outlines -> a ghost under the drawing ----
  const grey = easeInOutCubic(clamp01(seg(t, 0.2, 0.42)));
  const draw = easeInOutCubic(clamp01(seg(t, 0.26, 0.58)));
  const ghost = easeInOutCubic(clamp01(seg(t, 0.5, 0.64)));
  const ox = (marks[0]?.x ?? 0.5) * 100, oy = (marks[0]?.y ?? 0.5) * 100;
  const radius = draw * 150;                       // % of the plate: from the first mark outward past every corner
  const reveal = `radial-gradient(circle at ${ox}% ${oy}%, #000 ${Math.max(0, radius - 12)}%, transparent ${radius}%)`;
  const linesUrl = `url(${staticFile(lines)})`;

  const labelPx = Math.max(Math.round(U * 0.028), Math.min(Math.round(U * 0.034),
    ...marks.map((m) => fitTextPx(m.label, W * 0.2, Math.round(U * 0.034)))));
  return (
    <AbsoluteFill style={{background: dna ? `radial-gradient(90% 80% at 50% 45%, ${mix(BG, ACC, 0.06 * draw)}, ${BG} 72%)` : BG}}>
      {title ? <div style={{position: 'absolute', left: px0, top: Math.max(CONTENT_TOP, Math.round(U * 0.07)), color: mix(FG, DIM, 0.3),
        font: `700 ${fitTextPx(title, pw, Math.round(U * 0.036))}px/1.1 ${DISPLAY}`}}>{title}</div> : null}
      <div style={{position: 'absolute', left: px0, top: py0, width: pw, height: ph, overflow: 'hidden',
        borderRadius: Math.round(U * 0.008), boxShadow: `0 ${Math.round(U * 0.02)}px ${Math.round(U * 0.05)}px #0006`}}>
        <Img src={staticFile(photo)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover',
          opacity: 1 - 0.86 * ghost, filter: `grayscale(${grey}) brightness(${1 - 0.5 * grey})`}} />
        {/* the photograph's own outlines, in the film's accent, drawn on outward from the first point the film names */}
        <div style={{position: 'absolute', inset: 0, background: ACC,
          WebkitMaskImage: `${linesUrl}, ${reveal}`, maskImage: `${linesUrl}, ${reveal}`,
          WebkitMaskSize: '100% 100%, 100% 100%', maskSize: '100% 100%, 100% 100%',
          WebkitMaskRepeat: 'no-repeat', maskRepeat: 'no-repeat',
          WebkitMaskComposite: 'source-in', maskComposite: 'intersect'} as React.CSSProperties} />
      </div>
      {marks.map((m, i) => {
        const [a, b] = cue.win('marks.' + i, 0.6 + i * 0.06, 0.68 + i * 0.06, REACH_CUBIC);
        const on = easeOutCubic(clamp01(seg(t, a, b)));
        const cx = px0 + m.x * pw, cy = py0 + m.y * ph;
        // the label goes out to the NEAREST side of the plate, so its leader crosses as little of the drawing as it can
        const right = m.x >= 0.5;
        const lx = right ? Math.max(cx + U * 0.05, px0 + pw + U * 0.03) : Math.min(cx - U * 0.05, px0 - U * 0.03);
        const ly = cy;
        const dot = Math.round(U * 0.009);
        return (
          <React.Fragment key={i}>
            <svg style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity: on}} width={1} height={1}>
              <line x1={cx} y1={cy} x2={cx + (lx - cx) * on} y2={ly} stroke={mix(FG, ACC, 0.4)} strokeWidth={Math.max(2, U * 0.0018)} />
              <circle cx={cx} cy={cy} r={dot} fill={ACC} stroke={BG} strokeWidth={Math.max(2, U * 0.002)} />
            </svg>
            <div style={{position: 'absolute', top: ly - labelPx * 0.7, opacity: on, whiteSpace: 'nowrap', color: FG,
              ...(right ? {left: lx + U * 0.01} : {right: W - lx + U * 0.01}),
              font: `600 ${labelPx}px/${leading(m.label, 1.3)} ${DISPLAY}`}}>{m.label}</div>
          </React.Fragment>
        );
      })}
      {credit ? <div style={{position: 'absolute', left: px0, top: py0 + ph + Math.round(creditPx * 0.6), color: DIM, opacity: 0.85,
        font: `400 ${creditPx}px/1.35 ${MONO}`}}>{credit}</div> : null}
    </AbsoluteFill>
  );
};
export default PhotoToDiagram;
