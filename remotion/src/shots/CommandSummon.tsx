// SHOT · Command Summon — Raycast/Superhuman language (DARK, on purpose — the command palette's native look).
// A palette flies in, a plain-language command TYPES itself, matches filter live, Return fires — and the
// work spawns as a checklist that ticks off. "One instruction → it plans and runs." Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s

const ACCENT0 = '#6E8BFF';
const DEFAULT_ROWS = ['Plan the deck outline', 'Pull the Q3 numbers', 'Design 24 slides', 'Write the narrative', 'Export to your folder'];

export const CommandSummon: React.FC<{command?: string; items?: string[]}> = ({
  command = 'Build the Q3 board deck from ~/finance', items: ROWS = DEFAULT_ROWS} = {}) => {
  const t = useT();
  const dna = useDNA(); const ACCENT = dna?.accent ?? ACCENT0;
  const {width: W, height: H} = useVideoConfig();
  // phases: palette in (0-.12) · type command (.12-.42) · Return flash (.46) · checklist spawns+ticks (.5-1)
  const inP = easeOutBack(seg(t, 0, 0.14));
  const typed = Math.floor(command.length * easeOutCubic(seg(t, 0.14, 0.44)));
  const fired = t > 0.46;
  const flash = fired ? Math.max(0, 1 - (t - 0.46) / 0.06) : 0;
  const caretOn = t < 0.46 && Math.floor(t * 60) % 2 === 0;
  const palY = lerp(60, 0, inP) + (fired ? -lerp(0, 40, easeOutCubic(seg(t, 0.46, 0.6))) : 0);
  const palScale = fired ? lerp(1, 0.94, easeOutCubic(seg(t, 0.46, 0.62))) : 1;
  const PW = 1180, PX = (W - PW) / 2;
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 100% at 50% 22%, #141a26, #090c12 60%)'}}>
      {/* soft accent glow behind the palette */}
      <div style={{position: 'absolute', left: W / 2 - 420, top: 150, width: 840, height: 520,
        background: `radial-gradient(closest-side, ${ACCENT}22, transparent)`, filter: 'blur(30px)'}} />
      {/* THE PALETTE */}
      <div style={{position: 'absolute', left: PX, top: 210 + palY, width: PW, opacity: clamp01(inP),
        transform: `scale(${palScale})`, transformOrigin: '50% 0', background: 'rgba(20,25,35,0.92)',
        border: '1px solid #2a3346', borderRadius: 20, boxShadow: '0 50px 120px rgba(0,0,0,.6)', backdropFilter: 'blur(20px)'}}>
        {/* input row */}
        <div style={{display: 'flex', alignItems: 'center', gap: 22, padding: '34px 40px', borderBottom: '1px solid #232c3d'}}>
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke={ACCENT} strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="21" y2="21" /></svg>
          <div style={{font: '500 46px/1 var(--f-body, Inter,system-ui,sans-serif)', color: '#eef2f8', whiteSpace: 'pre'}}>
            {command.slice(0, typed)}<span style={{opacity: caretOn ? 1 : 0, color: ACCENT}}>|</span>
          </div>
        </div>
        {/* matched actions / checklist that spawns after Return */}
        <div style={{padding: '18px 20px'}}>
          {ROWS.map((r, i) => {
            const rev = fired ? easeOutBack(seg(t, 0.5 + i * 0.07, 0.5 + i * 0.07 + 0.18)) : (i === 0 ? 1 : 0.0);
            const tick = fired && t > 0.66 + i * 0.06;
            return (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, padding: '20px 24px', borderRadius: 12,
                opacity: clamp01(rev), transform: `translateX(${lerp(-20, 0, clamp01(rev))}px)`,
                background: (!fired && i === 0) ? `${ACCENT}1e` : 'transparent'}}>
                <div style={{width: 34, height: 34, borderRadius: 9, border: `2px solid ${tick ? '#59d98b' : '#3a475e'}`,
                  background: tick ? '#59d98b' : 'transparent', color: '#0b0f17', font: '700 22px/30px var(--f-body, Inter)', textAlign: 'center'}}>{tick ? '✓' : ''}</div>
                <div style={{font: '500 38px/1 var(--f-body, Inter,system-ui,sans-serif)', color: tick ? '#8f9bb0' : '#dfe6f0'}}>{r}</div>
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
