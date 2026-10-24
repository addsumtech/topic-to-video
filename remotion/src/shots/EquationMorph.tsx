// SHOT · Equation Morph — the beat's equation WRITTEN on, then carried through its next forms the way a derivation is
// worked on a board: the marks two forms share travel to their new places, the rest leave and arrive, and at the end
// the term the narration is about is picked out (circled, swelled, named). Real typeset maths — the film's own TeX,
// set by MathJax's TeX fonts (runtime/mathMorph) — never a Unicode imitation of it.
//
// WHAT IT ARGUES. That the next form IS the last one, rearranged. Hide the caption and the motion still says which
// parts survived the step (they slid), which were consumed (they shrank away) and which the step introduced (they grew
// in); a constant that changes sides travels OVER the equals sign rather than through it, so "move it across" is
// something the eye watches happen. Not for a single static formula with no steps and no term to point at (a title
// register will do), and not for a quantity's history (a chart).
//
// HOW IT MOVES. Form 1 is written glyph by glyph — outline drawn, then filled (Manim's Write). Each later form arrives
// by TransformMatchingTex (runtime/mathCore): \class{name}{…} in two forms marks the SAME term and is matched first,
// then the longest run of shared marks in reading order, measured where the glyphs are drawn; the forms share one
// scale and one baseline, and their relation signs sit on one vertical when the frame allows, so `=` never moves. The
// step labels swap as each form lands. `highlight` names a \class in the last form: a frame is drawn round it, it
// swells once and keeps the accent, and its label takes the label line. `live` turns a \class slot in the last form
// into a number that runs from the film's `from` to its `to` (a ValueTracker) — the settled frame prints `to` exactly.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';
import {useDNA, readableOn, dimOn, contrastOf} from '../runtime/dna';
import {drawOn} from '../runtime/draw';
import {rows} from '../runtime/rows';
import {useKinetic, KineticText} from '../runtime/kinetic';
import {useEquations, MathLayer, frameAround, placeAll, matchGlyphs, writeState, transformState, stillState,
  indicate, unionBox, glyphsOf, liveDraws, liveText, parseLive, type Equation, type GDraw} from '../runtime/mathMorph';

export const DURATION = 330; // 11s — four forms need a held second each to be read

const BG_D0 = '#0c1016', FG_D0 = '#f1f3f7', DIM_D0 = '#8d96a6', ACC_D0 = '#ffb547';
const DISPLAY = 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

export type EqStep = {
  /** the form, in TeX. \class{name}{…} names a term: the same name in two forms is the same term. */
  tex: string;
  /** what this form is — the step that produced it ("complete the square", 「两边开平方」) */
  label?: string;
};
export type EqHighlight = {
  /** a \class name in the LAST form */
  term: string;
  /** what the term is */
  label?: string;
};
export type EqLive = {
  /** a \class{live…} slot in the LAST form, written as wide as the widest value (e.g. \class{live}{00.0}) */
  term: string;
  /** the film's two values; the number runs from one to the other */
  from: string;
  to: string;
};

const DEFAULT_TITLE = 'Solving by completing the square';
const DEFAULT_HIGHLIGHT: EqHighlight = {term: 'root', label: 'Two roots: x = −1 and x = −5'};
const DEFAULT_STEPS: EqStep[] = [
  {tex: 'x^2 + 6x + 5 = 0', label: 'The equation'},
  {tex: '\\class{sq}{(x+3)^2} - 4 = 0', label: 'Complete the square'},
  {tex: '\\class{sq}{(x+3)^2} = 4', label: 'Move the constant across'},
  {tex: 'x = -3 \\class{root}{\\pm 2}', label: 'Take the square root'},
];

export const EquationMorph: React.FC<{
  kicker?: string;
  title?: string;
  /** 1–4 forms of the expression, in order */
  steps?: EqStep[];
  /** a term of the last form to pick out */
  highlight?: EqHighlight;
  /** a number in the last form that runs from one value to another */
  live?: EqLive;
  /** `equals` sets every form's relation sign on one vertical (when the frame allows); `center` centres each form */
  align?: 'equals' | 'center';
  accent?: string;
}> = ({kicker = 'DERIVATION', title: TITLE_IN, steps: STEPS_IN = DEFAULT_STEPS,
       highlight: HL_IN = DEFAULT_HIGHLIGHT, live, align = 'equals', accent: accIn} = {}) => {
  // The demo's title and highlighted term belong to the DEMO's forms: a film that writes its own steps and leaves
  // either out gets none — not a sentence about completing the square over somebody else's equation. Steps and the
  // highlight are told apart by IDENTITY (an omitted prop IS the default object, and the demo-copy gate reads both as
  // defaults); the title by `??`, because a string default cannot be told apart from the same string passed.
  const demo = STEPS_IN === DEFAULT_STEPS;
  const title = TITLE_IN ?? (demo ? DEFAULT_TITLE : undefined);
  const highlight = demo || HL_IN !== DEFAULT_HIGHLIGHT ? HL_IN : undefined;
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const steps = rows<EqStep>(STEPS_IN, 'steps', 'EquationMorph');
  if (!steps.length || steps.length > 4) {
    throw new Error(`EquationMorph shows 1–4 forms of one expression, got ${steps.length} — a longer derivation is two beats.`);
  }
  steps.forEach((s, i) => {
    if (!s || typeof s.tex !== 'string' || !s.tex.trim()) throw new Error(`EquationMorph: form ${i + 1} has no \`tex\`.`);
  });
  const labelled = steps.filter((s) => (s.label ?? '').trim()).length;
  if (labelled && labelled !== steps.length) {
    throw new Error('EquationMorph: label every form or none — a form with no label would show the previous one\'s.');
  }
  if (live) parseLive(live.from), parseLive(live.to);      // throws by name on anything that is not one number

  const BG = dna?.bg ?? BG_D0;
  const FG = readableOn(BG, dna?.fg ?? FG_D0, FG_D0, '#0b0f17');
  const acc0 = accIn ?? dna?.accent ?? ACC_D0;
  const ACC = contrastOf(acc0, BG) >= 3 ? acc0 : readableOn(BG, acc0, FG);
  const DIM = dimOn(BG, dna?.dim ?? DIM_D0, 4.5);

  const U = Math.min(W, H);
  const mx = Math.round(W * 0.07);
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const KICK = Math.ceil(U * 0.028);
  const kickH = kicker ? Math.round(KICK * 1.25 + U * 0.022) : 0;
  const TITLE = Math.round(U * 0.058);
  const titleH = title ? Math.round(TITLE * 1.12 * 2 + U * 0.02) : 0;
  const LABEL = Math.round(U * 0.04);
  const hasLabelLine = labelled > 0 || !!highlight?.label;
  const labelH = hasLabelLine ? Math.round(LABEL * 1.5 * 2) : 0;

  const kick = useKinetic({text: kicker || ' ', w: W - 2 * mx, nowrap: true, fit: 'box',
    font: {family: MONO, weight: 600, size: KICK, minSize: KICK, lineHeight: 1.2, tracking: 0.14}});
  const head = useKinetic({text: title || ' ', w: W - 2 * mx, h: titleH, fit: 'box', maxLines: 2, wrap: 'balance',
    font: {family: DISPLAY, weight: 640, size: TITLE, minSize: Math.ceil(U * 0.036), lineHeight: 1.08, tracking: -0.015}});
  // the label line: one alternative per form, then the highlighted term's label — a swap, read as one line by the gates
  const alts = [...(labelled ? steps.map((s) => String(s.label)) : []), ...(highlight?.label ? [highlight.label] : [])];
  const lab = useKinetic({alts: alts.length ? alts : [' '], w: W - 2 * mx, h: labelH, fit: 'box', maxLines: 2,
    align: 'center', wrap: 'balance', valign: 'top',
    font: {family: BODY, weight: 520, size: LABEL, minSize: Math.ceil(U * 0.03), lineHeight: 1.3}});

  const eqs = useEquations(steps.map((s) => s.tex));

  // ── the timeline (t is the shot's 0→1) ───────────────────────────────────────────────────────────────────────
  const nForms = steps.length;
  const writeA = 0.05, writeB = nForms > 1 ? 0.22 : 0.4;
  const endT = highlight ? 0.74 : 0.9;
  const slot = nForms > 1 ? (endT - writeB) / (nForms - 1) : 0;
  // each later form: held for 45% of its slot (the last form read), then transformed over the rest
  const trans = Array.from({length: Math.max(0, nForms - 1)}, (_, i) => {
    const s0 = writeB + slot * i;
    return [s0 + slot * 0.42, s0 + slot] as [number, number];
  });
  const hlA = endT + 0.01, hlB = Math.min(0.95, endT + 0.12);
  const lastLand = nForms > 1 ? trans[nForms - 2][1] : writeB;
  const liveA = lastLand + 0.02, liveB = Math.min(0.96, lastLand + (highlight ? 0.14 : 0.3));
  const swapTimes = [...trans.map(([a, b]) => (a + b) / 2), ...(highlight?.label ? [hlA + 0.02] : [])];

  // ── the equations ───────────────────────────────────────────────────────────────────────────────────────────
  const boxTop = zoneTop + kickH + titleH + U * 0.03;
  const boxBot = zoneBot - labelH - U * 0.035;
  const box = {x: mx, y: boxTop, w: W - 2 * mx, h: Math.max(U * 0.1, boxBot - boxTop)};
  const EM = Math.round(U * 0.115);
  let draws: GDraw[] = [];
  let shownTex = steps[0].tex;
  let emPx = EM;
  let frame: string | null = null;
  let frameP = 0;
  let leader: [number, number, number, number] | null = null;
  let labelY = zoneBot - labelH;
  if (eqs) {
    // the live slot is the film's number, never the template's digits: drawn apart from the matching
    const liveIdx = live ? new Set(glyphsOf(eqs[nForms - 1], live.term)) : new Set<number>();
    if (live && !liveIdx.size) throw new Error(`EquationMorph: \`live.term\` "${live.term}" is not a \\class in the last form.`);
    const forms: Equation[] = eqs.map((e, i) => (i === nForms - 1 && liveIdx.size
      ? {...e, glyphs: e.glyphs.filter((_, gi) => !liveIdx.has(gi))} : e));
    // THE EQUATION AND ITS LABEL ARE ONE GROUP, centred in the room under the heading. Placed in the whole room, a
    // portrait frame set the label a third of the screen below the equation it names (seen at 9:16). So: the scale
    // from the whole room, then the group's real height (the tallest form's ink + the label line) centred in it.
    const fit = placeAll(eqs, box, EM, align);
    // A FORM TOO WIDE FOR THE FRAME IS REFUSED, NOT SET SMALLER. The fit shrinks the em until the widest form fits; below
    // ~4% of the short side (43 px at 1080) maths stops being readable on a phone, and a register that shrinks past it
    // ships an equation nobody can read with every gate green (the type gate only warns).
    if (fit.s * 1000 < U * 0.04) {
      throw new Error(`EquationMorph: the widest form only fits this frame at ${Math.round(fit.s * 1000)} px an em ` +
        `(floor ${Math.round(U * 0.04)}). Split the derivation across beats, or break the form with \\begin{aligned}.`);
    }
    const asc = Math.max(...eqs.map((e) => e.base - e.ink[1])), desc = Math.max(...eqs.map((e) => e.ink[3] - e.base));
    const eqH = (asc + desc) * fit.s;
    const gap = hasLabelLine ? U * 0.05 : 0;
    const groupTop = box.y + Math.max(0, (zoneBot - box.y - (eqH + gap + labelH)) / 2);
    const placed = placeAll(eqs, {x: box.x, y: groupTop, w: box.w, h: eqH}, fit.s * 1000, align);
    emPx = placed.s * 1000;
    labelY = Math.min(zoneBot - labelH, groupTop + eqH + gap);
    const pl = placed.pl;
    // which stage the frame is in
    let stage = 0;
    trans.forEach(([a], i) => { if (t >= a) stage = i + 1; });
    let arrive = 1;                                   // how far the last form's live slot has arrived
    if (t < writeB || nForms === 1) {
      draws = writeState(forms[0], pl[0], clamp01(seg(t, writeA, writeB)), 0.55, 'w');
      arrive = clamp01(seg(t, writeA + (writeB - writeA) * 0.5, writeB));
    } else if (stage === 0) {
      draws = stillState(forms[0], pl[0], 's0_');
    } else {
      const i = stage - 1;
      const [a, b] = trans[i];
      const p = clamp01(seg(t, a, b));
      if (p >= 1) draws = stillState(forms[i + 1], pl[i + 1], `s${i + 1}_`);
      else {
        const m = matchGlyphs(forms[i], forms[i + 1], pl[i], pl[i + 1]);
        draws = transformState(forms[i], pl[i], forms[i + 1], pl[i + 1], m, p);
      }
      shownTex = p >= 0.5 ? steps[i + 1].tex : steps[i].tex;
      arrive = i === nForms - 2 ? clamp01(seg(p, 0.55, 1)) : 0;
    }
    const onLast = nForms === 1 || stage === nForms - 1;
    if (live && onLast) {
      const pv = clamp01(seg(t, liveA, liveB));
      const txt = liveText(live.from, live.to, easeOutCubic(pv));
      draws = draws.concat(liveDraws(eqs[nForms - 1], pl[nForms - 1], live.term, txt).map((d) => ({...d, fill: arrive})));
    }
    if (highlight && onLast) {
      const idx = glyphsOf(eqs[nForms - 1], highlight.term);
      if (!idx.length) throw new Error(`EquationMorph: \`highlight.term\` "${highlight.term}" is not a \\class in the last form.`);
      const hb = unionBox(eqs[nForms - 1], idx, pl[nForms - 1])!;
      const ph = clamp01(seg(t, hlA, hlB));
      if (ph > 0) {
        // the term's glyphs, by the ids the settled form draws them under
        const ids = new Set(idx.map((gi) => {
          const kept = forms[nForms - 1].glyphs.indexOf(eqs[nForms - 1].glyphs[gi]);
          return `s${nForms - 1}_${kept}`;
        }));
        draws = indicate(draws, ids, hb, clamp01(seg(ph, 0, 0.75)));
        const pad = emPx * 0.14;
        frame = frameAround(hb, pad, emPx * 0.16);
        frameP = easeOutCubic(clamp01(seg(ph, 0.05, 0.7)));
        if (highlight.label) leader = [(hb[0] + hb[2]) / 2, hb[3] + pad, (hb[0] + hb[2]) / 2, labelY - U * 0.01];
      }
    }
  }
  const ruleW = Math.max(2, Math.round(emPx * 0.028));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {kicker ? (
        <KineticText k={kick} x={mx} y={zoneTop} color={ACC} read={false} id="kicker"
          motion={{from: {opacity: 0, blur: 0.3}, enter: {by: 'grapheme', at: 0.02, stagger: 0.03, dur: 0.45,
            ease: 'power3', cueKeys: ['kicker'], until: 0.2}}} />
      ) : kick.anchor}
      {title ? (
        <KineticText k={head} x={mx} y={zoneTop + kickH} color={FG} id="title"
          motion={{mask: 'line', from: {ymask: 1.02, blur: 0.03}, enter: {by: 'line', at: 0.04, stagger: 0.12,
            dur: 0.8, ease: 'expo', cueKeys: ['title'], until: 0.24}}} />
      ) : head.anchor}
      {eqs ? (
        <MathLayer draws={draws} tex={shownTex} emPx={emPx} W={W} H={H} ink={FG} accent={ACC} id="equation" />
      ) : null}
      {frame ? (
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <path d={frame} fill="none" stroke={ACC} strokeWidth={ruleW} strokeLinecap="round" {...drawOn(frameP)} />
          {leader && frameP > 0.6 ? (
            <path d={`M${leader[0]} ${leader[1]}L${leader[2]} ${leader[3]}`} stroke={ACC} strokeWidth={ruleW * 0.6}
              strokeLinecap="round" fill="none" {...drawOn(clamp01((frameP - 0.6) / 0.4))} />
          ) : null}
        </svg>
      ) : null}
      {alts.length ? (
        <KineticText k={lab} x={mx} y={labelY} color={DIM} emphColor={ACC} id="label"
          motion={{from: {opacity: 0, y: 0.25}, enter: {by: 'line', at: labelled ? writeA + 0.04 : hlA + 0.02,
            stagger: 0.1, dur: 0.6, ease: 'power3', until: labelled ? writeB : hlB},
            ...(alts.length > 1 ? {swap: {mode: 'flip', first: swapTimes[0], last: swapTimes[swapTimes.length - 1],
              times: [0, ...swapTimes], turn: 0.45, stagger: 0.012,
              cueKeys: [...(labelled ? steps.map((_, i) => `steps.${i}.label`) : []),
                ...(highlight?.label ? ['highlight.label'] : [])]}} : {})}} />
      ) : lab.anchor}
    </AbsoluteFill>
  );
};
export default EquationMorph;
