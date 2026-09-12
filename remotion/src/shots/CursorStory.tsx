// SHOT · Cursor Story — Raycast/Superhuman language: a single HERO cursor drives the whole story, moving
// with exaggerated easing (+ a motion trail), firing keyboard-shortcut chips, and jump-cutting past loading
// so a task finishes in a blink. Dark + Raycast-red (a red-accented dark, distinct from the blue/purple).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeCursor, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {useDNA} from '../runtime/dna';
import {CONTENT_TOP, contentBottom} from '../runtime/layout';

export const DURATION = 135; // 4.5s
const RED_D0 = '#FF6B6B', BG_D0 = '#0d1017';
const DEFAULT_ROWS = ['Weekly report', 'Invoice batch', 'Q3 numbers', 'Vendor list', 'Meeting notes', 'Launch copy'];

// cursor position along waypoints at a given (possibly past) time — used for the trail ghosts too.
function cursorAt(tt: number, W: number, H: number): [number, number] {
  const pts: [number, number][] = [[W * 0.5, H * 0.8], [W * 0.34, 300], [W * 0.34, 560], [W * 0.62, 720]];
  const segs = [[0.08, 0.3], [0.34, 0.5], [0.56, 0.74]];
  let x = pts[0][0], y = pts[0][1];
  for (let i = 0; i < segs.length; i++) {
    const e = easeCursor(seg(tt, segs[i][0], segs[i][1]));
    x = lerp(x, pts[i + 1][0], e); y = lerp(y, pts[i + 1][1], e);
  }
  return [x, y];
}

export const CursorStory: React.FC<{items?: string[]; doneLabel?: string; doneNote?: string; command?: string}> = ({items: ROWS = DEFAULT_ROWS, doneLabel: DONE = '', doneNote: DONE_NOTE = '', command: CMD = ''} = {}) => {
  const dna = useDNA();
  const RED = dna?.accent ?? RED_D0, BG = dna?.bg ?? BG_D0;
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const [cx, cy] = cursorAt(t, W, H);
  const kCmd = t > 0.3 && t < 0.44;      // ⌘K chip
  const kEnter = t > 0.5 && t < 0.64;    // ↵ chip
  const paletteOn = t > 0.32 && t < 0.56;
  const done = t > 0.74;
  const hi = t < 0.32 ? -1 : Math.min(ROWS.length - 1, Math.floor(seg(t, 0.08, 0.3) * 3)); // hovered row
  // THE LIST GROWS DOWNWARD FROM A FIXED TOP, so its last row ('Launch copy' — the one the palette is
  // about to clear) ran into the caption band at 1:1. The first repair moved the TOP up by what did not
  // fit, which is right until the list is longer than the zone: ten items pushed it to y=-237 and the first
  // two rows left the frame through the TOP instead — a clamp with no floor. A list too long for the zone
  // is a PITCH problem, not a position one, so the rows close up and the top never rises above the content
  // zone. The default six on a 16:9 frame keep their full 106.
  const PAD = 26, LINE = 40, MARGIN = 12, BORDER = 2;
  const n = Math.max(1, ROWS.length);
  const zone = contentBottom(W, H) - CONTENT_TOP;
  const ROW_H = Math.min(PAD * 2 + LINE + BORDER + MARGIN, Math.floor(zone / n));
  const PADY = Math.max(6, Math.round((ROW_H - LINE - BORDER - MARGIN) / 2));
  const LX = W * 0.26, LY = Math.max(CONTENT_TOP, Math.min(240, contentBottom(W, H) - n * ROW_H));
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 100% at 40% 20%, #161b26, ${BG} 60%)`}}>
      {/* the list UI */}
      <div style={{position: 'absolute', left: LX, top: LY, width: Math.min(900, W - LX - 40), opacity: paletteOn ? 0.35 : 1, transition: 'none'}}>
        {ROWS.map((r, i) => (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22, padding: `${PADY}px 30px`, borderRadius: 12,
            marginBottom: MARGIN, background: i === hi ? `${RED}1c` : '#141922', border: `1px solid ${i === hi ? RED : '#1e2531'}`}}>
            <div style={{width: 14, height: 14, borderRadius: 7, background: i <= hi && t > 0.6 ? '#59d98b' : '#3a4658'}} />
            <div style={{font: '600 40px/1 var(--f-body, Inter,system-ui,sans-serif)', color: '#d6deea'}}>{r}</div>
            {i === hi && <div style={{marginLeft: 'auto', font: '700 26px/1 var(--f-body, Inter)', color: RED}}>⌘K</div>}
          </div>
        ))}
      </div>
      {/* command palette that jump-cuts in */}
      {paletteOn && (
        <div style={{position: 'absolute', left: W / 2 - Math.min(460, W * 0.44), top: 300, width: Math.min(920, W * 0.88), background: 'rgba(20,24,32,.96)',
          border: `1px solid ${RED}55`, borderRadius: 18, boxShadow: '0 40px 100px rgba(0,0,0,.6)', padding: '30px 36px'}}>
          <div style={{font: '500 42px/1 var(--f-body, Inter)', color: '#eef2f8'}}>{CMD}{'\u258d'}</div>
        </div>
      )}
      {/* result toast after Return (jump-cut past the work) */}
      {/* AND THE CONTAINER IS GATED ON THE SAME THING ITS LINES ARE. The comment below says "with nothing
          passed the block simply does not draw" and it drew: `done` is a TIME, so on default props the
          toast rendered its background, border and 34px of padding with nothing inside, over the second
          row of its own list, at 16:9. No gate can see it — it is not text, so the type sweeps are blind to
          it, and it is not a ground, so the luminance ones are too. It took looking at a still. */}
      {done && (DONE || DONE_NOTE) && (
        <div style={{position: 'absolute', left: W / 2 - 300, top: 340, width: 600, opacity: easeOutBack(seg(t, 0.74, 0.86)),
          background: '#12241a', border: '1px solid #1f6b3f', borderRadius: 16, padding: '34px 40px', textAlign: 'center'}}>
          {/* THE RESULT LINE COMES FROM THE FILM. These two were literals — `Cleared · 6 tasks` and
              `in one keystroke` — so every film that reached for this register printed English, and the
              「6」 was a count nobody supplied. No default on doneLabel: a number is not invented, so with
              nothing passed the block simply does not draw. */}
          {DONE ? <div style={{font: '800 60px/1 var(--f-body, Inter)', color: '#59d98b'}}>{DONE}</div> : null}
          {DONE_NOTE ? <div style={{font: `600 32px/${leading(DONE_NOTE, 1)} var(--f-body, Inter)`, color: '#89e0a8', marginTop: 12}}>{DONE_NOTE}</div> : null}
        </div>
      )}
      {/* keyboard chips */}
      {kCmd && <KeyChip x={cx + 40} y={cy - 10} label="⌘K" c={RED} />}
      {kEnter && <KeyChip x={cx + 40} y={cy - 10} label="↵" c={RED} />}
      {/* the hero cursor (no ghost trail — a discrete ghost reads as a render artifact, not speed) */}
      <Pointer x={cx} y={cy} op={1} />
    </AbsoluteFill>
  );
};

const Pointer: React.FC<{x: number; y: number; op: number}> = ({x, y, op}) => (
  <div style={{position: 'absolute', left: x, top: y, opacity: op, filter: op === 1 ? 'drop-shadow(0 5px 10px rgba(0,0,0,.6))' : undefined}}>
    <svg width="34" height="40" viewBox="0 0 22 26"><path d="M2,2 L2,22 L7,17 L10,24 L13,23 L10,16 L17,16 Z" fill="#fff" stroke="#0d1017" strokeWidth="1.4" strokeLinejoin="round" /></svg>
  </div>
);
const KeyChip: React.FC<{x: number; y: number; label: string; c: string}> = ({x, y, label, c}) => (
  <div style={{position: 'absolute', left: x, top: y, padding: '10px 20px', borderRadius: 10, background: c,
    color: '#0d1017', font: '800 34px/1 var(--f-body, Inter,system-ui,sans-serif)', boxShadow: '0 8px 20px rgba(0,0,0,.5)'}}>{label}</div>
);
export default CursorStory;
