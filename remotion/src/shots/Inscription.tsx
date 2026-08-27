// SHOT · Inscription — a date cut into stone: incised capitals on a dressed face, with the chisel shadow
// that makes them read as carved rather than typed. Family J (survey / archive).
//
// THE ARGUMENT SHAPE: a moment somebody thought worth COMMEMORATING, as against merely recording. A
// timeline entry says "this happened in 1321"; a foundation stone says "the people who did it wanted it
// remembered". When a beat turns on an act of intent — a founding, a dedication, a treaty, a launch — the
// form the world already keeps that in is cut letters on a prepared face.
//
// Carving is drawn with light, not with a texture image: every glyph is painted twice, once offset down-right
// in a shadow tone and once up-left in a highlight, so the letter reads as a V-cut groove lit from above.
// That is also why the face is a solid tone and not the film's paper: stone is a different material from the
// page it sits on, and saying so is most of the effect.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';

export const DURATION = 155;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7', SURF_D0 = '#e5dac6';

export const Inscription: React.FC<{
  lines?: string[];      // the cut text, one line per row — keep them short, this is stone
  date?: string;         // the line the beat turns on; set larger and given the accent
  foot?: string;         // a small line under the face, in the film's own voice rather than the stone's
  face?: string;         // override the stone tone; defaults to a darker cut of the DNA's surface
}> = ({
  // A demo default must read as a PLACEHOLDER. 'THE FIRST STONE' was lifted straight from the film this
  // register was written during, so the register carried one film's copy as its own and the demo-default
  // check could not tell a film that set the prop from one that forgot.
  lines: LINES = ['THE WORDS CUT HERE', 'AND WHAT THEY MARK'],
  date = '',
  foot = '',
  face = ''} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const FG = dna?.fg ?? FG_D0, DIM = dna?.dim ?? DIM_D0;
  const ACC = dna?.accent ?? ACC_D0, LINE = dna?.line ?? LINE_D0;
  const SURF = dna?.surface ?? SURF_D0;
  const disp = 'var(--f-display, Georgia, serif)';
  const mono = 'var(--f-mono, ui-monospace, monospace)';
  const hair = Math.max(1, Math.round(W * 0.0012));

  // the dressed face: a stone tone derived from the film's own surface, so it belongs to the palette
  const STONE = face || (mix ? mix(SURF, FG, 0.16) : SURF);
  const SHADOW = mix ? mix(STONE, FG, 0.55) : FG;
  const HILITE = mix ? mix(STONE, '#ffffff', 0.55) : '#fff';

  const top = CONTENT_TOP + H * 0.02;
  const bottom = H - captionBand(W, H) - H * 0.06;
  const fw = Math.min(W * 0.62, (bottom - top) * 1.9);
  const fh = bottom - top;
  const fx = (W - fw) / 2;

  const dress = easeOutCubic(clamp01(seg(t, 0.02, 0.22)));     // the face is dressed
  const land = easeOutExpo(clamp01(seg(t, 0.74, 0.92)));
  const cut = Math.max(2, Math.round(W * 0.0016));              // the depth of the groove

  const rows = LINES.slice(0, 4);
  const size = Math.round(W * (rows.length > 2 ? 0.036 : 0.044));
  const dateSize = Math.round(W * 0.070);

  // one line of cut text: a shadow copy, a highlight copy, and the ink on top
  const Cut: React.FC<{text: string; s: number; color: string; on: number; weight: number}> =
    ({text, s, color, on, weight}) => (
      <div style={{position: 'relative', opacity: on, letterSpacing: '0.10em'}}>
        <div style={{position: 'absolute', inset: 0, transform: `translate(${cut}px, ${cut}px)`,
          color: SHADOW, font: `${weight} ${s}px/1.25 ${disp}`}}>{text}</div>
        <div style={{position: 'absolute', inset: 0, transform: `translate(${-cut}px, ${-cut}px)`,
          color: HILITE, font: `${weight} ${s}px/1.25 ${disp}`}}>{text}</div>
        <div style={{position: 'relative', color, font: `${weight} ${s}px/1.25 ${disp}`}}>{text}</div>
      </div>
    );

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? BG_D0, color: FG}}>
      {/* the dressed face, with a chamfered margin the way a real tablet is finished */}
      <div style={{position: 'absolute', left: fx, top, width: fw * dress, height: fh,
        background: STONE, boxShadow: `0 ${Math.round(W*0.004)}px ${Math.round(W*0.014)}px ${mix ? mix(STONE, FG, 0.35) : LINE}33`}} />
      <div style={{position: 'absolute', left: fx + W * 0.012, top: top + H * 0.022,
        width: (fw - W * 0.024) * dress, height: fh - H * 0.044,
        border: `${hair * 2}px solid ${mix ? mix(STONE, FG, 0.22) : LINE}`, boxSizing: 'border-box'}} />

      {/* the cut text, centred on the face */}
      <div style={{position: 'absolute', left: fx, top, width: fw, height: fh,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: Math.round(W * 0.008)}}>
        {rows.map((L, i) => {
          const on = easeOutCubic(clamp01(seg(t, 0.24 + i * 0.11, 0.42 + i * 0.11)));
          return <Cut key={i} text={L} s={size} color={mix ? mix(STONE, FG, 0.82) : FG} on={on} weight={600} />;
        })}
        {date ? (
          <div style={{marginTop: Math.round(W * 0.016)}}>
            <Cut text={date} s={dateSize} color={ACC} on={land} weight={700} />
          </div>
        ) : null}
      </div>

      {foot ? (
        <div style={{position: 'absolute', left: fx, top: bottom + H * 0.020, width: fw, textAlign: 'center',
          opacity: land, font: `400 ${Math.round(W * 0.0135)}px/1.4 ${mono}`, color: DIM,
          letterSpacing: '0.05em'}}>{foot}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default Inscription;
