// SHOT · Kinetic Manifesto — Linear/Framer language: screen-filling phrases RUSH toward the viewer on the
// Z-axis, one after another, each snapping sharp at reading size then blowing past into blur as the next
// arrives. Bold SATURATED colour field (deliberately loud + unlike every other shot). Deterministic;
// motion-blur approximated by CSS blur on the fast approach/exit (frame-safe, no ancestor-flatten).

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, easeOutCubic, clamp01} from '../runtime/motion';
import {leading} from '../runtime/cjkType';
import {CONTENT_TOP, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {useDNA} from '../runtime/dna';

export const DURATION = 150; // 5s
// LEVEL-C: the loud saturated colour FIELD is this shot's identity, so it's KEPT as a field — but on a themed DNA
// the field becomes the DNA's accent→accent2 gradient (a green flood on terminal, etc.) and the words use on-accent.
// Null DNA = the original bold blue/yellow. Word reads useDNA itself (module-scope subcomponent).
//
// THE HERO WORD USED TO BE PAINTED IN ONE OF THE TWO COLOURS OF ITS OWN GROUND. The flood is
// `linear-gradient(135deg, accent, accent2)` and the hero ink was `accent2` — the colour the gradient
// reaches at its far end. Measured across all eight shipped presets: 1.00:1 exactly there, and 1.03–2.08:1
// at the flood's middle where the word actually sits (1.31:1 read off a rendered `terminal` frame). HERO is
// the LAST phrase, so the film ended on the one line nobody could read.
//
// AND THE EMPHASIS CANNOT BE A SECOND HUE — that is structural, not taste. The ground IS the two accents,
// and `onAccent` is the only token the DNA contract guarantees against them (5.9–10.1:1 measured across the
// presets; `fg` is 1.67:1 there, `bg` is a different near-black indistinguishable from `onAccent`). The
// phrases also never share the screen — each Word returns null outside its own window — so the emphasis was
// never a comparison in the first place. Every word takes the one readable ink at full strength and the
// hero is the one that lands at FULL SIZE, the others a step under it. Size costs no contrast.
const PHRASES = ['ONE PROMPT.', 'A HUNDRED EXPERTS.', 'YOUR AI TEAM.'];
const HERO = 2; // which phrase pops in the accent colour

const Word: React.FC<{text: string; start: number; span: number; t: number; hero: boolean}> = ({text, start, span, t, hero}) => {
  const dna = useDNA();
  const {width: W, height: H} = useVideoConfig();
  // A null DNA keeps the original bold yellow-on-blue pair, which was never the failure: that flood is a
  // mid-dark hsl field and both inks are light on it.
  const ink = dna?.onAccent ?? null;
  // AND 200px IS A LATIN NUMBER. Every Han glyph is a full em, so a Chinese manifesto line at 200px is
  // about four frames wide: fed '把重复的步骤交给它，自己去做只有你能做的那部分工作' it wrapped past both edges
  // AND 692px into the caption band at 1:1. The size is fitted to the box the words actually get — the
  // 82%-wide column between the title band and the caption — the same way MagazineSpread fits its
  // headline. Latin demo copy keeps 200 exactly, so nothing that ships today moves.
  const heroC = ink ?? '#FFE24D', normC = ink ?? '#ffffff';
  const lead = leading(text, 0.95);
  const zone = contentBottom(W, H) - CONTENT_TOP;
  // THE MEASURE IS STATED, NOT INFERRED. It was `maxWidth: 82%` plus `padding: 0 60px` on a flex item, and
  // what the browser then wrapped in was not the number this file computed: the estimate said three lines
  // and the frame drew FOUR, so the fit believed it fitted and the fourth line went into the caption band.
  // An explicit width with border-box sizing makes the number the type wraps in and the number the fit
  // reasons about the same number — which is the only version of this that cannot drift apart.
  const measure = Math.max(120, Math.round(W * 0.82) - 120);
  const px = Math.round(fitBlockPx(text, measure, zone, 200, {leading: lead, usable: 1}));
  // AND THE WORD RUSHES PAST, so the SETTLED size is not the size the frame has to hold. The depart phase
  // scales to 1.9, and a transform does not change layout but it does change what is drawn: fitted to the
  // zone at rest, a three-line Chinese phrase then swelled 117px into the caption band on its way out. The
  // rush is clamped to what the zone can take instead of the type being shrunk to make room for a 1.9 that
  // a one-line Latin phrase never needs — Latin fits 3x over, so `departTo` is 1.9 there and nothing that
  // ships today moves.
  const blockH = wrapLines(text, px, measure) * px * lead;   // the same count the fit used
  const departTo = Math.min(1.9, Math.max(1.02, zone / blockH));
  const lp = clamp01((t - start) / span);
  if (t < start - 0.02 || lp >= 1) return null;
  // WHERE THE WORD SETTLES. The hero lands at reading size and the rest a step under it — the step a viewer
  // reads as one phrase mattering more, taken in the one dimension that cannot cost legibility. Shrinking is
  // also the safe direction: the type is 200px in an 82%-wide box and a longer phrase already wraps there.
  const settle = hero || !ink ? 1.0 : 0.86;
  // approach (0-.22): far+blur+fade-in → hold (.22-.62): reading size, sharp → depart (.62-1): rush past, blur+fade
  const scale = lp < 0.62 ? lerp(0.62 * settle, settle, easeOutCubic(clamp01(lp / 0.22)))
                          : lerp(settle, departTo * settle, easeOutCubic((lp - 0.62) / 0.38));
  const op = lp < 0.18 ? lp / 0.18 : lp > 0.72 ? clamp01((1 - lp) / 0.28) : 1;
  const blur = lp < 0.16 ? 18 * (1 - lp / 0.16) : lp > 0.66 ? 26 * ((lp - 0.66) / 0.34) : 0;
  // CENTRED ON THE CONTENT ZONE, NOT ON THE FRAME. The fit above sizes the block to the zone, and then
  // centring it on H/2 pushed the extra half of a tall (Chinese) block straight through the caption band
  // anyway — the size was right and the anchor was not. The padding makes the flex centre the zone's
  // centre; on a 16:9 frame that is 12px from where it was.
  return (
    <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center',
      paddingTop: CONTENT_TOP, paddingBottom: H - contentBottom(W, H)}}>
      <div style={{font: `900 ${px}px/${lead} var(--f-display, Inter,system-ui,sans-serif)`, letterSpacing: '-0.03em', textAlign: 'center',
        color: hero ? heroC : normC, opacity: op, transform: `scale(${scale})`,
        filter: blur > 0.5 ? `blur(${blur}px)` : undefined, textShadow: '0 20px 60px rgba(0,0,0,.25)',
        boxSizing: 'content-box', width: measure, padding: '0 60px'}}>{text}</div>
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
