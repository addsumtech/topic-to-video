// SHOT · Chat Thread — conversation language: a messaging thread where you ask and WorkBuddy replies, with
// typing indicators and bubbles sliding in. Light, human, casual (a communication/support look). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutBack, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 165; // 5.5s
// LEVEL-C DNA migration: the whole chat UI flips together — ground, bubble surfaces, ink, and on-accent text — so
// on a dark DNA it reads as a dark chat instead of light-ink-on-light-bubble (the level-A inversion). Both the main
// component AND the Bubble subcomponent read useDNA (a subcomponent renders inside the provider). Null DNA = original.
const YOU = '#2E7BFF', WB = '#f0f1f4', INK = '#1b2333', A2 = '#7C5CFF', DOT = '#9aa3b2';
type Msg = {side: 'you' | 'wb'; text: string; at: number};
const DEFAULT_MSGS: Msg[] = [
  {side: 'you', text: 'Build the Q3 board deck from the finance folder', at: 0.1},
  {side: 'wb', text: 'On it — planning now.', at: 0.32},
  {side: 'wb', text: '5 experts working in parallel…', at: 0.5},
  {side: 'wb', text: 'Done ✓ — 24 slides, in your Deliverables folder.', at: 0.74},
];

const Bubble: React.FC<{m: Msg; t: number}> = ({m, t}) => {
  const dna = useDNA();
  const A1 = dna?.accent ?? YOU, SURF = dna?.surface ?? WB, INKc = dna?.fg ?? INK, ON = dna?.onAccent ?? '#fff', A2c = dna?.accent2 ?? A2;
  const r = easeOutBack(seg(t, m.at, m.at + 0.22));
  const you = m.side === 'you';
  return (
    <div style={{display: 'flex', justifyContent: you ? 'flex-end' : 'flex-start', marginBottom: 34,
      opacity: clamp01(r), transform: `translateY(${lerp(30, 0, clamp01(r))}px)`}}>
      {!you && <div style={{width: 74, height: 74, borderRadius: 37, marginRight: 22, background: `linear-gradient(150deg,${A1},${A2c})`, flexShrink: 0}} />}
      <div style={{maxWidth: 880, padding: '30px 40px', borderRadius: 28, background: you ? A1 : SURF,
        color: you ? ON : INKc, font: '500 46px/1.35 Inter,system-ui,sans-serif', borderBottomRightRadius: you ? 8 : 28, borderBottomLeftRadius: you ? 28 : 8}}>{m.text}</div>
    </div>
  );
};

export const ChatThread: React.FC<{messages?: Msg[]}> = ({messages: MSGS = DEFAULT_MSGS} = {}) => {
  const dna = useDNA();
  const BG = dna?.bg ?? '#fbfcfe', SURF = dna?.surface ?? WB, A1 = dna?.accent ?? YOU, A2c = dna?.accent2 ?? A2, DIM = dna?.dim ?? DOT;
  const t = useT();
  const {width: W} = useVideoConfig();
  // typing indicator shows just before the next wb message
  const nextWb = MSGS.find((m) => m.side === 'wb' && t > m.at - 0.12 && t < m.at);
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: (W - 1500) / 2, top: 170, width: 1500}}>
        {MSGS.map((m, i) => (t > m.at - 0.02 ? <Bubble key={i} m={m} t={t} /> : null))}
        {nextWb && (
          <div style={{display: 'flex', alignItems: 'center', gap: 22, marginBottom: 34}}>
            <div style={{width: 74, height: 74, borderRadius: 37, background: `linear-gradient(150deg,${A1},${A2c})`}} />
            <div style={{padding: '30px 36px', borderRadius: 28, background: SURF, display: 'flex', gap: 12}}>
              {[0, 1, 2].map((k) => <div key={k} style={{width: 18, height: 18, borderRadius: 9, background: DIM,
                opacity: 0.4 + 0.6 * Math.max(0, Math.sin((t * 30 - k * 2)))}} />)}
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
export default ChatThread;
