// SHOT · GazetteerEntry — a NAME defined the way a gazetteer or a dictionary defines one: headword,
// pronunciation, etymology, numbered senses. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: sometimes the word is the evidence. A place whose name means "river crossing", a
// term whose root gives away what it was for, a label that turns out to describe the thing exactly — in
// all of those the beat is not "here is a fact about X", it is "read the word". A dictionary entry is the
// form that argument already has in the world, so the frame borrows it rather than inventing a diagram.
//
// The senses arrive numbered and in order, which is what makes it an argument rather than a caption: the
// last sense is the one the film is claiming.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 150;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7';

export const GazetteerEntry: React.FC<{
  headword?: string;
  pronunciation?: string;       // the bracketed respelling, if the word is worth hearing
  origin?: string;              // the etymology line, set in italic like a real entry
  senses?: string[];            // numbered, in order; the LAST one is the claim
  note?: string;                // a source / cross-reference footer
}> = ({
  headword = 'headword',
  pronunciation = '',
  origin = '',
  senses: SENSES = ['the first sense', 'the sense this film is about'],
  note = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const disp = 'var(--f-display, Georgia, serif)';
  const body = 'var(--f-body, system-ui, sans-serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';

  const left = W * 0.11, right = W * 0.11;
  const top = CONTENT_TOP + H * 0.02;
  const bottom = H - captionBand(W, H) - H * 0.04;

  const head = easeOutCubic(clamp01(seg(t, 0.03, 0.22)));
  const rule = easeOutCubic(clamp01(seg(t, 0.16, 0.34)));
  const orig = easeOutCubic(clamp01(seg(t, 0.24, 0.42)));
  const hair = Math.max(1, Math.round(W * 0.0011));

  const items = SENSES.slice(0, 4);
  // Every vertical measure below is a fraction of the CONTENT ZONE, not of the frame. Using H directly left
  // a 570px hole between the etymology and the first sense at 9:16, because the same 0.30 of a 1920-tall
  // frame is nothing like 0.30 of a 1080-tall one. The zone is what the layout actually has to fill.
  const zone = bottom - top;
  const senseTop = top + zone * 0.34;
  const gap = Math.min(zone * 0.20, Math.max(zone * 0.11, (bottom - senseTop) / Math.max(1, items.length)));

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {/* headword */}
      <div style={{position: 'absolute', left, top, right,
        opacity: head, transform: `translateY(${(1 - head) * 12}px)`,
        font: `700 ${Math.round(W * 0.062)}px/1.02 ${disp}`, letterSpacing: '-0.015em'}}>{headword}</div>

      {/* pronunciation, set on the same baseline family a real entry uses */}
      {pronunciation ? (
        <div style={{position: 'absolute', left, top: top + Math.round(W * 0.070), opacity: orig,
          font: `400 ${Math.round(W * 0.0165)}px/1.3 ${mono}`, color: DIM,
          letterSpacing: '0.04em'}}>{pronunciation}</div>
      ) : null}

      <div style={{position: 'absolute', left, top: top + zone * 0.20, width: (W - left - right) * rule,
        height: hair * 2, background: ACC}} />

      {origin ? (
        <div style={{position: 'absolute', left, top: top + zone * 0.235, right,
          opacity: orig, font: `italic 400 ${Math.round(W * 0.0225)}px/1.4 ${disp}`, color: DIM}}>{origin}</div>
      ) : null}

      {/* the senses, numbered, arriving in order */}
      {items.map((s, i) => {
        const st = 0.40 + i * 0.13;
        const on = easeOutCubic(clamp01(seg(t, st, st + 0.18)));
        const last = i === items.length - 1;
        return (
          <div key={i} style={{position: 'absolute', left, right, top: senseTop + i * gap,
            opacity: on, transform: `translateY(${(1 - on) * 10}px)`,
            display: 'flex', gap: Math.round(W * 0.016), alignItems: 'baseline'}}>
            <div style={{font: `600 ${Math.round(W * 0.0155)}px/1.5 ${mono}`, color: ACC,
              minWidth: Math.round(W * 0.022)}}>{i + 1}.</div>
            <div style={{font: `${last ? 600 : 400} ${Math.round(W * (last ? 0.0265 : 0.023))}px/1.42 ${body}`,
              color: last ? FG : DIM}}>{s}</div>
          </div>
        );
      })}

      {note ? (
        <div style={{position: 'absolute', left, right, top: bottom - Math.round(W * 0.016),
          opacity: easeOutCubic(clamp01(seg(t, 0.80, 0.94))),
          font: `400 ${Math.round(W * 0.0125)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>{note}</div>
      ) : null}

      {/* a hairline down the outer margin — the edge of a printed column */}
      <div style={{position: 'absolute', left: left - W * 0.035, top, width: hair,
        height: (bottom - top) * rule, background: LINE}} />
    </AbsoluteFill>
  );
};
export default GazetteerEntry;
