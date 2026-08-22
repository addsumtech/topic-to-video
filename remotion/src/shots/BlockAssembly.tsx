// SHOT · Block Assembly — Notion language: a document BUILDS itself block by block. Each block snaps into
// the page (slide-up + settle) top-to-bottom — title, text, callout, to-dos, table. Warm off-white, calm,
// minimal ink (deliberately unlike the loud/dark shots). Deterministic staggered assembly.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {List} from '../runtime/atoms';

export const DURATION = 165; // 5.5s
// LEVEL-C: the Notion-style light document flips with the DNA (page→bg, ink→fg, blocks/borders→line, accent) → a
// dark document on a dark DNA, the original warm off-white on null DNA.
const INK = '#37352f', DIM = '#e6e3dd', ACCENT = '#2E7BFF';

const Block: React.FC<{i: number; t: number; children: React.ReactNode}> = ({i, t, children}) => {
  const r = easeOutBack(seg(t, 0.14 + i * 0.13, 0.14 + i * 0.13 + 0.24));
  return <div style={{opacity: clamp01(r), transform: `translateY(${lerp(46, 0, clamp01(r))}px)`, marginBottom: 30}}>{children}</div>;
};

export const BlockAssembly: React.FC<{title?: string; callout?: string; items?: string[]}> = ({
  title = 'Q3 Board Deck', callout = 'Goal: a board-ready deck from the Q3 numbers, by Friday.',
  items = ['Pull the financials', 'Draft the narrative', 'Design 24 slides']} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? '#faf9f7', FG = dna?.fg ?? INK, ACC = dna?.accent ?? ACCENT, GOOD = dna?.accent2 ?? '#12b76a';
  const MUTE = dna?.line ?? DIM, SURF = dna?.surface ?? '#fff', DIMc = dna?.dim ?? '#8b877d', ON = dna?.onAccent ?? '#fff';
  // per-element fallbacks: these two had their OWN originals, so a null DNA must restore exactly those
  const CHECK_EDGE = dna?.line ?? '#c9c5bc', DONE_INK = dna?.dim ?? '#9b968c';
  const t = useT();
  const {width: W} = useVideoConfig();
  const line = (w: string, c = MUTE) => <div style={{height: 20, borderRadius: 6, background: c, width: w}} />;
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: (W - 1120) / 2, top: 150, width: 1120}}>
        <Block i={0} t={t}><div style={{font: '800 92px/1 Inter,system-ui,sans-serif', color: FG}}>{title}</div></Block>
        <Block i={1} t={t}><div style={{display: 'flex', flexDirection: 'column', gap: 16}}>{line('96%')}{line('88%')}{line('72%')}</div></Block>
        <Block i={2} t={t}>
          <div style={{display: 'flex', gap: 22, padding: '30px 34px', borderRadius: 14, background: `${ACC}22`, borderLeft: `5px solid ${ACC}`}}>
            <div style={{font: '700 40px/1 Inter', color: ACC}}>i</div>
            <div style={{font: '600 36px/1.35 Inter,system-ui,sans-serif', color: FG}}>{callout}</div>
          </div>
        </Block>
        <Block i={3} t={t}>
          <div style={{display: 'flex', flexDirection: 'column', gap: 20}}>
            {items.map((s, k) => (
              <div key={k} style={{display: 'flex', alignItems: 'center', gap: 20}}>
                <div style={{width: 34, height: 34, borderRadius: 7, background: k < 2 ? GOOD : SURF, border: `2px solid ${k < 2 ? GOOD : CHECK_EDGE}`, color: ON, font: '700 20px/30px Inter', textAlign: 'center'}}>{k < 2 ? '✓' : ''}</div>
                <div style={{textDecoration: k < 2 ? 'line-through' : 'none'}}>
                  <List items={[s]} ink={k < 2 ? DONE_INK : FG} marker={false} gap={0}
                    size={38} weight={600} lineHeight={1} />
                </div>
              </div>
            ))}
          </div>
        </Block>
        <Block i={4} t={t}>
          <div style={{border: `1px solid ${MUTE}`, borderRadius: 12, overflow: 'hidden'}}>
            {[0, 1, 2].map(r => <div key={r} style={{display: 'flex', borderBottom: r < 2 ? `1px solid ${MUTE}` : 'none'}}>
              {[0, 1, 2].map(c => <div key={c} style={{flex: 1, padding: '22px 26px', borderRight: c < 2 ? `1px solid ${MUTE}` : 'none',
                font: `${r === 0 ? 700 : 500} 30px/1 Inter`, color: r === 0 ? FG : DIMc}}>{r === 0 ? ['Metric', 'Q2', 'Q3'][c] : ['—', '—', '—'][c]}</div>)}
            </div>)}
          </div>
        </Block>
      </div>
    </AbsoluteFill>
  );
};
export default BlockAssembly;
