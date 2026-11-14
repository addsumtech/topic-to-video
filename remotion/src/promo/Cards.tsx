// PROMO · Cards — the screen-level shots: brand open, chapter card, caption, cut carry, recall outro
// (references/promo-film.md §cards).
//
// OUR OWN LANGUAGE, distilled rather than copied. What the reference films taught is a set of PRINCIPLES — a card is a
// breath between product shots, it lands one statement, the brand moments rest a full second, a cut carries energy
// instead of dissolving it. The look that carries those principles here is ours:
//   · the CHAPTER card: the film's argument is numbered (01 / 04) and a hairline shows how far through it we are —
//     a narrated film's structure made visible; words RISE through a mask line (CJK by character); the accent span
//     fills with the accent colour like ink drawn across it, so the accent works in any script (no italic needed);
//     the card leaves by its words rising out, not by fading.
//   · the BRAND lockup grows out of a single accent dot.
//   · the OUTRO recalls the film: its own shots, live, as a wall that pulls back while the lockup forms over it.
import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {span, useLook, parseUnits, typeScale, isDarkHex, alpha, isCJK, contrast, SERIF, SANS, MONO} from './kit';
import {BASELINE_UNLOCK} from '../runtime/glide';

// Every transform that moves or scales TYPE here carries the baseline unlock (runtime/glide.ts): under a pure
// scale+translate Skia snaps each baseline to a whole pixel and slow motion becomes a staircase.
const U = BASELINE_UNLOCK;

const urlOf = (src: string) => (/^(https?:|data:|\/)/.test(src) ? src : staticFile(src));

/** The card ground: the look's paper, a key light in the accent's hue from the top, a vignette. Light or dark. */
export const CardGround: React.FC<{children?: React.ReactNode; style?: React.CSSProperties; key2?: {x: number; y: number}}> = (
  {children, style, key2 = {x: 0.5, y: 0.0}}) => {
  const look = useLook();
  const frame = useCurrentFrame();
  const dark = isDarkHex(look.paper);
  const drift = Math.sin(frame / 90) * 3;
  return (
    <AbsoluteFill style={{background: look.paper, ...style}}>
      <AbsoluteFill style={{background: `radial-gradient(75% 65% at ${key2.x * 100 + drift}% ${key2.y * 100}%, ${alpha(look.accent, dark ? 0.22 : 0.10)}, rgba(0,0,0,0) 70%)`}} />
      <AbsoluteFill style={{background: `radial-gradient(60% 50% at 50% 45%, ${dark ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.7)'}, rgba(255,255,255,0) 70%)`}} />
      <AbsoluteFill style={{background: `radial-gradient(130% 100% at 50% 45%, rgba(0,0,0,0) 60%, ${dark ? 'rgba(0,0,0,0.45)' : 'rgba(30,26,20,0.08)'} 100%)`}} />
      {children}
    </AbsoluteFill>
  );
};

/** A line set unit by unit, each rising through its own mask; the accent span filled with the accent colour once it
 *  has landed. `start`/`gap` in frames; `leaveAt` (a frame) sends the units up and out. */
export const RiseLine: React.FC<{text: string; px: number; start?: number; gap?: number; leaveAt?: number; weight?: number;
  family?: string; color?: string; align?: 'center' | 'left'; maxWidth?: number; lineHeight?: number; nowrap?: boolean}> = (
  {text, px, start = 2, gap = 3, leaveAt, weight = 680, family: familyIn, color, align = 'center', maxWidth, lineHeight = 1.1, nowrap = false}) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const family = familyIn ?? look.display ?? SANS;
  const units = parseUnits(text);
  const n = units.length;
  const cjk = isCJK(text);
  const g = cjk ? Math.min(gap, 22 / Math.max(1, n)) * 1.4 : gap;  // a long Chinese line still lands within ~0.9 s
  const lastLand = start + (n - 1) * g + 12;
  return (
    <div style={{display: 'flex', flexWrap: nowrap ? 'nowrap' : 'wrap', justifyContent: align === 'center' ? 'center' : 'flex-start', maxWidth,
      whiteSpace: nowrap ? 'nowrap' : undefined, transform: U,
      fontFamily: family, fontSize: px, fontWeight: weight, lineHeight, letterSpacing: cjk ? '0.02em' : '-0.025em', color: color ?? look.ink}}>
      {units.map((u, i) => {
        const a = start + i * g;
        const t = span(frame, a, a + 12, 'snappy');
        const out = leaveAt !== undefined ? span(frame, leaveAt + i * 0.8, leaveAt + i * 0.8 + 8, 'exit') : 0;
        const y = (1 - t) * 105 - out * 105;
        const fill = u.accent ? span(frame, lastLand - 2 + i * 0.6, lastLand + 10 + i * 0.6, 'smooth') : 0;
        return (
          <span key={i} style={{display: 'inline-block', overflow: 'hidden', paddingBottom: '0.1em', marginBottom: '-0.1em',
            marginRight: u.space ? '0.24em' : 0}}>
            <span style={{display: 'inline-block', transform: `translateY(${y}%) ${U}`,
              ...(u.accent ? {backgroundImage: `linear-gradient(90deg, ${look.accentInk} ${fill * 100}%, ${color ?? look.ink} ${fill * 100}%)`,
                WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
                fontFamily: !cjk ? SERIF : family, fontStyle: !cjk ? 'italic' : 'normal', fontWeight: !cjk ? 560 : weight} : {})}}>{u.text}</span>
          </span>
        );
      })}
    </div>
  );
};

/** CHAPTER CARD: `01 / 04` and the chapter's kicker at the top left, one statement in the middle rising through its
 *  mask, a hairline across the foot showing the film's progress (this chapter's share drawn in the accent). */
export const ChapterCard: React.FC<{text: string; dur: number; index?: number; total?: number; kicker?: string; size?: number}> = (
  {text, dur, index, total, kicker, size = 104}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const portrait = H > W;
  // NO CREEP: a 2 % push over a card is ~0.1 px a frame at its type's edges — the speed at which strokes visibly
  // 'breathe' between pixel rows (PageCam CREEP). The card's life is its words rising and its accent filling.
  const push = 1;
  const meta = span(frame, 0, 10, 'out') * (1 - span(frame, dur - 8, dur, 'exit'));
  const p0 = index && total ? (index - 1) / total : 0, p1 = index && total ? index / total : 0;
  const bar = span(frame, 4, 22, 'snappy');
  const pad = 72 * s;
  return (
    <CardGround>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `scale(${push}) ${U}`, padding: `0 ${pad}px`}}>
        <RiseLine text={text} px={(portrait ? size * 0.92 : size) * s} start={3} leaveAt={dur - 9} maxWidth={W - 2 * pad} />
      </AbsoluteFill>
      {index ? (
        <div style={{position: 'absolute', left: pad, top: pad * 0.9, opacity: meta, display: 'flex', alignItems: 'baseline', gap: 18 * s,
          fontFamily: MONO, fontSize: 22 * s, letterSpacing: '0.16em', textTransform: 'uppercase', color: look.muted}}>
          <span style={{color: look.accentInk, fontWeight: 700, fontSize: 30 * s, letterSpacing: '0.04em'}}>{String(index).padStart(2, '0')}</span>
          {total ? <span>/ {String(total).padStart(2, '0')}</span> : null}
          {kicker ? <span style={{marginLeft: 10 * s, color: look.ink}}>{kicker}</span> : null}
        </div>
      ) : null}
      {index && total ? (
        <div style={{position: 'absolute', left: pad, right: pad, bottom: pad * 0.9, height: 2 * s, background: alpha(look.ink, 0.12), opacity: meta}}>
          <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${p0 * 100}%`, background: alpha(look.ink, 0.35)}} />
          <div style={{position: 'absolute', left: `${p0 * 100}%`, top: -1 * s, height: 4 * s, width: `${(p1 - p0) * 100 * bar}%`, background: look.accent,
            boxShadow: `0 0 ${10 * s}px ${alpha(look.accent, 0.6)}`}} />
        </div>
      ) : null}
    </CardGround>
  );
};
/** Back-compat name. */
export const TitleCard: React.FC<{text: string; dur: number; sub?: string; size?: number; index?: number; total?: number}> = (p) =>
  <ChapterCard text={p.text} dur={p.dur} size={p.size} index={p.index} total={p.total} kicker={p.sub} />;

/** CUT CARRY: a hard cut that carries one move through it. The leaving shot keeps travelling and smears; the arriving
 *  shot comes out of the same smear already moving. `dir` +1 = content travels left. Applied by PromoFilm round cuts. */
export const carryStyle = (frame: number, dur: number, dirIn: number, dirOut: number, W: number, inn = true, out = true): React.CSSProperties => {
  const k = 5;
  const o = out ? span(frame, dur - k, dur, 'exit') : 0;
  const i = inn ? 1 - span(frame, 0, k + 2, 'snappy') : 0;
  const dx = (-o * dirOut + i * dirIn) * W * 0.06;
  const blur = (o + i) * 14;
  return {transform: `translateX(${dx}px) scale(${1 + (o + i) * 0.03}) ${U}`, filter: blur > 0.3 ? `blur(${blur}px)` : undefined};
};

/** A light FLASH, kept as an option for a film whose look wants it (`cut: 'flash'`); not the default. */
export const FlashCut: React.FC<{dur?: number; strength?: number}> = ({dur = 10, strength = 0.6}) => {
  const frame = useCurrentFrame();
  const o = frame < dur * 0.45 ? span(frame, 0, dur * 0.45, 'out') : 1 - span(frame, dur * 0.45, dur, 'smooth');
  return <AbsoluteFill style={{pointerEvents: 'none', opacity: o * strength,
    background: 'radial-gradient(ellipse at 50% 45%, rgba(255,255,255,1), rgba(255,255,255,0.5) 55%, rgba(255,255,255,0) 82%)'}} />;
};

/** CAPTION: what is happening, in a lower-left tag (an accent bar and the line); never over a card. */
export const CaptionStrip: React.FC<{text: string; dur: number}> = ({text, dur}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const o = span(frame, 0, 10, 'snappy');
  const out = span(frame, dur - 8, dur, 'exit');
  const dark = isDarkHex(look.ground);
  return (
    <div style={{position: 'absolute', left: 64 * s, bottom: (H > W ? 220 : 60) * s, display: 'flex', alignItems: 'center', gap: 14 * s,
      opacity: 1 - out, transform: `translateX(${(1 - o) * -24 * s}px) ${U}`, clipPath: `inset(-20px ${(1 - o) * 100}% -20px -20px)`}}>
      <div style={{width: 4 * s, height: 34 * s, borderRadius: 2 * s, background: look.accent}} />
      <div style={{fontFamily: SANS, fontSize: 28 * s, fontWeight: 620, letterSpacing: isCJK(text) ? '0.04em' : '-0.005em', color: dark ? '#f4f3ef' : look.ink,
        padding: `${8 * s}px ${16 * s}px`, borderRadius: 10 * s, background: dark ? 'rgba(20,20,22,0.72)' : 'rgba(255,255,255,0.9)',
        boxShadow: '0 10px 30px rgba(10,10,10,0.16)'}}>{text}</div>
    </div>
  );
};

/** The ink that reads best on `bg`, from the film's own candidates (white on a yellow pill was 1.3:1). */
export const inkOn = (bg: string, inks: string[]) => inks.reduce((best, c) => (contrast(c, bg) > contrast(best, bg) ? c : best), inks[0]);

/** The brand lockup from one SVG: the icon square at its left (width ≈ the SVG's height) and the wordmark after it,
 *  drawn as two clipped copies of the file so each part moves alone. `grow` 0→1 grows the icon out of an accent dot. */
export const Lockup: React.FC<{mark: string; aspect: number; h: number; grow: number; word: number; plate?: boolean}> = ({mark, aspect, h, grow, word, plate: plateProp}) => {
  const look = useLook();
  const w = h * aspect, iconW = h * 1.08;
  const dot = 1 - span(grow, 0.35, 0.75, 'linear');
  // a brand mark is drawn for a light page; on a dark paper it sits on a light plate rather than vanishing into it —
  // unless the mark is itself light (made for dark grounds: promo_film reads its pixels and says `plate: false`)
  const plate = plateProp ?? isDarkHex(look.paper);
  return (
    <div style={{position: 'relative', width: w, height: h, ...(plate ? {padding: `${h * 0.28}px ${h * 0.4}px`, margin: `${-h * 0.28}px ${-h * 0.4}px`,
      boxSizing: 'content-box', borderRadius: h * 0.3, background: `rgba(250,250,248,${Math.min(1, word * 1.2 + grow * 0.3)})`,
      boxShadow: `0 ${h * 0.2}px ${h * 0.8}px rgba(0,0,0,0.45)`} : {})}}>
      <div style={{position: 'absolute', left: plate ? h * 0.4 : 0, top: plate ? h * 0.28 : 0, width: w, height: h}}>
      <div style={{position: 'absolute', left: h / 2 - h * 0.09, top: h / 2 - h * 0.09, width: h * 0.18, height: h * 0.18, borderRadius: '50%',
        background: look.accent, transform: `scale(${Math.min(1, grow * 4) * (1 + 2.4 * span(grow, 0.25, 0.6, 'linear'))})`, opacity: dot,
        boxShadow: `0 0 ${h * 0.3}px ${alpha(look.accent, 0.7)}`}} />
      <div style={{position: 'absolute', left: 0, top: 0, width: iconW, height: h, overflow: 'hidden',
        clipPath: `circle(${span(grow, 0.3, 0.85, 'snappy') * 75}% at ${h / 2}px ${h / 2}px)`}}>
        <Img src={urlOf(mark)} style={{position: 'absolute', left: 0, top: 0, width: w, height: h}} />
      </div>
      <div style={{position: 'absolute', left: iconW, top: 0, width: w - iconW, height: h, overflow: 'hidden', clipPath: `inset(0 ${(1 - word) * 100}% 0 0)`}}>
        <Img src={urlOf(mark)} style={{position: 'absolute', left: -iconW, top: 0, width: w, height: h, transform: `translateX(${(1 - word) * -h * 0.3}px)`}} />
      </div>
      </div>
    </div>
  );
};

/** BRAND OPEN: an accent dot lands, grows into the icon, the wordmark draws out of it, the kicker rises under it;
 *  the lockup RESTS a full second, then the card rises out as the first shot carries in. */
export const BrandOpen: React.FC<{mark: string; aspect: number; kicker?: string; dur: number; markH?: number; plate?: boolean}> = ({mark, aspect, kicker = '', dur, markH = 170, plate}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const grow = span(frame, 2, 26, 'linear');
  const word = span(frame, 18, 36, 'snappy');
  const out = span(frame, dur - 10, dur, 'exit');
  const mh = Math.min(markH * s, (W * 0.78) / aspect);
  return (
    <CardGround>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `translateY(${-out * 60 * s}px) ${U}`, opacity: 1 - out}}>
        <Lockup mark={mark} aspect={aspect} h={mh} grow={grow} word={word} plate={plate} />
        {kicker ? <div style={{marginTop: 44 * s}}>
          <RiseLine text={kicker} px={26 * s} start={30} gap={1.5} family={MONO} weight={600} color={look.muted} />
        </div> : null}
      </AbsoluteFill>
    </CardGround>
  );
};

/** RECALL OUTRO: the film's own shots come back as a wall of live frames that pulls back; at `stampAt` the wall
 *  steps behind a scrim and the lockup grows out of its dot, the tagline rising under it; the end holds a second. */
export const RecallOutro: React.FC<{tiles: React.ReactNode[]; mark: string; aspect: number; tagline?: string; dur: number; stampAt?: number; markH?: number;
  cta?: string; plate?: boolean}> = ({tiles, mark, aspect, tagline = '', dur, stampAt = 46, markH = 150, cta, plate}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H} = useVideoConfig();
  const look = useLook();
  const s = typeScale(W, H);
  const n = tiles.length;
  const cols = H > W ? 2 : n <= 4 ? 2 : 3;
  const rows = Math.max(1, Math.ceil(n / cols));
  const gapPx = 26 * s;
  const tw = (W * 0.92 - gapPx * (cols - 1)) / cols, th = tw * (H / W);
  const gridW = cols * tw + (cols - 1) * gapPx, gridH = rows * th + (rows - 1) * gapPx;
  const pull = 1.16 - 0.16 * span(frame, 0, stampAt + 10, 'smooth') - 0.04 * span(frame, stampAt + 10, dur, 'linear');
  const back = span(frame, stampAt - 4, stampAt + 12, 'smooth');
  const grow = span(frame, stampAt, stampAt + 22, 'linear');
  const word = span(frame, stampAt + 14, stampAt + 30, 'snappy');
  const dark = isDarkHex(look.paper);
  const mh = Math.min(markH * s, (W * 0.7) / aspect);
  return (
    <CardGround>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{position: 'relative', width: gridW, height: gridH, transform: `scale(${pull}) ${U}`, filter: back > 0.01 ? `blur(${back * 1.5}px)` : undefined}}>
          {tiles.map((t, i) => {
            const c = i % cols, r = Math.floor(i / cols);
            const at = 1 + i * 2.5;
            const k = span(frame, at, at + 14, 'snappy');
            return (
              <div key={i} style={{position: 'absolute', left: c * (tw + gapPx), top: r * (th + gapPx), width: tw, height: th, borderRadius: 14 * s,
                overflow: 'hidden', opacity: k, transform: `translateY(${(1 - k) * 40 * s}px) scale(${0.94 + 0.06 * k})`,
                boxShadow: `0 ${18 * s}px ${50 * s}px rgba(10,10,10,${dark ? 0.5 : 0.18})`}}>
                <div style={{width: W, height: H, transform: `scale(${tw / W})`, transformOrigin: '0 0', position: 'relative'}}>{t}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{background: `radial-gradient(42% 38% at 50% 50%, ${alpha(look.paper, 0.92 * back)}, ${alpha(look.paper, 0.78 * back)} 55%, ${alpha(look.paper, 0.32 * back)} 100%)`}} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <Lockup mark={mark} aspect={aspect} h={mh} grow={grow} word={word} plate={plate} />
        {tagline ? <div style={{marginTop: 34 * s}}>
          <RiseLine text={tagline} px={46 * s} start={stampAt + 26} gap={2} weight={560} color={look.ink} />
        </div> : null}
        {/* the CTA: a real address or command, set as a button and HELD (it is what the viewer acts on) */}
        {cta ? (() => {
          const c = span(frame, stampAt + 40, stampAt + 52, 'snappy');
          return <div style={{marginTop: 36 * s, opacity: c, transform: `translateY(${(1 - c) * 14 * s}px) ${U}`, padding: `${12 * s}px ${28 * s}px`,
            borderRadius: 999, background: look.accentInk, color: inkOn(look.accentInk, [look.paper, look.ink, '#ffffff', '#141413']), fontFamily: SANS, fontSize: 28 * s, fontWeight: 650,
            letterSpacing: '0.01em', boxShadow: `0 ${10 * s}px ${30 * s}px ${alpha(look.accentInk, 0.35)}`}}>{cta}</div>;
        })() : null}
      </AbsoluteFill>
    </CardGround>
  );
};
