// SHOT · Command Summon — Raycast/Superhuman language (DARK, on purpose — the command palette's native look).
// A palette flies in, a plain-language command TYPES itself, matches filter live, Return fires — and the
// work spawns as a checklist that ticks off. "One instruction → it plans and runs." Deterministic.
//
// EVERY ROW THE FILM GIVES IS REVEALED AND TICKED, HOWEVER MANY THERE ARE. Every item ticking is this
// register's premise — one instruction, all of it done — and the ticks are not per-item data. But the
// schedule was written for five rows: row i appeared at 0.5 + 0.07·i and ticked at 0.66 + 0.06·i of the clip,
// so from the seventh row on the tick time fell past the end. A film with eight steps ended on six ticked,
// one unticked and one still fading in — a frame that said two of the film's steps were not done, chosen by
// nothing but their position in the list. The spacing now shrinks with the count so the last row lands and
// ticks inside the clip (five rows keep their exact original timing). And the palette has a height: each
// row is 78px, and the whole palette box — every row's slot is laid out before Return, invisible — has to
// end above the caption band, which is six rows on a 1080-tall frame. More than that, or none, throws.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01, useAnimSpan, ENTRY_T, ReducedMotionContext} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {contentBottom, fitTextPx} from '../runtime/layout';
import {caretOn, framesBetween} from '../runtime/gesture';
import {useGlide} from '../runtime/glide';

export const DURATION = 165; // 5.5s

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  '↵ run',
];

const ACCENT0 = '#6E8BFF';
const DEFAULT_ROWS = ['Plan the deck outline', 'Pull the Q3 numbers', 'Design 24 slides', 'Write the narrative', 'Export to your folder'];

export const CommandSummon: React.FC<{command?: string; items?: string[]}> = ({
  command = 'Build the Q3 board deck from ~/finance', items: ROWS = DEFAULT_ROWS} = {}) => {
  const t = useT();
  const glide = useGlide();
  const dna = useDNA(); const ACCENT = dna?.accent ?? ACCENT0;
  const {width: W, height: H} = useVideoConfig();
  // palette top 210 + input row (34px padding x2 + 46px type) + list padding 36, then 78px a row (34px box
  // with its 2px border each side, 20px padding above and below)
  const ROW_H = 78, PAL_HEAD = 210 + 114 + 36;
  const maxRows = Math.floor((contentBottom(W, H) - PAL_HEAD) / ROW_H);
  if (!Array.isArray(ROWS) || ROWS.length < 1) {
    throw new Error('CommandSummon needs at least one row in `items` — the command has to spawn something to run.');
  }
  if (ROWS.length > maxRows) {
    throw new Error(`CommandSummon fits at most ${maxRows} \`items\` on a ${W}x${H} frame (got ${ROWS.length}): each row is ` +
      `${ROW_H}px and the palette has to end above the caption band. Group the steps, or cast a list register.`);
  }
  // the reveal and tick spacing shrink with the count, so the last row is revealed by 0.96 and ticked by 0.94
  const n = ROWS.length;
  const stepR = Math.min(0.07, 0.28 / Math.max(1, n - 1)), stepT = Math.min(0.06, 0.28 / Math.max(1, n - 1));
  // phases: palette in (0-.12) · type command (.12-.42) · Return flash (.46) · checklist spawns+ticks (.5-1)
  const inP = easeOutBack(seg(t, 0, 0.14));
  const typed = Math.floor(command.length * easeOutCubic(seg(t, 0.14, 0.44)));
  const fired = t > 0.46;
  const flash = fired ? Math.max(0, 1 - (t - 0.46) / 0.06) : 0;
  // The caret runs on FRAMES (runtime/gesture): solid while the command types, then the system's 16-frame
  // phases. It used to be `Math.floor(t * 60) % 2` — a rate tied to the beat's length, measured at 5.6
  // flashes a second on a 5-second beat, blinking mid-word.
  const span = useAnimSpan();
  const reduced = React.useContext(ReducedMotionContext);
  const TYPED_BY = 0.44;
  const caretShown = t < 0.46 && caretOn(t < TYPED_BY ? null : framesBetween(TYPED_BY, t, span, ENTRY_T), reduced);
  const palY = lerp(60, 0, inP) + (fired ? -lerp(0, 40, easeOutCubic(seg(t, 0.46, 0.6))) : 0);
  const palScale = fired ? lerp(1, 0.94, easeOutCubic(seg(t, 0.46, 0.62))) : 1;
  // A PALETTE WIDER THAN THE FRAME. 1180 was the width of a comfortable command palette on a 1920 frame;
  // every other aspect this renderer offers is 1080 wide, so `PX` came out NEGATIVE and the palette hung
  // off both edges before a single character was typed into it. Clamped to the frame, and the copy inside
  // is then fitted to the width the palette really has — the command line is `white-space: pre`, so it
  // cannot wrap out of an overflow, and a Chinese command ran 89px past the edge.
  const PW = Math.min(1180, Math.round(W * 0.92)), PX = Math.round((W - PW) / 2);
  const CMD_PADX = 40, ROW_PADX = 24, ICON = 34 + 22;
  const cmdPx = fitTextPx(command, PW - CMD_PADX * 2 - ICON, 46, {usable: 1});
  const rowPx = ROWS.reduce((px, r) => Math.min(px, fitTextPx(r, PW - 40 - ROW_PADX * 2 - 54 - 120, 38, {usable: 1})), 38);
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 100% at 50% 22%, #141a26, #090c12 60%)'}}>
      {/* soft accent glow behind the palette */}
      <div style={{position: 'absolute', left: W / 2 - 420, top: 150, width: 840, height: 520,
        background: `radial-gradient(closest-side, ${ACCENT}22, transparent)`, filter: 'blur(30px)'}} />
      {/* THE PALETTE — it travels by its own `top` (sliding in, then the Return bounce) and scales, both of
          which Skia rounds the same way it rounds a translate; the unlock carries every line inside it (the
          command's caret, the row text, the ↵ run badge) for as long as either motion can still be running */}
      {/* the palette rises by a TRANSLATE: by its layout top it was rounded to whole pixels before anything was
          drawn, and stepped whatever unlocked it (it rests on whole pixels, 0 and -40, as before) */}
      <div style={{position: 'absolute', left: PX, top: 210, width: PW, opacity: clamp01(inP),
        transform: glide(`translateY(${palY}px) scale(${palScale})`, inP !== 1 || (fired && t < 0.62)), transformOrigin: '50% 0', background: 'rgba(20,25,35,0.92)',
        border: '1px solid #2a3346', borderRadius: 20, boxShadow: '0 50px 120px rgba(0,0,0,.6)', backdropFilter: 'blur(20px)'}}>
        {/* input row */}
        <div style={{display: 'flex', alignItems: 'center', gap: 22, padding: `34px ${CMD_PADX}px`, borderBottom: '1px solid #232c3d'}}>
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke={ACCENT} strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="21" y2="21" /></svg>
          <div style={{font: `500 ${cmdPx}px/1 var(--f-body, Inter,system-ui,sans-serif)`, color: '#eef2f8', whiteSpace: 'pre'}}>
            {command.slice(0, typed)}<span style={{opacity: caretShown ? 1 : 0, color: ACCENT}}>|</span>
          </div>
        </div>
        {/* matched actions / checklist that spawns after Return */}
        <div style={{padding: '18px 20px'}}>
          {ROWS.map((r, i) => {
            const rev = fired ? easeOutBack(seg(t, 0.5 + i * stepR, 0.5 + i * stepR + 0.18)) : (i === 0 ? 1 : 0.0);
            const tick = fired && t > 0.66 + i * stepT;
            return (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, padding: `20px ${ROW_PADX}px`, borderRadius: 12,
                opacity: clamp01(rev), transform: glide(`translateX(${lerp(-20, 0, clamp01(rev))}px)`, rev !== 1),
                background: (!fired && i === 0) ? `${ACCENT}1e` : 'transparent'}}>
                <div style={{width: 34, height: 34, borderRadius: 9, border: `2px solid ${tick ? '#59d98b' : '#3a475e'}`,
                  background: tick ? '#59d98b' : 'transparent', color: '#0b0f17', font: '700 22px/30px var(--f-body, Inter)', textAlign: 'center'}}>{tick ? '✓' : ''}</div>
                <div style={{font: `500 ${rowPx}px/1 var(--f-body, Inter,system-ui,sans-serif)`, color: tick ? '#8f9bb0' : '#dfe6f0'}}>{r}</div>
                {i === 0 && !fired && <div style={{marginLeft: 'auto', padding: '8px 16px', borderRadius: 8, background: '#2a3346',
                  font: '700 26px/1 var(--f-body, Inter)', color: ACCENT}}>↵ run</div>}
              </div>
            );
          })}
        </div>
      </div>
      {/* Return flash */}
      {flash > 0 && <AbsoluteFill style={{background: '#fff', opacity: 0.14 * flash}} />}
    </AbsoluteFill>
  );
};
export default CommandSummon;
