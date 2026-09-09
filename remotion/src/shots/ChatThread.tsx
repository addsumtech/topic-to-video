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

// THE THREAD SCALES WITH ITS COLUMN. Every number here was drawn for a 1500px column, and the column is
// `min(1500, W * 0.94)` — 1015 on a 1080-wide frame. So the same four messages wrapped to more lines in a
// narrower box at the SAME 46px, and the last one ('Done ✓ — 24 slides, in your Deliverables folder.', the
// line the whole exchange is for) ran 28px into the caption band at 1:1. A chat column that gets narrower
// sets its type smaller; `f` is exactly 1 on any frame wide enough for the full column, so 16:9 and 9:16
// are byte-identical.
const Bubble: React.FC<{m: Msg; t: number; f: number}> = ({m, t, f}) => {
  const dna = useDNA();
  const A1 = dna?.accent ?? YOU, SURF = dna?.surface ?? WB, INKc = dna?.fg ?? INK, ON = dna?.onAccent ?? '#fff', A2c = dna?.accent2 ?? A2;
  const r = easeOutBack(seg(t, m.at, m.at + 0.22));
  const you = m.side === 'you';
  const av = Math.round(74 * f);
  return (
    <div style={{display: 'flex', justifyContent: you ? 'flex-end' : 'flex-start', marginBottom: Math.round(34 * f),
      opacity: clamp01(r), transform: `translateY(${lerp(30, 0, clamp01(r))}px)`}}>
      {!you && <div style={{width: av, height: av, borderRadius: av / 2, marginRight: Math.round(22 * f), background: `linear-gradient(150deg,${A1},${A2c})`, flexShrink: 0}} />}
      <div style={{maxWidth: 880 * f, padding: `${Math.round(30 * f)}px ${Math.round(40 * f)}px`, borderRadius: Math.round(28 * f), background: you ? A1 : SURF,
        color: you ? ON : INKc, font: `500 ${Math.round(46 * f)}px/1.35 var(--f-body, Inter,system-ui,sans-serif)`, borderBottomRightRadius: you ? 8 : Math.round(28 * f), borderBottomLeftRadius: you ? Math.round(28 * f) : 8}}>{m.text}</div>
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
  const CW = Math.min(1500, W * 0.94);
  const f = CW / 1500;
  return (
    <AbsoluteFill style={{background: BG}}>
      <div style={{position: 'absolute', left: (W - CW) / 2, top: 170, width: CW}}>
        {MSGS.map((m, i) => (t > m.at - 0.02 ? <Bubble key={i} m={m} t={t} f={f} /> : null))}
        {nextWb && (
          <div style={{display: 'flex', alignItems: 'center', gap: Math.round(22 * f), marginBottom: Math.round(34 * f)}}>
            <div style={{width: Math.round(74 * f), height: Math.round(74 * f), borderRadius: Math.round(37 * f), background: `linear-gradient(150deg,${A1},${A2c})`}} />
            <div style={{padding: `${Math.round(30 * f)}px ${Math.round(36 * f)}px`, borderRadius: Math.round(28 * f), background: SURF, display: 'flex', gap: Math.round(12 * f)}}>
              {[0, 1, 2].map((k) => <div key={k} style={{width: Math.round(18 * f), height: Math.round(18 * f), borderRadius: Math.round(9 * f), background: DIM,
                opacity: 0.4 + 0.6 * Math.max(0, Math.sin((t * 30 - k * 2)))}} />)}
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
export default ChatThread;
