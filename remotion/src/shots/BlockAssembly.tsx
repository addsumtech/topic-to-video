// SHOT · Block Assembly — Notion language: a document BUILDS itself block by block. Each block snaps into
// the page (slide-up + settle) top-to-bottom — title, text, callout, to-dos, table. Warm off-white, calm,
// minimal ink (deliberately unlike the loud/dark shots). Deterministic staggered assembly.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';

export const DURATION = 165; // 5.5s
const INK = '#37352f', DIM = '#e6e3dd', ACCENT = '#2E7BFF';

const Block: React.FC<{i: number; t: number; children: React.ReactNode}> = ({i, t, children}) => {
  const r = easeOutBack(seg(t, 0.14 + i * 0.13, 0.14 + i * 0.13 + 0.24));
  return <div style={{opacity: clamp01(r), transform: `translateY(${lerp(46, 0, clamp01(r))}px)`, marginBottom: 30}}>{children}</div>;
};

export const BlockAssembly: React.FC<{title?: string; callout?: string; items?: string[]}> = ({
  title = 'Q3 Board Deck', callout = 'Goal: a board-ready deck from the Q3 numbers, by Friday.',
  items = ['Pull the financials', 'Draft the narrative', 'Design 24 slides']} = {}) => {
  const t = useT();
  const {width: W} = useVideoConfig();
  const line = (w: string, c = DIM) => <div style={{height: 20, borderRadius: 6, background: c, width: w}} />;
  return (
    <AbsoluteFill style={{background: '#faf9f7'}}>
      <div style={{position: 'absolute', left: (W - 1120) / 2, top: 150, width: 1120}}>
        <Block i={0} t={t}><div style={{font: '800 92px/1 Inter,system-ui,sans-serif', color: INK}}>{title}</div></Block>
        <Block i={1} t={t}><div style={{display: 'flex', flexDirection: 'column', gap: 16}}>{line('96%')}{line('88%')}{line('72%')}</div></Block>
        <Block i={2} t={t}>
          <div style={{display: 'flex', gap: 22, padding: '30px 34px', borderRadius: 14, background: `${ACCENT}14`, borderLeft: `5px solid ${ACCENT}`}}>
            <div style={{font: '700 40px/1 Inter', color: ACCENT}}>i</div>
            <div style={{font: '600 36px/1.35 Inter,system-ui,sans-serif', color: INK}}>{callout}</div>
          </div>
        </Block>
        <Block i={3} t={t}>
          <div style={{display: 'flex', flexDirection: 'column', gap: 20}}>
            {items.map((s, k) => (
              <div key={k} style={{display: 'flex', alignItems: 'center', gap: 20}}>
                <div style={{width: 34, height: 34, borderRadius: 7, background: k < 2 ? '#12b76a' : '#fff', border: `2px solid ${k < 2 ? '#12b76a' : '#c9c5bc'}`, color: '#fff', font: '700 20px/30px Inter', textAlign: 'center'}}>{k < 2 ? '✓' : ''}</div>
                <div style={{font: '600 38px/1 Inter,system-ui,sans-serif', color: k < 2 ? '#9b968c' : INK, textDecoration: k < 2 ? 'line-through' : 'none'}}>{s}</div>
              </div>
            ))}
          </div>
        </Block>
        <Block i={4} t={t}>
          <div style={{border: `1px solid ${DIM}`, borderRadius: 12, overflow: 'hidden'}}>
            {[0, 1, 2].map(r => <div key={r} style={{display: 'flex', borderBottom: r < 2 ? `1px solid ${DIM}` : 'none'}}>
              {[0, 1, 2].map(c => <div key={c} style={{flex: 1, padding: '22px 26px', borderRight: c < 2 ? `1px solid ${DIM}` : 'none',
                font: `${r === 0 ? 700 : 500} 30px/1 Inter`, color: r === 0 ? INK : '#8b877d'}}>{r === 0 ? ['Metric', 'Q2', 'Q3'][c] : ['—', '—', '—'][c]}</div>)}
            </div>)}
          </div>
        </Block>
      </div>
    </AbsoluteFill>
  );
};
export default BlockAssembly;
