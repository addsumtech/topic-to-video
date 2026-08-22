// SHOT · Versus Split — a head-to-head split screen: two contenders slide in from opposite edges across a
// diagonal seam, a VS badge slams in the middle, attribute rows tick in per side, and the winner side lights
// up. The "A vs B / this beats that" register (family H — comparison). Attributes/winner are QUALITATIVE and
// overridable (a real film supplies the honest comparison). Deterministic.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeOutBack, easeOutExpo, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 155; // ~5.2s

type Side = {label?: string; points?: string[]};

const Panel: React.FC<{side: Side; enter: number; align: 'left' | 'right'; tone: string; win: boolean; t: number; base: number}> = ({
  side, enter, align, tone, win, t, base}) => (
  <div style={{position: 'absolute', top: 0, bottom: 0, [align]: 0, width: '58%',
    transform: `translateX(${(align === 'left' ? -1 : 1) * (1 - enter) * 60}%)`,
    display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: align === 'left' ? '0 0 0 130px' : '0 130px 0 0',
    alignItems: align === 'left' ? 'flex-start' : 'flex-end',
    background: win ? `linear-gradient(${align === 'left' ? 105 : 255}deg, ${tone}2e, #0000 70%)` : 'transparent'}}>
    <div style={{color: win ? '#fff' : '#c7cee0', font: '800 92px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.03em',
      textShadow: win ? `0 0 40px ${tone}88` : 'none'}}>{side.label}</div>
    <div style={{marginTop: 30, display: 'flex', flexDirection: 'column', gap: 18,
      alignItems: align === 'left' ? 'flex-start' : 'flex-end'}}>
      {(side.points ?? []).slice(0, 4).map((p, i) => {
        const on = clamp01(seg(t, base + i * 0.08, base + 0.2 + i * 0.08));
        return <div key={i} style={{opacity: on, transform: `translateY(${(1 - on) * 10}px)`,
          display: 'flex', flexDirection: align === 'left' ? 'row' : 'row-reverse', alignItems: 'center', gap: 14,
          color: '#aeb6ca', font: '600 32px/1 Inter, system-ui, sans-serif'}}>
          <span style={{color: tone, fontWeight: 800}}>{win ? '✓' : '•'}</span>{p}</div>;
      })}
    </div>
    {win ? <div style={{marginTop: 34, padding: '12px 28px', borderRadius: 999, background: tone, color: '#04120d',
      font: '800 30px/1 Inter, system-ui, sans-serif', opacity: clamp01(seg(t, 0.8, 0.95))}}>WINNER</div> : null}
  </div>
);

export const VersusSplit: React.FC<{left?: Side; right?: Side; winner?: number; title?: string}> = ({
  left: LEFT = {label: 'Before', points: ['Manual steps', 'Hours lost', 'Easy to miss']},
  right: RIGHT = {label: 'After', points: ['One command', 'Seconds', 'Always caught']},
  winner: WINNER = 1, title: TITLE = 'The difference'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  const lEnter = easeOutExpo(seg(t, 0.08, 0.42));
  const rEnter = easeOutExpo(seg(t, 0.16, 0.5));
  const vs = easeOutBack(clamp01(seg(t, 0.46, 0.64)));
  const titleIn = easeOutCubic(seg(t, 0.02, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? ('#0a0c12'), overflow: 'hidden'}}>
      {/* two grounds */}
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(120deg, #141a2e 0%, #141a2e 50%, #1e1420 50%, #1e1420 100%)'}} />
      {/* diagonal seam */}
      <div style={{position: 'absolute', top: -60, bottom: -60, left: '50%', width: 6, background: '#0a0c12',
        transform: 'translateX(-50%) rotate(8deg)', boxShadow: '0 0 30px #000'}} />

      <div style={{position: 'absolute', top: 54, left: 0, right: 0, textAlign: 'center', opacity: titleIn, zIndex: 5,
        color: '#aeb6ca', font: '700 30px/1 "JetBrains Mono", monospace', letterSpacing: '0.3em', textTransform: 'uppercase'}}>{TITLE}</div>

      <Panel side={LEFT} enter={lEnter} align="left" tone="#5b8cff" win={WINNER === 0} t={t} base={0.5} />
      <Panel side={RIGHT} enter={rEnter} align="right" tone="#37d4a6" win={WINNER === 1} t={t} base={0.56} />

      {/* VS badge */}
      <div style={{position: 'absolute', left: '50%', top: '50%', transform: `translate(-50%,-50%) scale(${vs}) rotate(${lerp(-14, 0, vs)}deg)`,
        width: 150, height: 150, borderRadius: '50%', background: 'radial-gradient(circle at 40% 35%, #2a3048, #12141f)',
        border: '3px solid #454d68', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 6,
        boxShadow: '0 20px 60px #000a'}}>
        <div style={{color: '#fff', font: '900 58px/1 Inter, system-ui, sans-serif', letterSpacing: '-0.02em'}}>VS</div>
      </div>
    </AbsoluteFill>
  );
};
export default VersusSplit;
