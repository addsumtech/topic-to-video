// SHOT · Word Dust — one word comes apart into its own dust and the SAME dust settles into another word: the
// claim is conservation — this became that, nothing added, nothing lost. With no `from`, a loose cloud condenses
// into the word: many small things gathering into one.
//
// Every particle is taken from the word's own pixels (runtime/particlesDom: the word set on a canvas in the film's
// display face, sampled every few pixels) and lands exactly on the next word's (runtime/particles: two sets made
// one size and paired in reading order, so the left of one word flows to the left of the next). The settled words
// are REAL TEXT in the same face at the size the canvas chose, centred as the canvas centred them: drawn as the
// canvas pictures they were in register to the pixel, but the type audits (text_safe_qa, cjk_type_qa) cannot see
// type inside a picture and reported the register as having drawn nothing.
//
// Peer: video-shotcraft's grain-dissolve (a line boils into grain, the cloud condenses into a larger glowing word)
// — reviewed 2026-11-02. Their version is a title effect; here the two words are the film's, and the move says what
// happened between them.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {leading} from '../runtime/cjkType';
import {pair, particleAt, type Pt} from '../runtime/particles';
import {useTextMark, Dust} from '../runtime/particlesDom';

export const DURATION = 180; // 6 s

const h01 = (i: number, s: number) => {
  const x = Math.sin((i + 1) * 12.9898 + s * 78.233) * 43758.5453;
  return x - Math.floor(x);
};

/** The settled word: the canvas's text, at the canvas's size, centred in the same box. */
const Word: React.FC<{text: string; px: number; x: number; y: number; w: number; h: number; ink: string; face: string;
  opacity: number; left?: boolean}> = ({text, px, x, y, w, h, ink, face, opacity, left}) => (
  <div style={{position: 'absolute', left: x, top: y, width: w, height: h, display: 'flex', alignItems: 'center',
    justifyContent: left ? 'flex-start' : 'center', whiteSpace: 'nowrap', color: ink, opacity, font: `800 ${px}px/1 ${face}`}}>{text}</div>
);

export const WordDust: React.FC<{from?: string; to?: string; note?: string; place?: 'centre' | 'left'}> = ({
  from = 'Demo before', to = 'Demo after', note = '', place = 'centre'} = {}) => {
  // `place` is a COMPOSITION choice the film makes against its neighbours (text_safe_qa names a film whose titles
  // all sit in one place): the words centred, or set from the left edge of the content column
  const left = place === 'left';
  if (!String(to ?? '').trim()) throw new Error('WordDust needs `to`: the word the dust settles into');
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  const BG = dna?.bg ?? '#07090d', FG = dna?.fg ?? '#f2f4f8', DIM = dna?.dim ?? '#8a93a4';
  const ACC = dna?.accent ?? '#7cc4ff';
  const FACE = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';
  const BODY = 'var(--f-body, Inter, system-ui, sans-serif)';

  const top = Math.max(CONTENT_TOP, Math.round(U * 0.08)), bottom = contentBottom(W, H);
  const boxW = Math.round(W * 0.86), boxH = Math.round(Math.min(U * 0.3, (bottom - top) * 0.5));
  const boxX = left ? Math.round(W * 0.07) : Math.round((W - boxW) / 2), boxY = Math.round(top + (bottom - top) * 0.42 - boxH / 2);
  const step = Math.max(4, Math.round(U * 0.0048));
  const A = useTextMark(from ? String(from) : '', FACE, boxW, boxH, {step, ink: FG, align: left ? 'left' : 'center'});
  const B = useTextMark(String(to), FACE, boxW, boxH, {step, ink: ACC, align: left ? 'left' : 'center'});
  if (!B || (from && !A)) return <AbsoluteFill style={{background: BG}} />;

  // with no first word, the dust starts as a loose cloud over the whole zone
  const cloud: Pt[] = from ? [] : B.pts.map((_, i) => ({x: (h01(i, 1) * 1.2 - 0.1) * boxW,
    y: (h01(i, 2) * 2.4 - 0.7) * boxH}));
  const pairs = pair(from ? (A as {pts: Pt[]}).pts : cloud, B.pts, 3);

  const [aOn, aOff] = from ? [0.06, 0.3] : [0, 0];          // the first word, solid
  const [f0, f1] = from ? [0.3, 0.7] : [0.08, 0.6];          // the flow
  const flow = seg(t, f0, f1);
  const solidA = from ? clamp01(seg(t, aOn, aOn + 0.06)) * (1 - clamp01(seg(t, aOff, aOff + 0.04))) : 0;
  const solidB = clamp01(seg(t, f1 - 0.02, f1 + 0.08));
  const dustOn = from ? clamp01(seg(t, aOff - 0.01, aOff + 0.03)) : clamp01(seg(t, 0.02, 0.1));
  const dust = dustOn * (1 - solidB);
  const pts = dust > 0 ? pairs.map((q, i) => particleAt(q, i, flow, {scatter: boxH * 0.9, stagger: 0.25})) : [];
  const r = step * 0.42;
  // @positional: every ninth grain a step lighter — sparkle in the dust, not a status of anything the film named
  const col = (i: number) => (i % 9 === 0 ? mix(FG, ACC, 0.3) : mix(FG, ACC, clamp01(flow * 1.2)));
  const noteOn = easeOutCubic(clamp01(seg(t, f1 + 0.06, f1 + 0.16)));
  const notePx = note ? Math.max(Math.round(U * 0.03), fitTextPx(note, W * 0.7, Math.round(U * 0.038))) : 0;

  return (
    <AbsoluteFill style={{background: dna ? `radial-gradient(90% 80% at 50% 45%, ${mix(BG, ACC, 0.08)}, ${BG} 70%)` : BG}}>
      {A && solidA > 0 ? <Word text={String(from)} px={A.px} x={boxX} y={boxY} w={A.w} h={A.h} ink={FG} face={FACE}
        opacity={solidA} left={left} /> : null}
      {pts.length ? <Dust pts={pts} r={r} color={col} glow={2.5 * Math.sin(Math.PI * flow)}
        style={{left: boxX, top: boxY, opacity: dust}} /> : null}
      {solidB > 0 ? <Word text={String(to)} px={B.px} x={boxX} y={boxY} w={B.w} h={B.h} ink={ACC} face={FACE}
        opacity={solidB} left={left} /> : null}
      {note ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: boxY + boxH + Math.round(U * 0.02), textAlign: left ? 'left' : 'center', paddingLeft: left ? boxX : 0,
          opacity: noteOn, color: mix(DIM, FG, 0.4), font: `500 ${notePx}px/${leading(note, 1.3)} ${BODY}`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default WordDust;
