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
import {CONTENT_TOP, contentBottom, fitTextPx, wrapLines} from '../runtime/layout';
import {LitStage, softShadow, rgba} from '../runtime/craftStage';
import {typePx, typeStyle, TextReveal} from '../runtime/craftType';
import {caretOn, framesBetween} from '../runtime/gesture';
import {useGlide} from '../runtime/glide';
import type {SoundDecl} from '../runtime/sound';

export const DURATION = 165; // 5.5s
// a key on each character's frame as the command types (the typed count is floor(n * easeOutCubic(seg(t, 0.14, 0.44)))),
// then the press that runs it, as the palette fires
export const SOUNDS: readonly SoundDecl[] = [
  {kind: 'key', type: 'command', at: 0.14, to: 0.44, ease: 'out-cubic'},
  {kind: 'click', at: 0.45, gain: 0.7},
] as const;

// This register's own vocabulary — the labels that belong to the FORM the way an axis belongs to a
// graph, not sample copy about a topic. Declared so onscreen_text_qa can tell them apart from the
// demo furniture that used to print on every film (WORKBUDDY, DASHBOARD, x:960 y:540).
export const INTRINSIC_TEXT = [
  '↵ run',
];

const ACCENT0 = '#6E8BFF';
const DEFAULT_ROWS = ['Plan the deck outline', 'Pull the Q3 numbers', 'Design 24 slides', 'Write the narrative', 'Export to your folder'];

export const CommandSummon: React.FC<{command?: string; items?: string[];
  /** optional: a display line set beside the palette (the UI + headline composition, craft-standard §Film); without it
   *  the palette is centred alone */
  title?: string; titleAccent?: string[];
  /** optional: what the run produced — a file card slides out of the palette once every row has ticked (the payoff:
   *  the instruction, the steps, then the thing) */
  result?: {name: string; note?: string}}> = ({
  command = 'Build the Q3 board deck from ~/finance', items: ROWS = DEFAULT_ROWS, title, titleAccent = [], result} = {}) => {
  const t = useT();
  const glide = useGlide();
  const dna = useDNA(); const ACCENT = dna?.accent ?? ACCENT0;
  const {width: W, height: H} = useVideoConfig();
  // A PALETTE WIDER THAN THE FRAME. 1180 was the width of a comfortable command palette on a 1920 frame;
  // every other aspect this renderer offers is 1080 wide, so `PX` came out NEGATIVE and the palette hung
  // off both edges before a single character was typed into it. Clamped to the frame, and the copy inside
  // is then fitted to the width the palette really has.
  //
  // THE FIT HAS A FLOOR. The command (46 px) and the rows (38 px) were fitted DOWN to whatever the palette's
  // width allowed, with no lower bound. Both are copy: they stop at the label floor (30 px at 1080) and WRAP from
  // there — the command line is `pre-wrap` with its height reserved up front (so typing never moves the rows
  // below it), and `PAL_HEAD` below counts the extra lines against the caption band.
  const paired = !!title && W > H;
  const PW = paired ? Math.round(W * 0.5) : Math.min(1180, Math.round(W * 0.92));
  const PX = paired ? Math.round(W * 0.07) : Math.round((W - PW) / 2);
  const CMD_PADX = 40, ROW_PADX = 24, ICON = 34 + 22;
  const FLOOR = Math.round(Math.min(W, H) * 0.0278);
  const cmdPx = Math.max(FLOOR, fitTextPx(command, PW - CMD_PADX * 2 - ICON, 46, {usable: 1}));
  const cmdLines = wrapLines(command, cmdPx, PW - CMD_PADX * 2 - ICON);
  const cmdH = cmdLines > 1 ? Math.ceil(cmdLines * cmdPx * 1.12) : 46;
  // palette top 210 + input row (34px padding x2 + the command's own height, 46px for one line) + list padding 36,
  // then 78px a row (the 44px tick box with its 2px border each side, 17px padding above and below)
  const ROW_H = 78, TICK_BOX = 44, PAL_HEAD = 210 + 68 + cmdH + 36;
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
  // THE PALETTE STANDS IN THE MIDDLE OF THE CONTENT ZONE on its final height (craft standard: the subject uses the
  // frame — pinned at top 210 it left the lower 40 % of every beat empty). The row-count limit above still reads the
  // original top, so no film's board stops fitting.
  const palH = 68 + cmdH + 36 + n * ROW_H;
  const RES_H = result ? 132 : 0; // the result card lands UNDER the palette; the two are centred as one group
  const palTop = Math.max(CONTENT_TOP, Math.round(CONTENT_TOP + (contentBottom(W, H) - CONTENT_TOP - palH - RES_H) / 2));
  const palY = lerp(60, 0, inP);
  const palScale = 1;
  const sweep = fired ? clamp01((t - 0.48) / 0.16) : 0;
  const rowPx = ROWS.reduce((px, r) => Math.min(px, fitTextPx(r, PW - 40 - ROW_PADX * 2 - (TICK_BOX + 20) - 130, 38, {usable: 1})), 38);
  const rowFit = Math.max(FLOOR, rowPx);
  return (
    <AbsoluteFill style={{background: dna?.bg ?? '#090c12'}}>
      {/* THE STAGE: the key light falls on the palette (runtime/craftStage); the original radial ground stays the
          un-themed film's colours: radial-gradient(120% 100% at 50% 22%, #141a26, #090c12 60%) */}
      <LitStage ground={dna?.bg ?? '#090c12'} light={ACCENT} fill={dna?.accent2 ?? null}
        keyAt={{x: (PX + PW / 2) / W, y: (palTop + palH * 0.35) / H}} intensity={1.15} />
      {/* THE PALETTE — it travels by its own `top` (sliding in, then the Return bounce) and scales, both of
          which Skia rounds the same way it rounds a translate; the unlock carries every line inside it (the
          command's caret, the row text, the ↵ run badge) for as long as either motion can still be running */}
      {/* the palette rises by a TRANSLATE: by its layout top it was rounded to whole pixels before anything was
          drawn, and stepped whatever unlocked it (it rests on whole pixels, 0 and -40, as before) */}
      {/* NO BACKDROP-FILTER. The palette was frosted (`backdropFilter: blur(20px)`), and the browser draws a backdrop-
          filter's content as a layer of its own, which the unlock does not reach: the command trembled 0.41px RMS as
          the palette scaled, 0 without it (a one-beat film of the topic-to-video promo, jitter_qa, 2026-11-04). The
          fill is 92% opaque, so the blur behind it was all but invisible anyway. */}
      <div style={{position: 'absolute', left: PX, top: palTop, width: PW, opacity: clamp01(inP), overflow: 'hidden',
        transform: glide(`translateY(${palY}px) scale(${palScale})`, true), transformOrigin: '50% 0',
        background: 'linear-gradient(180deg, rgba(30,36,50,0.96), rgba(20,25,35,0.96) 40%)',
        border: '1px solid #2a3346', borderRadius: 22,
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px ${rgba(ACCENT, 0.18)}, 0 0 80px ${rgba(ACCENT, 0.16)}, ${softShadow(3, '#000000')}`}}>
        {/* one pass of light across the palette as the command runs (once, on the hero) */}
        {sweep > 0 && sweep < 1 ? <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', background:
          `linear-gradient(115deg, transparent ${-40 + sweep * 180 - 16}%, rgba(255,255,255,0.10) ${-40 + sweep * 180}%, transparent ${-40 + sweep * 180 + 16}%)`}} /> : null}
        {/* input row */}
        <div style={{display: 'flex', alignItems: 'center', gap: 22, padding: `34px ${CMD_PADX}px`, borderBottom: '1px solid #232c3d'}}>
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke={ACCENT} strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="21" y2="21" /></svg>
          <div style={{font: `500 ${cmdPx}px/${cmdLines > 1 ? 1.12 : 1} var(--f-body, Inter,system-ui,sans-serif)`, color: '#eef2f8', whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere', minWidth: 0, minHeight: cmdH}}>
            {command.slice(0, typed)}<span style={{opacity: caretShown ? 1 : 0, color: ACCENT}}>|</span>
          </div>
        </div>
        {/* matched actions / checklist that spawns after Return */}
        <div style={{padding: '18px 20px'}}>
          {ROWS.map((r, i) => {
            const rev = fired ? easeOutBack(seg(t, 0.5 + i * stepR, 0.5 + i * stepR + 0.18)) : (i === 0 ? 1 : 0.0);
            const tick = fired && t > 0.66 + i * stepT;
            return (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, padding: `17px ${ROW_PADX}px`, borderRadius: 12,
                opacity: clamp01(rev), transform: glide(`translateX(${lerp(-20, 0, clamp01(rev))}px)`, true),
                background: (!fired && i === 0) ? `${ACCENT}1e` : 'transparent'}}>
                {/* the tick fills its 44 px box less 10 px, ~32 px once the palette has scaled to 0.94 */}
                <div style={{flex: 'none', boxSizing: 'border-box', width: TICK_BOX, height: TICK_BOX, borderRadius: 11, border: `2px solid ${tick ? '#59d98b' : '#3a475e'}`,
                  background: tick ? '#59d98b' : 'transparent',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                  {/* the tick is a PATH (runtime/icons' check stroke), not a '✓' glyph: Inter has no ✓, so it came from a
                      fallback face, and as type it trembled 0.18px RMS under a camera push where a path glides
                      (jitter_qa on a one-beat promo film, 2026-11-04) */}
                  {tick ? <svg width={TICK_BOX - 10} height={TICK_BOX - 10} viewBox="5 6 14 12" fill="none" stroke="#0b0f17"
                    strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round"><path d="M8 12.5l2.7 2.7L16 9" /></svg> : null}
                </div>
                <div style={{minWidth: 0, font: `500 ${rowFit}px/1 var(--f-body, Inter,system-ui,sans-serif)`, color: tick ? '#8f9bb0' : '#dfe6f0'}}>{r}</div>
                {i === 0 && !fired && <div style={{marginLeft: 'auto', padding: '8px 16px', borderRadius: 8, background: '#2a3346',
                  font: '700 30px/1 var(--f-body, Inter)', color: ACCENT, whiteSpace: 'nowrap', flex: 'none'}}>↵ run</div>}
              </div>
            );
          })}
        </div>
      </div>
      {result ? (() => {
        const lastTick = 0.66 + (n - 1) * stepT;
        const r = easeOutBack(seg(t, lastTick + 0.04, lastTick + 0.16));
        const RW = Math.round(Math.min(PW * 0.62, W * 0.4)), RX = PX + PW - RW - Math.round(W * 0.02);
        const ext = (result.name.split('.').pop() ?? '').toUpperCase().slice(0, 4); // @truncates: the file's own extension, read off its name, as its badge — not a claim
        return (
          <div style={{position: 'absolute', left: RX, top: palTop + palH + 22, width: RW, opacity: clamp01(r),
            transform: glide(`translateY(${lerp(30, 0, clamp01(r))}px)`, true), display: 'flex', alignItems: 'center', gap: 22,
            padding: '22px 26px', borderRadius: 18, background: '#f4f7fb', boxShadow: `${softShadow(3, '#000000')}, 0 0 0 1px ${rgba(ACCENT, 0.4)}`}}>
            <div style={{flex: 'none', width: 58, height: 70, borderRadius: 10, background: ACCENT, display: 'flex', alignItems: 'flex-end',
              justifyContent: 'center', paddingBottom: 10, font: '800 17px/1 var(--f-body, Inter)', color: '#ffffff'}}>{ext}</div>
            <div style={{minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6}}>
              <div style={{font: `700 ${Math.max(FLOOR, 34)}px/1.1 var(--f-body, Inter, system-ui, sans-serif)`, color: '#0b0f17', whiteSpace: 'nowrap',
                overflow: 'hidden', textOverflow: 'ellipsis'}}>{result.name}</div>
              {result.note ? <div style={{font: `600 ${FLOOR}px/1.1 var(--f-body, Inter, system-ui, sans-serif)`, color: '#1f8f57'}}>{result.note}</div> : null}
            </div>
          </div>
        );
      })() : null}
      {paired ? (
        <div style={{position: 'absolute', left: PX + PW + Math.round(W * 0.05), top: palTop, width: W - (PX + PW + Math.round(W * 0.05)) - Math.round(W * 0.06),
          height: palH, display: 'flex', alignItems: 'center',
          ...typeStyle(Math.min(typePx('h1', W, H), Math.floor((W - (PX + PW + W * 0.11)) / Math.max(6, Math.max(...(title ?? '').split(/\s+/).map((w) => w.length)) * 0.56))),
            {weight: 780, color: '#f3f5f9'}),
          fontFamily: 'var(--f-display, Inter, "Noto Sans SC", system-ui, sans-serif)'}}>
          <div><TextReveal text={title ?? ''} start={Math.round(span * 0.5)} accent={titleAccent} accentColor={ACCENT} /></div>
        </div>
      ) : null}
      {/* Return flash */}
      {flash > 0 && <AbsoluteFill style={{background: '#fff', opacity: 0.14 * flash}} />}
    </AbsoluteFill>
  );
};
export default CommandSummon;
