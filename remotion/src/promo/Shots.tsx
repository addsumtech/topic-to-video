// PROMO · Shots — more building blocks for a film whose STRUCTURE is designed per product (references/promo-film.md
// §design). None of these is a slot in a fixed sequence: a film may open on any of them, use any of them twice, or
// none at all. Each is a pure function of its frame.
//   statement  one line of display type, word by word out of a blur, on paper / the accent / ink — then still
//   compare    the same region of two captures (before | after, A | B) with a divider sweeping across
//   montage    a quick run of the product's own crops, each landing and holding a beat (a montage, not a slideshow)
//   Subtitles  the narration's lines, timed to the voice (promo_film writes them)
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {span, useLook, parseUnits, typeScale, isDarkHex, isCJK, alpha, SERIF, SANS, MONO, type Box} from './kit';
import {CardGround, inkOn} from './Cards';
import {BASELINE_UNLOCK} from '../runtime/glide';

const U = BASELINE_UNLOCK;
const urlOf = (src: string) => (/^(https?:|data:|\/)/.test(src) ? src : staticFile(src));

export type Region = {src: string; w: number; h: number; box: Box};

/** One region of a capture, drawn to fit a frame box (contain), from the 2x pixels. */
const RegionView: React.FC<{r: Region; W: number; H: number; radius?: number; style?: React.CSSProperties}> = ({r, W, H, radius = 14, style}) => {
  const k = Math.min(W / r.box.w, H / r.box.h);
  return (
    <div style={{position: 'relative', width: r.box.w * k, height: r.box.h * k, overflow: 'hidden', borderRadius: radius, ...style}}>
      <Img src={urlOf(r.src)} style={{position: 'absolute', left: -r.box.x * k, top: -r.box.y * k, width: r.w * k, height: r.h * k, maxWidth: 'none'}} />
    </div>
  );
};

/** STATEMENT: one line in display type, sized to the frame, each word arriving out of a 6 px blur 2 frames after the
 *  last (no slide: a landed title is still), the accent span in the accent ink; it leaves on a short blur-out. */
export const Statement: React.FC<{text: string; dur: number; ground?: 'paper' | 'accent' | 'ink'; size?: number; sub?: string}> = (
  {text, dur, ground = 'paper', size, sub}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const units = parseUnits(text);
  const cjk = isCJK(text);
  const chars = units.reduce((n, u) => n + (cjk ? 1 : u.text.length + 1), 0);
  const px = size ? size * s : Math.min(170 * s, (W * 0.84) / Math.max(4, chars * (cjk ? 1.0 : 0.52)) * (chars > 26 ? 1.7 : 1));
  const bg = ground === 'accent' ? look.accent : ground === 'ink' ? look.ink : look.paper;
  // on any ground but the paper, the ink that reads best on it from the film's own (on a dark look `ink` IS the light
  // colour: the old rule drew cream type on the cream `ink` ground, an empty frame)
  const fg = ground === 'paper' ? look.ink : inkOn(bg, [look.paper, look.ink, '#ffffff', '#141413']);
  const acc = ground === 'paper' ? look.accentInk : fg;
  const out = span(frame, dur - 6, dur, 'exit');
  const body = (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: `0 ${80 * s}px`}}>
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', maxWidth: W * 0.88, fontFamily: look.display ?? SANS, fontSize: px,
        fontWeight: 720, lineHeight: 1.04, letterSpacing: cjk ? '0.01em' : '-0.035em', color: fg, transform: U,
        filter: out > 0 ? `blur(${out * 8}px)` : undefined, opacity: 1 - out}}>
        {units.map((u, i) => {
          const t = span(frame, 2 + i * 2, 6 + i * 2, 'out');
          return (
            <span key={i} style={{opacity: t, filter: t < 1 ? `blur(${(1 - t) * 6}px)` : undefined, marginRight: u.space ? '0.22em' : 0,
              ...(u.accent ? {color: acc, fontFamily: !cjk ? SERIF : undefined, fontStyle: !cjk ? 'italic' : 'normal', fontWeight: !cjk ? 560 : 720} : {})}}>
              {u.text}
            </span>
          );
        })}
      </div>
      {sub ? <div style={{marginTop: 34 * s, fontFamily: MONO, fontSize: 24 * s, letterSpacing: '0.16em', textTransform: 'uppercase', color: alpha(fg, 0.7),
        opacity: span(frame, 10, 20, 'out') * (1 - out)}}>{sub}</div> : null}
    </AbsoluteFill>
  );
  return ground === 'paper' ? <CardGround>{body}</CardGround> : <AbsoluteFill style={{background: bg}}>{body}</AbsoluteFill>;
};

/** COMPARE: the same region of two captures side by side as one picture, a divider sweeping across it to reveal the
 *  second over the first; each side named by the product's own words. The camera does not move (a comparison is read). */
export const Compare: React.FC<{a: Region; b: Region; labelA?: string; labelB?: string; at?: number; sweep?: number; dur: number}> = (
  {a, b, labelA, labelB, at = 10, sweep = 26}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const fw = W * 0.84, fh = H * 0.74;
  const k = Math.min(fw / a.box.w, fh / a.box.h);
  const pw = a.box.w * k, ph = a.box.h * k;
  const p = span(frame, at, at + sweep, 'smooth');
  const inn = span(frame, 0, 10, 'snappy');
  const chip = (t: string, side: 'l' | 'r', on: number) => (
    <div style={{position: 'absolute', top: 18 * s, [side === 'l' ? 'left' : 'right']: 18 * s, padding: `${8 * s}px ${14 * s}px`, borderRadius: 999,
      background: 'rgba(16,16,18,0.78)', color: '#fff', fontFamily: SANS, fontSize: 22 * s, fontWeight: 650, opacity: on, transform: U}}>{t}</div>
  );
  return (
    <CardGround>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{position: 'relative', width: pw, height: ph, borderRadius: 16 * s, overflow: 'hidden', opacity: inn,
          transform: `scale(${0.96 + 0.04 * inn}) ${U}`, boxShadow: '0 30px 80px rgba(0,0,0,0.22), 0 0 0 1px rgba(0,0,0,0.06)'}}>
          <RegionView r={a} W={pw} H={ph} radius={0} style={{position: 'absolute', left: 0, top: 0}} />
          {/* B is revealed BEHIND the divider: everything left of it is already the second picture */}
          <div style={{position: 'absolute', inset: 0, clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`}}>
            <RegionView r={b} W={pw} H={ph} radius={0} style={{position: 'absolute', left: 0, top: 0}} />
          </div>
          <div style={{position: 'absolute', top: 0, bottom: 0, left: pw * p - 2, width: 4, background: '#fff', opacity: p > 0 && p < 1 ? 1 : p >= 1 ? 0.0 : 0,
            boxShadow: `0 0 18px ${alpha(look.accent, 0.8)}`}} />
          {labelA ? chip(labelA, 'l', span(frame, at - 6, at + 4, 'out') * (1 - span(frame, at + sweep * 0.4, at + sweep * 0.7, 'smooth'))) : null}
          {labelB ? chip(labelB, 'r', span(frame, at + sweep * 0.6, at + sweep, 'out')) : null}
        </div>
      </AbsoluteFill>
    </CardGround>
  );
};

/** MONTAGE: the product's own regions in quick succession (`every` frames each, 8-18), each landing out of a slight
 *  scale and a blur and then HOLDING — fast in the cut, still in the frame. */
export const Montage: React.FC<{items: Region[]; every?: number; dur: number; full?: boolean}> = ({items, every = 12, full = false}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const s = typeScale(W, H);
  const i = Math.min(items.length - 1, Math.floor(frame / every));
  if (i < 0 || !items.length) return null;
  const t = span(frame - i * every, 0, 6, 'snappy');
  const r = items[i];
  const fw = W * (full ? 1 : 0.8), fh = H * (full ? 1 : 0.74);
  return (
    <CardGround>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{transform: `scale(${0.94 + 0.06 * t}) ${U}`, filter: t < 1 ? `blur(${(1 - t) * 8}px)` : undefined,
          boxShadow: full ? undefined : '0 26px 70px rgba(0,0,0,0.22)', borderRadius: full ? 0 : 14 * s, overflow: 'hidden'}}>
          <RegionView r={r} W={fw} H={fh} radius={full ? 0 : 14 * s} />
        </div>
      </AbsoluteFill>
    </CardGround>
  );
};

export type Sub = {from: number; to: number; text: string; pos?: 'top' | 'bottom'};
/** SUBTITLES: the voice's line on screen while it is spoken, low and centred on a soft plate (the frame's own ground
 *  shows through it) — or at the top, `pos: 'top'`, where the page's own text fills the bottom (promo_film decides).
 *  Timed by promo_film from the voice's word boundaries. */
export const Subtitles: React.FC<{subs: Sub[]}> = ({subs}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const cur = subs.find((x) => frame >= x.from && frame < x.to);
  if (!cur) return null;
  const o = span(frame, cur.from, cur.from + 5, 'out') * (1 - span(frame, cur.to - 5, cur.to, 'exit'));
  const dark = isDarkHex(look.paper);
  return (
    <AbsoluteFill style={{justifyContent: cur.pos === 'top' ? 'flex-start' : 'flex-end', alignItems: 'center', pointerEvents: 'none',
      ...(cur.pos === 'top' ? {paddingTop: H * (H > W ? 0.12 : 0.07)} : {paddingBottom: H * (H > W ? 0.16 : 0.07)})}}>
      <div style={{maxWidth: W * 0.72, textAlign: 'center', fontFamily: SANS, fontSize: 34 * s, fontWeight: 600, lineHeight: 1.3, color: dark ? '#f4f3ef' : '#141413',
        padding: `${10 * s}px ${22 * s}px`, borderRadius: 14 * s, background: dark ? 'rgba(14,14,16,0.62)' : 'rgba(255,255,255,0.80)',
        backdropFilter: 'blur(10px)', opacity: o, transform: U}}>{cur.text}</div>
    </AbsoluteFill>
  );
};

/** THROUGH: a cut that goes INTO the frame — the leaving shot pushes through a point (scale x2.4, blurring), the arriving
 *  one comes out of the same point (from x0.55). For one thing opening into the next (a button into its result). */
export const throughStyle = (frame: number, dur: number, inn: boolean, out: boolean, at: {x: number; y: number} = {x: 0.5, y: 0.5}): React.CSSProperties => {
  const k = 9;
  const o = out ? span(frame, dur - k, dur, 'exit') : 0;
  const i = inn ? 1 - span(frame, 0, k, 'snappy') : 0;
  const sc = (1 + o * 1.4) * (1 - i * 0.45);
  const blur = o * 18 + i * 12;
  return {transform: `scale(${sc}) ${U}`, transformOrigin: `${at.x * 100}% ${at.y * 100}%`, filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
    opacity: 1 - Math.max(0, o - 0.6) * 2.5};
};
