// SHOT · ASCII Field — generative/terminal language (a 2026 procedural trend): a live monospace character
// field flickers, a scan-wave sweeps and BRIGHTENS the glyphs it crosses, and a clean message decodes out of
// the noise. AMBER terminal phosphor (distinct from CodeRain's green Matrix rain) — this DECODES in place,
// CodeRain FALLS. Code-native. Deterministic (each glyph = fn of cell + frame).
//
// EVERY CHARACTER OF THE MESSAGE RESOLVES. Character i's opacity used to be `(decode - 0.12 * i) / 0.3` — a
// fixed per-character step against a decode that tops out at 1 — so only the first six characters ever reached
// full strength: the eighth peaked near half, the ninth stayed faint and the tenth onward never appeared at all.
// And the fit sized the box for the WHOLE string, so what did resolve sat off-centre beside an invisible tail.
// A film whose verdict was "构建成功，全部测试通过" showed its first six glyphs. The step is now laid out for
// the message — 0.12 stays the upper bound, so a short word keeps its exact cascade — so the last character
// reaches full strength exactly when the decode completes (t = 0.78, before the settled frame). Past
// MAX_ASCII_CHARS the message is a sentence, not a word resolving out of noise, and the register refuses.

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic, clamp01, hash01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {CONTENT_TOP, contentBottom, fitBlockPx, monoFit} from '../runtime/layout';

export const DURATION = 150; // 5s
// @dark-world: an amber PHOSPHOR field. A glyph here is not drawn in a colour, it is drawn by how much it
// GLOWS — `op = base + near * 0.9` — and the scan-wave's single action is to brighten the rows it crosses.
// Brightness is only legible against a darker field, so on a warm-white film the whole register measured a
// median 1.05:1 with 100% of its marks under 3:1 (scripts/ink_contrast_qa.py): the noise, the sweep and the
// message decoding out of them all went at once. Inverting it would make the sweep DARKEN what it touches,
// which is not a screen coming alive. So it keeps its own tube-dark ground.
const OWN_NIGHT = '#140b03';
const CH = '01</>{}[]#*+=~.:$%&ABCDEFXYZ01'.split('');
const DEFAULT_MSG = 'DONE.';
export const MAX_ASCII_CHARS = 32;
// Character i resolves over [i * step, i * step + CHAR_RISE] of the decode; DECODE_STEP is the original gap and
// only an upper bound, so the last character's window always closes at decode = 1.
const DECODE_STEP = 0.12, CHAR_RISE = 0.3;

export const AsciiField: React.FC<{message?: string}> = ({message: MSG = DEFAULT_MSG} = {}) => {
  const chars = [...String(MSG ?? '')];
  if (!String(MSG ?? '').trim() || chars.length > MAX_ASCII_CHARS) {
    throw new Error(
      `AsciiField needs a \`message\` of 1-${MAX_ASCII_CHARS} characters (got ` +
      `${String(MSG ?? '').trim() ? chars.length : 'no visible character'}). It is ONE short word or phrase ` +
      'decoding out of the noise, character by character; a sentence belongs in a headline register.');
  }
  const charStep = chars.length > 1 ? Math.min(DECODE_STEP, (1 - CHAR_RISE) / (chars.length - 1)) : DECODE_STEP;
  const frame = useCurrentFrame();
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);
  // THE FIELD STOPS WHERE THE CAPTION STARTS. It used to run to the bottom of the frame, so at 9:16 the
  // type-safety gate found 224 glyphs sitting inside the caption band — the burned subtitle printed over a
  // moving field of amber characters. The glyphs are noise, not copy, but the viewer still has to read a
  // sentence through them, and every other register in this library reserves that strip. It is the shot's
  // own ground down there now, which is exactly what the caption is drawn on.
  const bottom = contentBottom(W, H);
  // Sized off the frame's short side rather than in bare pixels, so a cell is a cell at any aspect.
  const cw = Math.max(8, Math.round(U * 0.0315)), chh = Math.max(10, Math.round(U * 0.037));
  // WHOLE ROWS ONLY. Ceil left the last row straddling the boundary and the svg clipped it through the
  // middle of the glyphs — a row of half-characters along the band, which reads as a broken render rather
  // than as an edge. The field ends on a row it can draw.
  const cols = Math.ceil(W / cw), rows = Math.max(1, Math.floor(bottom / chh));
  const fieldH = rows * chh;
  const scanY = (t * 1.3 - 0.15) * rows; // the sweep row
  const cells = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const flick = Math.floor(hash01(r * 91.7 + c * 13.1 + Math.floor(frame / 3)) * CH.length);
    const near = Math.max(0, 1 - Math.abs(r - scanY) / 3); // brighten near the scan-wave
    const base = 0.10 + 0.12 * hash01(r * 3.1 + c);
    const op = clamp01(base + near * 0.9);
    const col = near > 0.4 ? '#ffc861' : '#7a531c';   // AMBER phosphor (distinct from CodeRain's green rain)
    cells.push(<text key={`${r}-${c}`} x={c * cw + 6} y={r * chh + Math.round(chh * 0.75)} fill={col} fillOpacity={op}
      style={{font: `600 ${Math.round(U * 0.0278)}px/1 var(--f-mono, "JetBrains Mono", ui-monospace, monospace)`}}>{CH[flick]}</text>);
  }
  const decode = easeOutCubic(seg(t, 0.5, 0.78));
  // THE MESSAGE IS FITTED TO THE FIELD IT DECODES IN. `U * 0.194` is 210px on every frame this register
  // offers, which holds 'DONE.' and five Han glyphs — and a real Chinese message is longer than that. It
  // wrapped to four lines inside a box centred on the field, so it grew out of BOTH ends and the gate read
  // the top: glyphs cut off by 369px at 1:1. The face is MONOSPACE, where a Han glyph is two cells, so the
  // fit is told that rather than the proportional default it would otherwise assume.
  // `MSG_W` is passed to the fitter AND set on the box, so the measure the fit wrapped in is the measure
  // the browser wraps in — the two disagreeing is what put KineticManifesto's last line in the band.
  // AND IT IS FITTED TO THE HEIGHT IT CAN HAVE WITHOUT CROSSING THE TITLE BAND. The box is centred on the
  // field, and the field starts at the top of the frame — so a block fitted to the field's full height put its
  // first line at y = 40 on a 16:9 frame, inside the band every register keeps clear. That was invisible while
  // only six characters ever resolved; with every character drawn it is the first line a viewer reads. The
  // room is the band ABOUT THE FIELD'S CENTRE that stays inside [CONTENT_TOP, field bottom], so the centre (and
  // every short message, which already fitted) does not move.
  const fieldMid = fieldH / 2;
  const msgRoomH = 2 * Math.max(0, Math.min(fieldMid - CONTENT_TOP, fieldH - fieldMid));
  const MSG_W = Math.round(W * 0.86);
  const msgPx = fitBlockPx(MSG, MSG_W, msgRoomH * 0.92, Math.round(U * 0.194),
    {usable: 1, leading: 1, min: 28, ...monoFit()});
  // the film's ground while the film's ground is dark (all eight presets), this register's own night when it
  // is not. The branch is on what `darkGround` RETURNED, so a dark film grounded on exactly this colour still
  // gets its own `bgGrad` treatment rather than ours.
  const night = darkGround(dna?.bg, OWN_NIGHT);
  const ground = night === dna?.bg ? (dna?.bgGrad ?? night) : night;
  return (
    <AbsoluteFill style={{background: ground}}>
      <svg width={W} height={fieldH} style={{position: 'absolute', left: 0, top: 0}}>{cells}</svg>
      {/* the decoded message resolving out of the noise */}
      {/* the message centres in the CONTENT zone, with the field — centred in the whole frame it would sit
          low of the field's own middle, and lower still at 9:16 where the reserved band is deepest */}
      <AbsoluteFill style={{top: 0, height: fieldH, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{position: 'relative', maxWidth: MSG_W, textAlign: 'center', font: `900 ${msgPx}px/1 var(--f-mono, "JetBrains Mono", monospace)`, color: '#ffe6b0',
          letterSpacing: '0.04em', opacity: decode, textShadow: '0 0 40px rgba(255,190,90,.5)'}}>
          {chars.map((ch, i) => <span key={i} style={{opacity: clamp01((decode - i * charStep) / CHAR_RISE)}}>{ch}</span>)}
        </div>
      </AbsoluteFill>
      {/* scanline glow */}
      <div style={{position: 'absolute', left: 0, right: 0, top: (scanY / rows) * fieldH - 2, height: 4, background: 'rgba(120,255,180,.5)', filter: 'blur(3px)'}} />
    </AbsoluteFill>
  );
};
export default AsciiField;
