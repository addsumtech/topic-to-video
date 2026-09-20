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
//
// EVERY LINE THE FILM GAVE IS CUT, OR THE REGISTER SAYS IT CANNOT CUT THEM. It used to take `lines.slice(0, 4)`,
// so a five-line dedication lost its last line — on a stone, usually the name or the date phrase the rest
// leads up to — with nothing anywhere saying so. Four is the clock's limit: the rows are cut 0.11 of the clip
// apart from 0.24, so the fourth is finished (0.75) just as the date starts to land (0.74). A fifth would still
// be cutting while the date lands, and the date is the line the beat turns on — it has to land LAST — and a
// sixth would not finish before the clip ends. So up to four lines draw; a fifth THROWS naming the limit. An
// empty line throws, and so does a stone with no lines and no date: there would be nothing cut in it.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeOutExpo} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {useDNA, mix} from '../runtime/dna';

export const DURATION = 155;

const BG_D0 = '#efe7d8', FG_D0 = '#241d14', DIM_D0 = '#6e6152';
const ACC_D0 = '#9c3b1e', LINE_D0 = '#cdbfa7', SURF_D0 = '#e5dac6';

export const MAX_INSCRIPTION_LINES = 4;

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
  const disp = 'var(--f-display, "Source Serif 4", Georgia, serif)';
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

  // Every line once — the header says why four is the ceiling.
  if (!Array.isArray(LINES) || LINES.length > MAX_INSCRIPTION_LINES) {
    throw new Error(
      `Inscription cuts 0-${MAX_INSCRIPTION_LINES} \`lines\` (got ${Array.isArray(LINES) ? LINES.length : typeof LINES}). ` +
      `The rows are cut one after another and the fourth finishes as the date lands; a fifth would still be ` +
      `cutting when the date should land last. Shorten the inscription to four lines, or move the rest to \`foot\`.`);
  }
  const rows = LINES.map((L, i) => {
    const line = String(L ?? '').trim();
    if (!line) throw new Error(`Inscription: line ${i + 1} is empty. Every row cut into the stone must say something.`);
    return line;
  });
  if (!rows.length && !String(date ?? '').trim()) {
    throw new Error('Inscription needs `lines` or a `date` — with neither, the stone has nothing cut in it.');
  }
  // THE STACK FITS THE FACE IT IS CUT IN — vertically, which is plain arithmetic (every row is its size x
  // 1.25). At the ceiling of four rows plus a date the stack is ~589px on a 16:9 face whose inner chamfer
  // leaves ~541, so the first row sat on the top chamfer and the date on the bottom one, in any language.
  // Rows and date scale down together until the stack clears the chamfer with a margin; anything that
  // already fitted (the demo, every stone of three rows or fewer) is unchanged. Width is still not fitted —
  // see the card: keep the lines short.
  const baseSize = Math.round(W * (rows.length > 2 ? 0.036 : 0.044));
  const baseDate = Math.round(W * 0.070);
  const rowGap = Math.round(W * 0.008), dateGap = Math.round(W * 0.016);
  const hasDate = !!String(date ?? '').trim();
  const room = fh - 2 * H * 0.022 - 2 * H * 0.015;
  // the flex gap also falls between the last row and the date's wrapper, which then adds its own margin
  const fixedH = Math.max(0, rows.length - 1) * rowGap + (hasDate && rows.length ? rowGap + dateGap : 0);
  const scaledH = 1.25 * (rows.length * baseSize + (hasDate ? baseDate : 0));
  const fitK = Math.min(1, Math.max(0.3, (room - fixedH) / Math.max(1, scaledH)));
  const size = Math.round(baseSize * fitK);
  const dateSize = Math.round(baseDate * fitK);

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
        gap: rowGap}}>
        {rows.map((L, i) => {
          const on = easeOutCubic(clamp01(seg(t, 0.24 + i * 0.11, 0.42 + i * 0.11)));
          return <Cut key={i} text={L} s={size} color={mix ? mix(STONE, FG, 0.82) : FG} on={on} weight={600} />;
        })}
        {date ? (
          <div style={{marginTop: rows.length ? dateGap : 0}}>
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
