// SHOT · Screen + Bubble — Loom language: a light app screen being walked through, with a circular cam
// BUBBLE in the corner (a person narrating) and a cursor demonstrating. Casual, human, light. The picture-
// in-picture + screen choreography is a Remotion-native composite the flat tier doesn't do. Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeCursor, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
const BRAND = '#6C5CE7';

export const ScreenBubble: React.FC<{appTitle?: string; nav?: string[]}> = ({
  appTitle = 'workbuddy — untitled', nav = ['Home', 'Projects', 'Deliverables', 'Team']} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const SX = 150, SY = 130, SW = W - 300, SH = H - 300;
  // cursor path: rest → "New" button (click) → the created block
  const pts: [number, number][] = [[SX + SW * 0.5, SY + SH * 0.7], [SX + 250, SY + 150], [SX + SW * 0.62, SY + 360]];
  const seg1 = easeCursor(seg(t, 0.1, 0.34)), seg2 = easeCursor(seg(t, 0.44, 0.7));
  let cx = pts[0][0], cy = pts[0][1];
  if (t < 0.44) {cx = lerp(pts[0][0], pts[1][0], seg1); cy = lerp(pts[0][1], pts[1][1], seg1);}
  else {cx = lerp(pts[1][0], pts[2][0], seg2); cy = lerp(pts[1][1], pts[2][1], seg2);}
  const clicked = t > 0.34 && t < 0.44;
  const ripple = clicked ? (t - 0.34) / 0.1 : 0;
  const created = easeOutBack(seg(t, 0.46, 0.7));
  return (
    <AbsoluteFill style={{background: '#e9ebf2'}}>
      {/* the app window */}
      <div style={{position: 'absolute', left: SX, top: SY, width: SW, height: SH, background: '#fff', borderRadius: 18,
        boxShadow: '0 40px 100px rgba(40,45,80,.22)', overflow: 'hidden'}}>
        <div style={{height: 66, background: '#f6f7fb', borderBottom: '1px solid #e8eaf1', display: 'flex', alignItems: 'center', gap: 12, padding: '0 26px'}}>
          {['#ff5f57', '#febc2e', '#28c840'].map(c => <div key={c} style={{width: 16, height: 16, borderRadius: 8, background: c}} />)}
          <div style={{marginLeft: 20, font: '600 26px/1 Inter', color: '#8b90a3'}}>{appTitle}</div>
        </div>
        <div style={{display: 'flex', height: SH - 66}}>
          <div style={{width: 300, borderRight: '1px solid #eef0f6', padding: 26, display: 'flex', flexDirection: 'column', gap: 20}}>
            {nav.map((n, i) => <div key={i} style={{padding: '16px 20px', borderRadius: 10,
              background: i === 2 ? `${BRAND}18` : 'transparent', font: `${i === 2 ? 700 : 500} 30px/1 Inter`, color: i === 2 ? BRAND : '#6b7180'}}>{n}</div>)}
          </div>
          <div style={{flex: 1, padding: 44, position: 'relative'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <div style={{font: '800 52px/1 Inter', color: '#1b2333'}}>{nav[2] ?? nav[nav.length - 1]}</div>
              <div style={{position: 'relative', padding: '18px 30px', borderRadius: 12, background: BRAND, color: '#fff', font: '700 32px/1 Inter'}}>+ New
                {ripple > 0 && <div style={{position: 'absolute', inset: 0, borderRadius: 12, border: `3px solid ${BRAND}`, transform: `scale(${1 + ripple})`, opacity: 1 - ripple}} />}
              </div>
            </div>
            {/* the "created" deliverable row */}
            <div style={{marginTop: 40, opacity: clamp01(created), transform: `translateY(${lerp(24, 0, clamp01(created))}px)`,
              padding: '30px 34px', borderRadius: 14, border: '1px solid #eef0f6', background: '#fbfcfe', display: 'flex', alignItems: 'center', gap: 24}}>
              <div style={{width: 54, height: 54, borderRadius: 12, background: `${BRAND}22`}} />
              <div><div style={{font: '700 36px/1 Inter', color: '#1b2333'}}>Q3 board deck</div>
                <div style={{font: '500 26px/1 Inter', color: '#98a0b0', marginTop: 10}}>created just now</div></div>
            </div>
          </div>
        </div>
      </div>
      {/* the cursor */}
      <div style={{position: 'absolute', left: cx, top: cy, filter: 'drop-shadow(0 5px 10px rgba(30,40,80,.3))'}}>
        <svg width="32" height="38" viewBox="0 0 22 26"><path d="M2,2 L2,22 L7,17 L10,24 L13,23 L10,16 L17,16 Z" fill="#1b2333" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" /></svg>
      </div>
      {/* the CAM BUBBLE (person narrating) */}
      <div style={{position: 'absolute', left: 90, top: H - 320, width: 230, height: 230, borderRadius: 115,
        background: `linear-gradient(150deg, ${BRAND}, #EC4899)`, border: '6px solid #fff', boxShadow: '0 20px 50px rgba(40,45,80,.3)', overflow: 'hidden'}}>
        {/* abstract friendly avatar */}
        <div style={{position: 'absolute', left: 82, top: 46, width: 66, height: 66, borderRadius: 33, background: 'rgba(255,255,255,.9)'}} />
        <div style={{position: 'absolute', left: 48, top: 124, width: 134, height: 120, borderRadius: '60px 60px 0 0', background: 'rgba(255,255,255,.9)'}} />
        <div style={{position: 'absolute', left: 18, top: 18, display: 'flex', alignItems: 'center', gap: 8}}>
          <div style={{width: 14, height: 14, borderRadius: 7, background: '#ff4d4d'}} /><div style={{font: '700 20px/1 Inter', color: '#fff'}}>REC</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
export default ScreenBubble;
