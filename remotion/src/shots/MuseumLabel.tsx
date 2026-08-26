// SHOT · MuseumLabel — a real object beside its museum label: name, date, provenance, accession, and a
// short body. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: "the thing itself is the evidence." A photograph dropped into a slide is an
// illustration; a photograph beside a catalogue label is a CITATION — the label says what it is, when it
// is from, and where it came from, which is exactly what a viewer needs before they will accept a picture
// as proof. It is also the honest home for the credit line a license-clean image requires: in this form
// the attribution is not a legal footnote bolted on, it is part of the idiom.
//
// The image is optional. Without `src` the label stands alone against a ruled panel, which is still a
// legitimate reading — a catalogue entry for something not shown.

import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 165;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';

export const MuseumLabel: React.FC<{
  src?: string;             // a real image, resolved through the film's public dir
  object?: string;          // what it is
  date?: string;
  provenance?: string;      // where it is / where it came from
  accession?: string;       // the catalogue number — a mono line, like a real label
  body?: string;            // one short paragraph: what the viewer should notice
  credit?: string;          // the licence line the image requires
}> = ({
  src = '',
  object = 'the object',
  date = '',
  provenance = '',
  accession = '',
  body = '',
  credit = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Georgia, serif)';
  const bodyF = 'var(--f-body, system-ui, sans-serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  const top = CONTENT_TOP + H * 0.01;
  const bottom = H - captionBand(W, H) - H * 0.05;
  const portrait = H > W;

  // landscape: image left, label right. portrait: image above, label below — the shot must STACK.
  const gap = W * 0.035;
  const imgW = portrait ? W * 0.78 : W * 0.42;
  const imgH = portrait ? (bottom - top) * 0.52 : (bottom - top);
  const imgX = portrait ? (W - imgW) / 2 : W * 0.07;
  const imgY = top;
  const labX = portrait ? W * 0.11 : imgX + imgW + gap;
  const labY = portrait ? imgY + imgH + H * 0.035 : top + H * 0.03;
  const labW = portrait ? W * 0.78 : W - labX - W * 0.07;

  const plate = easeOutCubic(clamp01(seg(t, 0.03, 0.26)));
  const rule = easeOutCubic(clamp01(seg(t, 0.22, 0.40)));
  const lines = easeOutCubic(clamp01(seg(t, 0.32, 0.62)));
  const para = easeOutExpo(clamp01(seg(t, 0.56, 0.84)));

  const Row: React.FC<{text?: string; at: number; face: string; size: number; color: string;
    spacing?: string}> = ({text, at, face, size, color, spacing}) => {
    if (!text) return null;
    const on = easeOutCubic(clamp01(seg(t, at, at + 0.14)));
    return (
      <div style={{opacity: on, transform: `translateY(${(1 - on) * 6}px)`,
        font: `${size >= 0.030 ? 700 : 500} ${Math.round(W * size)}px/1.3 ${face}`, color,
        letterSpacing: spacing, marginBottom: Math.round(W * 0.007)}}>{text}</div>
    );
  };

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {/* the object, in a hairline mount */}
      <div style={{position: 'absolute', left: imgX, top: imgY, width: imgW, height: imgH,
        opacity: plate, overflow: 'hidden',
        border: `${hair * 2}px solid ${LINE}`, background: dna?.surface ?? '#e5dac6'}}>
        {src ? (
          <Img src={staticFile(src)}
            style={{width: '100%', height: '100%', objectFit: 'cover',
              transform: `scale(${1.04 - 0.04 * plate})`}} />
        ) : null}
      </div>

      {/* the label */}
      <div style={{position: 'absolute', left: labX, top: labY, width: labW}}>
        <div style={{width: labW * rule, height: hair * 2, background: ACC,
          marginBottom: Math.round(W * 0.014)}} />
        <Row text={object} at={0.30} face={disp} size={0.032} color={FG} />
        <Row text={date} at={0.38} face={mono} size={0.0155} color={ACC} spacing="0.08em" />
        <Row text={provenance} at={0.44} face={bodyF} size={0.0165} color={DIM} />
        {accession ? (
          <div style={{opacity: lines, font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
            letterSpacing: '0.06em', marginTop: Math.round(W * 0.004)}}>{accession}</div>
        ) : null}
        {body ? (
          <div style={{opacity: para, marginTop: Math.round(W * 0.018),
            paddingTop: Math.round(W * 0.014), borderTop: `${hair}px solid ${LINE}`,
            font: `400 ${Math.round(W * 0.0185)}px/1.5 ${bodyF}`, color: FG}}>{body}</div>
        ) : null}
      </div>

      {/* the licence line, in the label's own idiom rather than bolted on */}
      {credit ? (
        <div style={{position: 'absolute', left: imgX, top: portrait ? imgY + imgH + H * 0.008 : bottom + H * 0.012,
          width: imgW, opacity: para,
          font: `400 ${Math.round(W * 0.0105)}px/1.35 ${mono}`, color: DIM,
          letterSpacing: '0.03em'}}>{credit}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default MuseumLabel;
