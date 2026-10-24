// MATH PROBE — fixtures for tests/test_math_morph.py. Not a register: every variant isolates one claim.
//
//   reference  MathJax's OWN svg markup for the stress equation (a public-dir file the test writes), as an image
//   glyphs     the same equation drawn by runtime/mathMorph from the typeset glyph file, at the same place and size
//              → the two must be the same picture: the typesetter's transform composition, rules, nested viewports
//                (stretchy extenders, clipped) and stroked frames all reproduced
//   cut / band / ok / overlap   the type gates reading an equation as one line named by its TeX
//   morph      a + b = c → a = c − b at progress `p` (the matched b travels on an arc over the equals sign)
//   live       a live number slot at progress `p`
import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {captionBand} from './layout';
import {useEquations, MathLayer, stillState, matchGlyphs, transformState, liveDraws, liveText, placeAll,
  writeState} from './mathMorph';

export const DURATION = 90;
export const PROBE_STRESS = '\\sum_{k=1}^{n} \\frac{1}{k^2} \\le \\sqrt{\\frac{\\pi^2}{6}} + \\overbrace{a+b}^{n} + ' +
  '\\boxed{E=mc^2} + \\begin{pmatrix}1&0\\\\0&1\\end{pmatrix}';
const SIDES_A = '\\class{a}{a} + \\class{b}{b} = c', SIDES_B = '\\class{a}{a} = c - \\class{b}{b}';
const LIVE = 'T = \\class{live}{00.0}\\,\\mathrm{K}';

export const MathProbe: React.FC<{variant?: string; src?: string; p?: number; from?: string; to?: string}> = (
  {variant = 'glyphs', src = 'ref.svg', p = 0.5, from = '0.0', to = '37.5'}) => {
  const {width: W, height: H} = useVideoConfig();
  const eqs = useEquations([PROBE_STRESS, SIDES_A, SIDES_B, LIVE]);
  if (!eqs) return <AbsoluteFill style={{background: '#ffffff'}} />;
  const [stress, A, B, live] = eqs;
  const s = 1600 / stress.w;
  const at = {x: 160, y: 300, s};
  if (variant === 'reference') {
    return (
      <AbsoluteFill style={{background: '#ffffff'}}>
        <Img src={staticFile(src)} style={{position: 'absolute', left: at.x, top: at.y, width: stress.w * s,
          height: stress.h * s}} />
      </AbsoluteFill>
    );
  }
  if (variant === 'glyphs') {
    return (
      <AbsoluteFill style={{background: '#ffffff'}}>
        <MathLayer draws={stillState(stress, at, 'g')} tex={stress.tex} emPx={s * 1000} W={W} H={H} ink="#000000"
          accent="#000000" />
      </AbsoluteFill>
    );
  }
  if (variant === 'write') {
    return (
      <AbsoluteFill style={{background: '#ffffff'}}>
        <MathLayer draws={writeState(stress, at, p)} tex={stress.tex} emPx={s * 1000} W={W} H={H} ink="#000000"
          accent="#000000" />
      </AbsoluteFill>
    );
  }
  const small = 0.12;                      // 120 px em
  const bg = '#0c1016', ink = '#f1f3f7';
  if (variant === 'cut' || variant === 'band' || variant === 'ok' || variant === 'overlap') {
    const w = A.w * small;
    const x = variant === 'cut' ? W - w * 0.45 : (W - w) / 2;
    const y = variant === 'band' ? H - captionBand(W, H) * 0.7 : H * 0.35;
    return (
      <AbsoluteFill style={{background: bg}}>
        <MathLayer draws={stillState(A, {x, y, s: small}, 'q')} tex={A.tex} emPx={120} W={W} H={H} ink={ink}
          accent={ink} />
        {variant === 'overlap' ? (
          <div style={{position: 'absolute', left: x + w * 0.2, top: y + A.h * small * 0.25, color: '#ffb547',
            font: '600 64px Inter, sans-serif', whiteSpace: 'nowrap'}}>A label on the sum</div>
        ) : null}
      </AbsoluteFill>
    );
  }
  if (variant === 'morph') {
    const pl = placeAll([A, B], {x: W * 0.1, y: H * 0.3, w: W * 0.8, h: H * 0.3}, 140, 'equals');
    const m = matchGlyphs(A, B, pl.pl[0], pl.pl[1]);
    return (
      <AbsoluteFill style={{background: bg}}>
        <MathLayer draws={transformState(A, pl.pl[0], B, pl.pl[1], m, p)} tex={p < 0.5 ? A.tex : B.tex} emPx={140}
          W={W} H={H} ink={ink} accent="#ffb547" />
      </AbsoluteFill>
    );
  }
  // live
  const pl = {x: W * 0.3, y: H * 0.35, s: 0.14};
  const draws = stillState({...live, glyphs: live.glyphs.filter((g) => !g.k.includes('live'))}, pl, 'v')
    .concat(liveDraws(live, pl, 'live', liveText(from, to, p)));
  return (
    <AbsoluteFill style={{background: bg}}>
      <MathLayer draws={draws} tex={live.tex} emPx={140} W={W} H={H} ink={ink} accent="#ffb547" />
    </AbsoluteFill>
  );
};
export default MathProbe;
