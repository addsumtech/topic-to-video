// PROMO · Cards — the screen-level shots of a product film: the brand open, the serif title card (the film's breath
// between product shots), the flash cut, the caption strip and the outro assembly (references/promo-film.md §cards).
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {span, useLook, parseWords, hash01, SERIF, MONO, type Box} from './kit';
import {Crop} from './Layers';

const urlOf = (src: string) => (/^(https?:|data:|\/)/.test(src) ? src : staticFile(src));

/** The paper the cards are printed on: the look's paper, a warm top light, a faint vignette. */
const Paper: React.FC<{children?: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => {
  const look = useLook();
  return (
    <AbsoluteFill style={{background: look.paper, ...style}}>
      <AbsoluteFill style={{background: 'radial-gradient(60% 55% at 50% 40%, rgba(255,255,255,0.85), rgba(255,255,255,0) 70%)'}} />
      <AbsoluteFill style={{background: 'radial-gradient(130% 100% at 50% 45%, rgba(0,0,0,0) 62%, rgba(40,32,20,0.08) 100%)'}} />
      {children}
    </AbsoluteFill>
  );
};

/** TITLE CARD: one serif statement, letterpressed word by word (each word lands from 1.28x and a blur), the accent
 *  word(s) in the true italic and the accent ink, an accent rule drawing under it; the card breathes in (a slow 2.5 %
 *  push) and leaves on a short fade. 1.6-2.2 s is the band: long enough to read, short enough to stay a breath. */
export const TitleCard: React.FC<{text: string; dur: number; sub?: string; size?: number}> = ({text, dur, sub, size = 112}) => {
  const frame = useCurrentFrame();
  const {width: W} = useVideoConfig();
  const look = useLook();
  const s = W / 1920;
  const words = parseWords(text);
  const out = span(frame, dur - 8, dur, 'exit');
  const push = 1 + 0.025 * span(frame, 0, dur, 'linear');
  const rule = span(frame, 6 + words.length * 3, 22 + words.length * 3, 'snappy');
  return (
    <Paper style={{opacity: 1 - out}}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `scale(${push})`}}>
        <div style={{maxWidth: 1560 * s, textAlign: 'center'}}>
          <div style={{fontFamily: SERIF, fontSize: size * s, fontWeight: 600, lineHeight: 1.12, letterSpacing: '-0.015em', color: look.ink,
            display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: '0.26em'}}>
            {words.map((w, i) => {
              const t = span(frame, 3 + i * 3.5, 12 + i * 3.5, (x) => 1 - Math.pow(1 - x, 3));
              return (
                <span key={i} style={{display: 'inline-block', opacity: t, transform: `scale(${1.28 - 0.28 * t})`, filter: `blur(${(1 - t) * 7}px)`,
                  fontStyle: w.accent ? 'italic' : 'normal', fontWeight: w.accent ? 560 : 600, color: w.accent ? look.accentInk : undefined}}>{w.text}</span>
              );
            })}
          </div>
          <div style={{height: 6 * s, width: 200 * s, margin: `${36 * s}px auto 0`, borderRadius: 3 * s, background: look.accent,
            transform: `scaleX(${rule})`}} />
          {sub ? <div style={{marginTop: 30 * s, fontFamily: MONO, fontSize: 24 * s, letterSpacing: '0.16em', textTransform: 'uppercase',
            color: look.muted, opacity: span(frame, 12, 24, 'out')}}>{sub}</div> : null}
        </div>
      </AbsoluteFill>
    </Paper>
  );
};

/** FLASH CUT: a soft bright bloom straddling a hard cut (5 frames each side). Only on cuts, never as decoration. */
export const FlashCut: React.FC<{dur?: number; strength?: number}> = ({dur = 10, strength = 0.75}) => {
  const frame = useCurrentFrame();
  const o = frame < dur * 0.45 ? span(frame, 0, dur * 0.45, 'out') : 1 - span(frame, dur * 0.45, dur, 'smooth');
  return <AbsoluteFill style={{pointerEvents: 'none', opacity: o * strength,
    background: 'radial-gradient(ellipse at 50% 45%, rgba(255,253,248,1), rgba(255,250,240,0.6) 55%, rgba(255,250,240,0) 82%)'}} />;
};

/** CAPTION STRIP: a short mono line under a product shot (what is happening, in capitals), never over a card. */
export const CaptionStrip: React.FC<{text: string; dur: number}> = ({text, dur}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = W / 1920;
  const o = span(frame, 0, 10, 'out') * (1 - span(frame, dur - 8, dur, 'exit'));
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: H * 0.07, pointerEvents: 'none'}}>
      <div style={{opacity: o, transform: `translateY(${(1 - o) * 10 * s}px)`, fontFamily: MONO, fontSize: 22 * s, fontWeight: 600,
        letterSpacing: '0.18em', textTransform: 'uppercase', color: look.ink, padding: `${10 * s}px ${20 * s}px`, borderRadius: 999,
        background: 'rgba(255,255,255,0.86)', boxShadow: '0 6px 24px rgba(20,18,14,0.14)', backdropFilter: 'blur(6px)'}}>
        <span style={{color: look.accentInk, marginRight: '0.7em'}}>●</span>{text}
      </div>
    </AbsoluteFill>
  );
};

/** The brand lockup from one SVG: an icon square at the left (its width = the SVG's height, `iconRatio` of the
 *  height) and the wordmark after it. Drawn as two clipped copies of the same file, so each part can move alone. */
const Lockup: React.FC<{mark: string; aspect: number; h: number; icon: number; word: number; iconScale?: number}> = (
  {mark, aspect, h, icon, word, iconScale = 1}) => {
  const w = h * aspect;
  const iconW = h * 1.08;
  return (
    <div style={{position: 'relative', width: w, height: h}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: iconW, height: h, overflow: 'hidden', opacity: Math.min(1, icon * 1.5),
        transform: `scale(${iconScale * (0.6 + 0.4 * icon)})`, transformOrigin: `${h / 2}px ${h / 2}px`}}>
        <Img src={urlOf(mark)} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
      </div>
      <div style={{position: 'absolute', left: iconW, top: 0, width: w - iconW, height: h, overflow: 'hidden',
        clipPath: `inset(0 ${(1 - word) * 100}% 0 0)`}}>
        <Img src={urlOf(mark)} style={{position: 'absolute', left: -iconW, top: 0, width: w, height: h,
          transform: `translateX(${(1 - word) * -24}px)`}} />
      </div>
    </div>
  );
};

/** BRAND OPEN: the icon lands (one overshoot), the wordmark wipes on beside it, a kicker types under it; the lockup
 *  RESTS fully on for a second, then lifts and dissolves into the first product shot. */
export const BrandOpen: React.FC<{mark: string; aspect: number; kicker?: string; dur: number; markH?: number}> = ({mark, aspect, kicker = '', dur, markH = 170}) => {
  const frame = useCurrentFrame();
  const {width: W} = useVideoConfig();
  const look = useLook();
  const s = W / 1920;
  const icon = span(frame, 2, 18, 'overshoot');
  const word = span(frame, 12, 30, 'snappy');
  const kStart = 26, n = Math.max(0, Math.min(kicker.length, Math.floor((frame - kStart) / 0.8)));
  const out = span(frame, dur - 12, dur, 'exit');
  const sheen = span(frame, 20, 44, 'smooth');
  return (
    <Paper style={{opacity: 1 - out}}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `translateY(${-out * 40 * s}px) scale(${1 - out * 0.1})`}}>
        <div style={{position: 'relative'}}>
          <Lockup mark={mark} aspect={aspect} h={markH * s} icon={icon} word={word} />
          <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'soft-light',
            background: `linear-gradient(100deg, transparent ${sheen * 120 - 30}%, rgba(255,255,255,0.9) ${sheen * 120 - 15}%, transparent ${sheen * 120}%)`}} />
        </div>
        {kicker ? <div style={{marginTop: 40 * s, height: 30 * s, fontFamily: MONO, fontSize: 24 * s, letterSpacing: '0.2em', textTransform: 'uppercase',
          color: look.muted}}>{kicker.slice(0, n)}<span style={{opacity: n < kicker.length || Math.floor(frame / 12) % 2 ? 1 : 0, color: look.accentInk}}>▍</span></div> : null}
      </AbsoluteFill>
    </Paper>
  );
};

export type Piece = {src: string; pageW: number; pageH: number; box: Box; x: number; y: number; rot?: number; scale?: number};

/** OUTRO ASSEMBLY: pieces of the product (crops of its own pages) fly in from off-frame one after another and settle
 *  round the centre like a group photo; then they step back (smaller, softer) as the lockup STAMPS in the middle
 *  (from 1.35x and a blur, one overshoot), rules shoot out either side, the tagline sets in the serif italic, and
 *  the whole frame holds a full second. */
export const OutroAssembly: React.FC<{pieces: Piece[]; mark: string; aspect: number; tagline?: string; dur: number; stampAt?: number; markH?: number}> = (
  {pieces, mark, aspect, tagline = '', dur, stampAt = 46, markH = 150}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = W / 1920;
  const back = span(frame, stampAt - 6, stampAt + 8, 'smooth');
  const crane = 1.08 - 0.08 * span(frame, 0, stampAt, 'smooth') + 0.02 * span(frame, stampAt, dur, 'linear');
  const stamp = span(frame, stampAt, stampAt + 12, 'overshoot');
  const stampO = span(frame, stampAt, stampAt + 6, 'out');
  const rules = span(frame, stampAt + 12, stampAt + 22, 'snappy');
  const tag = span(frame, stampAt + 14, stampAt + 28, 'snappy');
  return (
    <Paper>
      <AbsoluteFill style={{transform: `scale(${crane})`}}>
        {pieces.map((p, i) => {
          const at = 2 + i * (28 / Math.max(1, pieces.length - 1 || 1));
          const t = span(frame, at, at + 16, 'snappy');
          const tx = p.x * W, ty = p.y * H;
          const dx = tx - W / 2, dy = ty - H / 2, len = Math.hypot(dx, dy) || 1;
          const fromX = tx + (dx / len) * W * 0.7, fromY = ty + (dy / len) * H * 0.7 + 60 * s;
          const sc = (p.scale ?? 1) * s * (1 - 0.1 * back);
          const x = fromX + (tx - fromX) * t, y = fromY + (ty - fromY) * t;
          const rot = (p.rot ?? 0) * t + (1 - t) * (hash01(i) - 0.5) * 24;
          const land = span(frame, at + 12, at + 22, 'out') * (1 - span(frame, at + 22, at + 34, 'smooth'));
          return (
            <div key={i} style={{position: 'absolute', left: x, top: y, width: p.box.w, height: p.box.h, opacity: Math.min(1, t * 2) * (1 - 0.3 * back),
              transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${sc})`, filter: `blur(${1.4 * back}px)`}}>
              <div style={{position: 'absolute', inset: -30, borderRadius: 30, background: `radial-gradient(closest-side, ${look.accent}66, transparent)`, opacity: land}} />
              <Crop src={p.src} pageW={p.pageW} pageH={p.pageH} box={p.box} radius={12}
                style={{left: 0, top: 0, boxShadow: `0 ${8 + 20 * (1 - t)}px ${24 + 40 * (1 - t)}px rgba(20,18,14,0.20), 0 0 0 1px rgba(20,18,14,0.06)`}} />
            </div>
          );
        })}
      </AbsoluteFill>
      {/* a stage light behind the lockup as it lands */}
      <AbsoluteFill style={{background: `radial-gradient(34% 30% at 50% 48%, rgba(255,255,255,${0.95 * back}), rgba(255,255,255,0) 100%)`}} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{opacity: stampO, transform: `scale(${1.35 - 0.35 * stamp})`, filter: `blur(${(1 - stampO) * 10}px)`}}>
          <Lockup mark={mark} aspect={aspect} h={markH * s} icon={1} word={1} />
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 22 * s, marginTop: 34 * s}}>
          <div style={{height: 2, width: 160 * s * rules, background: look.accent, opacity: 0.8}} />
          <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: 46 * s, fontWeight: 500, color: look.ink, opacity: tag,
            transform: `translateY(${(1 - tag) * 12 * s}px)`, letterSpacing: '-0.005em'}}>{tagline}</div>
          <div style={{height: 2, width: 160 * s * rules, background: look.accent, opacity: 0.8}} />
        </div>
      </AbsoluteFill>
    </Paper>
  );
};
