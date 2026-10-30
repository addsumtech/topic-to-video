// SHOT · AuroraCurtain — an aurora as what it is: a folded curtain of light in the night sky, its rays standing along
// the field, its colour set by the height it glows at. Family X (weather / atmosphere).
// @dark-world: an aurora is only visible in a dark sky — under a light DNA the register still paints a night ground
// (the DNA's own dark end), because a curtain of light over a cream page is not a picture of anything.
//
// WHAT IT ARGUES. "The colour is the height" / "light in the upper atmosphere" / "a curtain the solar wind lights".
// The curtain is runtime/volume's line-of-sight integral (one folded sheet; the folds that turn edge-on to the lens
// brighten themselves, the lower border is sharp where the emission stops, the tops fade) — not rects of light, which
// is what bench-aurora shipped as "a barcode on a flat wall". Hide the caption and the frame still says aurora; give
// it the film's `bands` and it says the colour key too: a ruler beside the curtain on the SAME projection the shader
// uses (volumeCore.curtainFit), so a band's label sits at the height its colour glows at.
//
// THE COLOURS are the film's `bands` (label, note, from/to km, colour) or, with none, the declared emission physics
// (volumeCore.AURORA_BANDS, sourced there) — and then NO numbers are drawn: a ruler with figures the film never gave
// would be a claim (E14). `ticks` are the film's altitudes to mark.
//
// ITS OWN SOUND (runtime/sound.ts): `surgeAt` — a substorm brightening at that point of the beat (NOAA: "the arcs may
// expand ... becoming very bright") — makes a `swell`, on the frame the light crests. No surgeAt, no surge, no sound.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, hash01} from '../runtime/motion';
import {useDNA, readableOn, mix} from '../runtime/dna';
import {darkGround} from '../runtime/light';
import {CONTENT_TOP, TITLE_Y, contentBottom, fitBlockPx, wrapLines} from '../runtime/layout';
import {Volume, curtainFit, checkBands, AURORA_BANDS, AURORA_LOWER_KM, AURORA_TOP_KM, type Band,
  type Rect} from '../runtime/volume';
import {soundT, type SoundDecl} from '../runtime/sound';
import {rows} from '../runtime/rows';

export const DURATION = 180; // 6s — long enough for the rays to be seen travelling along the arc
export const SOUNDS: readonly SoundDecl[] = [
  {kind: 'swell', at: 'surgeAt'},
] as const;

const DISPLAY = 'var(--f-display, "Source Serif 4", "Noto Serif SC", Georgia, serif)';
const BODY = 'var(--f-body, Inter, "Noto Sans SC", system-ui, sans-serif)';
const MONO = 'var(--f-mono, "JetBrains Mono", "Noto Sans SC", ui-monospace, monospace)';

type FilmBand = Band & {label?: string; note?: string};

export const AuroraCurtain: React.FC<{
  title?: string;
  kicker?: string;
  /** the film's colour key: altitude spans (km) and the colour each glows; labels/notes are drawn on the ruler */
  bands?: FilmBand[];
  /** altitudes (km) to mark on the ruler — the film's numbers; none given, none drawn */
  ticks?: number[];
  /** the ruler's unit label (the film's word for km) */
  unit?: string;
  /** a point of the beat (0..1) at which a substorm brightening crests — and its swell sounds */
  surgeAt?: number;
  /** how many parallel sheets (1-3) */
  sheets?: number;
  seed?: number;
}> = ({title = 'Light in the upper atmosphere', kicker = '', bands: bandsRaw, ticks: ticksRaw, unit = 'km', surgeAt, sheets = 2,
       seed = 7} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H), portrait = W < H;
  const ground = darkGround(dna?.bg, '#03060c');
  const ink = readableOn(ground, dna?.fg ?? '#eef3f8', '#eef3f8', '#0b0d12');
  const dim = mix(ink, ground, 0.38);
  // a list prop is checked BEFORE any array method touches it (runtime/rows): a film that sends one band as an
  // object gets a sentence naming the prop, not `bandsIn.some is not a function`
  const bandsIn = bandsRaw == null ? undefined : rows<FilmBand>(bandsRaw, 'bands', 'AuroraCurtain');
  const ticks = ticksRaw == null ? undefined : rows<number>(ticksRaw, 'ticks', 'AuroraCurtain');
  const bands: FilmBand[] = bandsIn ? (checkBands(bandsIn, 'AuroraCurtain') as FilmBand[]) : AURORA_BANDS;
  const ruled = !!bandsIn && (bandsIn.some((b) => b.label) || (ticks?.length ?? 0) > 0);
  if (ticks && !ticks.every((k) => Number.isFinite(k))) throw new Error('AuroraCurtain: ticks are altitudes in km');

  // ── the title (one or two lines, fitted in the face that draws it) ──
  const x0 = Math.round(W * (portrait ? 0.08 : 0.065));
  const colW = Math.round(W * (portrait ? 0.84 : 0.5));
  const titlePx = title ? fitBlockPx(title, colW, U * 0.2, Math.round(U * (portrait ? 0.075 : 0.064)),
    {usable: 0.95, leading: 1.1, min: Math.round(U * 0.036)}) : 0;
  const titleLines = title ? wrapLines(title, titlePx, colW * 0.95) : 0;
  const kickPx = Math.round(U * 0.026);
  const titleTop = TITLE_Y + (kicker ? kickPx * 1.6 : 0);
  const titleRect: Rect = {x: x0 - U * 0.01, y: TITLE_Y - U * 0.01, w: Math.min(colW, W - 2 * x0) + U * 0.02,
    h: titleTop - TITLE_Y + titleLines * titlePx * 1.12 + U * 0.02};

  // ── where the curtain hangs: its lower border above the caption band, its top under the title when ruled ──
  const lowKm = bands[0].from < AURORA_LOWER_KM && bands[0].to > AURORA_LOWER_KM ? AURORA_LOWER_KM
    : bandsIn ? bands[0].from : AURORA_LOWER_KM;
  const topKm = bandsIn ? bands[bands.length - 1].to : AURORA_TOP_KM;
  const yLow = Math.round(contentBottom(W, H) - U * 0.11);
  const yTop = Math.round(ruled ? Math.max(CONTENT_TOP, titleRect.y + titleRect.h + U * 0.04) : H * (portrait ? 0.16 : 0.08));
  const fit = curtainFit(yTop, yLow, lowKm, topKm);
  const horizon = yLow + U * 0.05;

  // ── the surge: a brightening that crests at surgeAt and ebbs ──
  const sT = soundT(SOUNDS, 'swell', {surgeAt});
  const surge = sT === null ? 0 : clamp01(1 - Math.abs(t - sT) / (t < sT ? 0.05 : 0.22)) ** 1.5;
  const lit = easeOutCubic(clamp01(seg(t, 0.0, 0.28)));

  // ── the ruler (only with the film's own bands / ticks) ──
  const rx = x0 + U * 0.01;
  const labelPx = Math.round(U * 0.03), notePx = Math.round(U * 0.022);
  const rulerIn = easeOutCubic(clamp01(seg(t, 0.12, 0.34)));
  const labelled = ruled ? bands.filter((b) => b.label) : [];
  const keep: Rect[] = title ? [titleRect] : [];
  // THE LABELS STACK, THEY DO NOT OVERLAP. Each sits at its band's middle altitude unless the one above it reaches
  // down that far; a film's note may be a sentence, so it WRAPS in its column and the block is measured by the same
  // wrap the browser does (E1/E5: an English two-word note is the fixture's limit, not the register's). A stack taller
  // than the ruler is refused, not overlapped.
  const colLW = Math.round(U * (portrait ? 0.34 : 0.36));
  const gapL = U * 0.014;
  const stackTop = TITLE_Y + (title ? titleRect.h : 0) + U * 0.01, stackBot = contentBottom(W, H) - U * 0.01;
  // two passes: each label as near its band as the one above allows (down), then the stack lifted off the caption
  // band from the bottom (up) — order kept, each label as close to its band as the room allows
  const boxes = labelled
    .map((b) => ({b, y: fit.yOf((b.from + Math.min(b.to, topKm)) / 2)}))
    .sort((a, c) => a.y - c.y)
    .map(({b, y}) => ({b, y, h: wrapLines(String(b.label), labelPx, colLW) * labelPx * 1.25 +
      (b.note ? wrapLines(b.note, notePx, colLW) * notePx * 1.4 : 0), top: 0}));
  let floorY = -Infinity;
  for (const x of boxes) { x.top = Math.max(x.y - labelPx * 0.7, floorY + gapL); floorY = x.top + x.h; }
  let ceilY = stackBot;
  for (let k = boxes.length - 1; k >= 0; k--) { boxes[k].top = Math.min(boxes[k].top, ceilY - boxes[k].h); ceilY = boxes[k].top - gapL; }
  if (boxes.length && boxes[0].top < stackTop) {
    throw new Error(`AuroraCurtain: the band labels and notes need ${Math.round(stackTop - boxes[0].top)}px more than ` +
      'the ruler has between the title and the caption band — shorten the notes or label fewer bands');
  }
  const labelBoxes = boxes.map((x) => ({b: x.b, y: x.y, rect: {x: rx + U * 0.035, y: x.top, w: colLW, h: x.h}}));
  floorY = boxes.length ? boxes[boxes.length - 1].top + boxes[boxes.length - 1].h : -Infinity;
  if (ruled) {
    const yA = Math.min(yTop, ...labelBoxes.map((l) => l.rect.y)) - U * 0.02;
    const yB = Math.max(yLow, floorY) + U * 0.02;
    keep.push({x: rx - U * 0.03, y: yA, w: colLW + U * 0.08, h: yB - yA});
  }

  // ── stars and the land, the night's own texture ──
  const stars = React.useMemo(() => Array.from({length: 170}, (_, i) => ({
    x: hash01(seed * 31 + i) * W, y: hash01(seed * 17 + i * 3) * horizon,
    r: U * 0.0011 * (0.6 + 1.8 * hash01(seed * 7 + i) ** 4), a: 0.25 + 0.6 * hash01(seed * 13 + i)})), [W, horizon, U, seed]);
  const ridge = React.useMemo(() => {
    const pts: string[] = [];
    for (let i = 0; i <= 160; i++) {
      const u = i / 160, x = u * W;
      const y = horizon + U * (0.016 * Math.sin(u * 7.1 + seed) + 0.009 * Math.sin(u * 19.3 + seed * 2) +
        0.004 * Math.sin(u * 47.0 + seed * 3));
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return `M0,${H} L${pts.join(' L')} L${W},${H} Z`;
  }, [W, H, horizon, U, seed]);

  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${mix(ground, '#000000', 0.25)} 0%, ${ground} 55%, ${mix(ground, '#0b1a22', 0.5)} 100%)`}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}} aria-hidden>
        {/* @decor: the stars are the night's texture, seeded */}
        {stars.map((s, i) => <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#ffffff" fillOpacity={s.a} />)}
      </svg>
      <Volume spec={{form: 'curtain', bands, sheets, seed, intensity: Math.min(1.6, 1.3 + 0.3 * surge)}}
        curtain={{yTop, yLow}} fade={lit} surge={surge} keepOut={keep} res={0.75} where="AuroraCurtain" />
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}} aria-hidden>
        {/* the ground the curtain is seen from: it gives the sky its scale and the caption its dark */}
        <path d={ridge} fill={mix(ground, '#000000', 0.55)} />
      </svg>
      {ruled ? (
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: rulerIn}} aria-hidden>
          <line x1={rx} y1={fit.yOf(topKm)} x2={rx} y2={yLow} stroke={dim} strokeWidth={Math.max(1, U / 700)} />
          {bands.map((b, i) => (
            // the band ON the ruler, in its own colour, spanning its own altitudes
            <rect key={i} x={rx - U * 0.004} y={fit.yOf(Math.min(b.to, topKm))} width={U * 0.008}
              height={fit.yOf(b.from) - fit.yOf(Math.min(b.to, topKm))} rx={U * 0.004} fill={b.color} fillOpacity={0.9} />
          ))}
          {labelBoxes.filter(({y, rect}) => Math.abs(rect.y + labelPx * 0.7 - y) > labelPx * 0.6).map(({b, y, rect}) => (
            // a label the stack moved off its band is joined to it, so the colour key still reads
            <polyline key={`ld${b.label}`} fill="none" stroke={dim} strokeWidth={Math.max(1, U / 900)}
              points={`${rx + U * 0.008},${y} ${rx + U * 0.02},${y} ${rect.x - U * 0.008},${rect.y + labelPx * 0.62}`} />
          ))}
          {(ticks ?? []).filter((k) => k >= lowKm - 1e-9 && k <= topKm + 1e-9).map((k) => (
            <g key={k}>
              <line x1={rx - U * 0.016} y1={fit.yOf(k)} x2={rx - U * 0.006} y2={fit.yOf(k)} stroke={dim} strokeWidth={Math.max(1, U / 700)} />
            </g>
          ))}
        </svg>
      ) : null}
      {ruled ? (
        <div style={{position: 'absolute', inset: 0, opacity: rulerIn}}>
          {(ticks ?? []).filter((k) => k >= lowKm - 1e-9 && k <= topKm + 1e-9).map((k) => (
            <div key={k} style={{position: 'absolute', right: W - (rx - U * 0.022), top: fit.yOf(k) - notePx * 0.65,
              color: dim, font: `500 ${notePx}px/1.3 ${MONO}`, whiteSpace: 'nowrap'}}>{k}</div>
          ))}
          {ticks?.length ? (
            <div style={{position: 'absolute', left: rx - U * 0.01, top: fit.yOf(topKm) - notePx * 1.9, color: dim,
              font: `500 ${notePx}px/1.3 ${MONO}`, whiteSpace: 'nowrap'}}>{unit}</div>
          ) : null}
          {labelBoxes.map(({b, rect}) => (
            <div key={b.label} style={{position: 'absolute', left: rect.x, top: rect.y, width: rect.w}}>
              <div style={{color: ink, font: `700 ${labelPx}px/1.25 ${BODY}`}}>{b.label}</div>
              {b.note ? <div style={{color: dim, font: `500 ${notePx}px/1.4 ${BODY}`, textWrap: 'balance'} as React.CSSProperties}>{b.note}</div> : null}
            </div>
          ))}
        </div>
      ) : null}
      {kicker ? (
        <div style={{position: 'absolute', left: x0, top: TITLE_Y, color: dna?.accent ?? '#7cf2a4',
          font: `600 ${kickPx}px/1.2 ${MONO}`, letterSpacing: '0.16em', textTransform: 'uppercase',
          opacity: easeOutCubic(clamp01(seg(t, 0.04, 0.2)))}}>{kicker}</div>
      ) : null}
      {title ? (
        <div style={{position: 'absolute', left: x0, top: titleTop, width: colW, color: ink,
          font: `700 ${titlePx}px/1.1 ${DISPLAY}`, letterSpacing: '-0.01em', textWrap: 'balance',
          opacity: easeOutCubic(clamp01(seg(t, 0.06, 0.26))),
          transform: `translateY(${Math.round((1 - easeOutCubic(clamp01(seg(t, 0.06, 0.26)))) * U * 0.02)}px)`} as React.CSSProperties}>{title}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default AuroraCurtain;
