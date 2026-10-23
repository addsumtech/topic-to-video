// KINETIC PROBE — the frames tests/test_kinetic.py renders to prove two things about runtime/kinetic.tsx:
//
//   1. a settled KineticText IS its text: `settled` and `reference` draw the same copy, once as glyphs placed from a
//      measured reference and once as one plain text node, and the two must be the same pixels (kerning, CJK
//      punctuation compression and line breaking all kept — the research measured 0 px; this holds the line);
//   2. the gates still see it: `cut` runs a line off the frame, `band` sets one in the caption band, `drift` crawls a
//      line by 0.3 px a frame (a staircase with the unlock off, `baselineUnlock: false`), `leading` pulls two lines of
//      a block into each other with a range selector, `swap` cycles alternatives faster than they can be read.
// Every one must be found, ONCE, by its line's text — and the clean twins must come back clean.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useKinetic, KineticText, KMotion, KSpec} from './kinetic';
import {captionBand} from './layout';

export const DURATION = 90;

const FAMILY = 'Inter, "Noto Sans SC", system-ui, sans-serif';
const LATIN = 'AVATAR Wave To office flyaway — Type, kerned *as it was set*';
const CJK = '“你好，世界。”（测试）「引用」、完。我们今天讨论运动图形设计';

export const KineticProbe: React.FC<{variant?: string; text?: string; lang?: string; size?: number;
  align?: 'left' | 'center' | 'right'}> = ({variant = 'settled', text, lang, size = 84, align = 'left'}) => {
  const {width: W, height: H} = useVideoConfig();
  const copy = text ?? (lang === 'zh' ? CJK : LATIN);
  const x = Math.round(W * 0.07), y = Math.round(H * 0.18), w = Math.round(W * 0.8);
  const font = {family: FAMILY, weight: 500, size, lineHeight: 1.2, tracking: -0.01};
  // phrase breaking OFF here: this probe is about where glyphs land, against a plain text node set the plain way
  let spec: KSpec = {text: copy, font, w, align, wrap: 'balance', fit: 'none', keepPhrases: false};
  let motion: KMotion = {};
  let px = x, py = y;
  if (variant === 'cut') { spec = {...spec, nowrap: true}; px = W - Math.round(W * 0.25); }
  if (variant === 'band') {
    spec = {...spec, nowrap: true, w: Math.round(W * 0.86), text: 'Set in the caption band'};
    py = H - captionBand(W, H) + 10;
  }
  if (variant === 'drift' || variant === 'drift-ok') {
    // 0.3 px a frame at 30 fps, as em per second at this size: the crawl a slow camera push makes
    spec = {...spec, nowrap: true, text: 'Drifting line'};
    motion = {drift: {y: (0.3 * 30) / size}};
  }
  if (variant === 'leading') {
    spec = {...spec, text: ['第一行文字在这里', '第二行文字在这里', '第三行文字在这里'], lang: 'zh'};
    // lines 2 and 3 held 0.8 em up by a SQUARE range over the last two thirds of the lines — a block set into itself
    motion = {enter: {by: 'line', at: 0, dur: 0.1, selector: {start: 1 / 3, end: 1, shape: 'square', from: 0, to: 0}},
      from: {y: -0.8}};
  }
  if (variant === 'swap' || variant === 'swap-ok') {
    const many = variant === 'swap';
    spec = {alts: many ? ['faster', 'cheaper', 'smaller', 'quieter', 'simpler', 'safer'] : ['faster', 'cheaper'],
      font: {...font, size: 120}, w, nowrap: true, fit: 'none'};
    motion = {swap: {mode: 'roll', first: 0.3, last: many ? 0.8 : 0.3}};
  }
  if (variant === 'path') {
    spec = {...spec, nowrap: true, text: 'along a curve'};
    motion = {path: {d: `M 0 ${H * 0.3} C ${w * 0.3} ${H * 0.05}, ${w * 0.6} ${H * 0.55}, ${w} ${H * 0.25}`, at: w * 0.2,
      travel: w * 0.2, enter: {at: 0.1, dur: 1.2}}};
  }
  const k = useKinetic(spec);
  const ref = variant === 'reference';
  return (
    <AbsoluteFill style={{background: '#ffffff'}}>
      {ref ? (
        <div lang={spec.lang ?? (lang === 'zh' ? 'zh' : 'en')} style={{position: 'absolute', left: x, top: y, width: w, fontFamily: FAMILY,
          fontWeight: 500, fontSize: size, lineHeight: `${size * 1.2}px`, letterSpacing: '-0.01em', color: '#111',
          textAlign: align, whiteSpace: 'pre-line', fontVariantLigatures: 'none', textWrap: 'balance'} as React.CSSProperties}>
          {copy.replace(/\*/g, '')}
        </div>
      ) : null}
      {ref ? k.anchor : (
      <KineticText k={k} x={px} y={py} color="#111" emphColor="#111" motion={motion} id={`probe-${variant}`}
          read={variant !== 'drift' && variant !== 'drift-ok'} />
      )}
    </AbsoluteFill>
  );
};
