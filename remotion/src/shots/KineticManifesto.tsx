// SHOT · Kinetic Manifesto — Linear/Framer language: screen-filling phrases RUSH toward the viewer on the
// Z-axis, one after another, each snapping sharp at reading size then blowing past into blur as the next
// arrives. Bold SATURATED colour field (deliberately loud + unlike every other shot). Deterministic;
// motion-blur approximated by CSS blur on the fast approach/exit (frame-safe, no ancestor-flatten).

import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useT, seg, lerp, easeOutCubic, clamp01} from '../runtime/motion';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
// LEVEL-C: the loud saturated colour FIELD is this shot's identity, so it's KEPT as a field — but on a themed DNA
// the field becomes the DNA's accent→accent2 gradient (a green flood on terminal, etc.) and the words use on-accent
// / a second accent. Null DNA = the original bold blue/yellow. Word reads useDNA itself (module-scope subcomponent).
const PHRASES = ['ONE PROMPT.', 'A HUNDRED EXPERTS.', 'YOUR AI TEAM.'];
const HERO = 2; // which phrase pops in the accent colour

const Word: React.FC<{text: string; start: number; span: number; t: number; hero: boolean}> = ({text, start, span, t, hero}) => {
  const dna = useDNA();
  const heroC = dna?.accent2 ?? '#FFE24D', normC = dna?.onAccent ?? '#ffffff';
  const lp = clamp01((t - start) / span);
  if (t < start - 0.02 || lp >= 1) return null;
  // approach (0-.22): far+blur+fade-in → hold (.22-.62): reading size, sharp → depart (.62-1): rush past, blur+fade
  const scale = lp < 0.62 ? lerp(0.62, 1.0, easeOutCubic(clamp01(lp / 0.22))) : lerp(1.0, 1.9, easeOutCubic((lp - 0.62) / 0.38));
  const op = lp < 0.18 ? lp / 0.18 : lp > 0.72 ? clamp01((1 - lp) / 0.28) : 1;
  const blur = lp < 0.16 ? 18 * (1 - lp / 0.16) : lp > 0.66 ? 26 * ((lp - 0.66) / 0.34) : 0;
  return (
    <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{font: '900 200px/0.95 Inter,system-ui,sans-serif', letterSpacing: '-0.03em', textAlign: 'center',
        color: hero ? heroC : normC, opacity: op, transform: `scale(${scale})`,
        filter: blur > 0.5 ? `blur(${blur}px)` : undefined, textShadow: '0 20px 60px rgba(0,0,0,.25)',
        maxWidth: '82%', padding: '0 60px'}}>{text}</div>
    </AbsoluteFill>
  );
};

export const KineticManifesto: React.FC<{phrases?: string[]}> = ({phrases = PHRASES}) => {
  const dna = useDNA();
  const t = useT();
  // a bold, slightly-shifting saturated gradient (deterministic drift) — or the DNA's accent field on a themed film
  const a = 220 + Math.sin(t * 2) * 8;
  const flood = dna ? `linear-gradient(135deg, ${dna.accent}, ${dna.accent2})` : `linear-gradient(135deg, hsl(${a} 90% 46%), hsl(${a + 40} 84% 40%))`;
  return (
    <AbsoluteFill style={{background: flood}}>
      {/* a faint moving light band for depth */}
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(60% 60% at ${30 + t * 40}% 30%, rgba(255,255,255,.16), transparent)`}} />
      {phrases.map((p, i) => {
        const span = 0.42, start = 0.06 + i * (span - 0.12); // overlap so words fly through continuously
        return <Word key={i} text={p} start={start} span={span} t={t} hero={i === HERO} />;
      })}
    </AbsoluteFill>
  );
};
export default KineticManifesto;
