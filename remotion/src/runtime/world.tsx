// WORLD — the PLACE a beat happens in, drawn behind it, named from the beat's own subject (slide.world, places.json).
//
// WHY. A paper-cut reference film sets every scene inside an illustrated world; our styled film put small drawings on
// a flat ground. A first spike drew ONE landscape behind every beat, and the user rejected it twice: "卫星的背景怎么可能
// 是山水，请根据实际来弄", then "你不要所有都换成太空场景，你要适配内容". So a place is a FACT about a beat — where the
// thing it shows actually is — named by the shot-director like its form, and a beat about an idea names none.
//
// WHAT IS DRAWN IS WHAT IS THERE. From a GPS orbit (~20,200 km) the Earth is a whole disc about 28 degrees across, not a
// horizon, and no continents are drawn — a hand-waved coastline is an invented geography; ocean, cloud bands and the
// thin atmosphere are true of any view. A place keeps its own colours (space is dark, grass is green); the film's ink
// draws its outlines so the place and the things in it are one drawing.
//
// THE CAPTION'S BAND STAYS CALM. Detail (windows, planks) is drawn above the caption's real top only: measured on the
// first sky, a caption set over a grid of lit windows read as noise.
//
// A PLACE IS FOR A BEAT WITH A PHYSICAL SUBJECT. A register that draws outline-only shapes (HandDrawn's boxes) reads
// see-through inside one — measured: a cloud drifted through a flow box. Such a beat is about an idea and names none.
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import placesTable from './places.json';
import {useStyle} from './styleSpec';
import {mix, useDNA} from './dna';
import {captionBand} from './layout';
import type {SafeProfile} from './safeZone';

const TABLE = placesTable as unknown as Record<string, {ground: string; for: string}>;
export const PLACES: string[] = Object.keys(TABLE).filter((k) => !k.startsWith('_'));
/** The ground a place stands on — the beat's declared ground when it names the place (render_remotion). */
export const placeGround = (place: string): string | null => (PLACES.includes(place) ? TABLE[place].ground : null);

const hash = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

type P = {W: number; H: number; t: number; line: string; lw: number; band: number};

const Orbit: React.FC<P> = ({W, H, t, lw}) => {
  const S = Math.min(W, H);
  const stars = Array.from({length: 90}, (_, i) => ({
    x: hash(i * 3 + 1) * W, y: hash(i * 3 + 2) * H * 0.72, r: S * (0.0012 + 0.0028 * hash(i * 3 + 3)),
    a: 0.45 + 0.45 * Math.abs(Math.sin(t * (0.6 + hash(i) * 1.2) + i)),
  }));
  const R = S * 0.62, cx = W * 0.5, cy = H * 0.62 + R;
  const spin = (t * 0.6) % 360;
  return (
    <>
      <rect width={W} height={H} fill={TABLE.orbit.ground} />
      {stars.map((s, i) => <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#ffffff" opacity={s.a} />)}
      <defs>
        <radialGradient id="w-atmo" cx="50%" cy="50%" r="50%">
          <stop offset="0.93" stopColor="#6fb6ff" stopOpacity="0" />
          <stop offset="0.965" stopColor="#6fb6ff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#6fb6ff" stopOpacity="0" />
        </radialGradient>
        <clipPath id="w-earth"><circle cx={cx} cy={cy} r={R} /></clipPath>
      </defs>
      <circle cx={cx} cy={cy} r={R * 1.07} fill="url(#w-atmo)" />
      <circle cx={cx} cy={cy} r={R} fill="#2f6fb8" stroke="#0a0f1f" strokeWidth={lw} />
      <g clipPath="url(#w-earth)" transform={`rotate(${spin.toFixed(3)} ${cx} ${cy})`}>
        {Array.from({length: 26}, (_, i) => {
          const a = hash(i * 5 + 1) * Math.PI * 2, d = R * Math.sqrt(hash(i * 5 + 2)) * 0.95;
          const x = cx + Math.cos(a) * d, y = cy + Math.sin(a) * d;
          return <ellipse key={i} cx={x} cy={y} rx={R * (0.06 + 0.08 * hash(i * 5 + 3))}
            ry={R * (0.012 + 0.012 * hash(i * 5 + 4))} fill="#ffffff" opacity={0.35 + 0.25 * hash(i)}
            transform={`rotate(${(-12 + 24 * hash(i * 5 + 5)).toFixed(1)} ${x} ${y})`} />;
        })}
      </g>
      <g clipPath="url(#w-earth)"><circle cx={cx + R * 0.55} cy={cy} r={R} fill="#000814" opacity={0.35} /></g>
    </>
  );
};

const Clouds: React.FC<P & {at: [number, number, number, number][]}> = ({W, t, line, lw, at, H}) => {
  const S = Math.min(W, H);
  const puff = [[-1.0, 0.15, 0.55], [-0.35, -0.2, 0.75], [0.4, -0.05, 0.65], [1.0, 0.2, 0.45]];
  return (
    <>
      {at.map(([x0, y, s, v], i) => {
        const cx = ((x0 * W + t * S * v) % (W * 1.3)) - W * 0.15, sz = s * S;
        return (
          <g key={i}>
            {puff.map(([dx, dy, r], j) => <circle key={'o' + j} cx={cx + dx * sz} cy={y * H + dy * sz} r={r * sz + lw * 0.8} fill={line} />)}
            {puff.map(([dx, dy, r], j) => <circle key={'f' + j} cx={cx + dx * sz} cy={y * H + dy * sz} r={r * sz} fill="#ffffff" />)}
          </g>
        );
      })}
    </>
  );
};

const Sky: React.FC<P> = (p) => {
  const {W, H, line, lw, band} = p;
  const S = Math.min(W, H);
  const calm = H - band;                                   // no window below this: the caption's band
  const blocks: {x: number; w: number; top: number; tone: number}[] = [];
  let x = 0, k = 0;
  while (x < W) {
    const w = S * (0.14 + 0.14 * hash(k * 7 + 1)), h = H * (0.08 + 0.12 * hash(k * 7 + 2));
    blocks.push({x, w, top: Math.min(calm - S * (0.1 + 0.22 * hash(k * 7 + 5)), H * 0.86 - h), tone: hash(k * 7 + 3)});
    x += w * (0.92 + 0.06 * hash(k * 7 + 4)); k++;
  }
  return (
    <>
      <defs>
        <linearGradient id="w-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8fc3ec" /><stop offset="0.8" stopColor={TABLE.sky.ground} />
        </linearGradient>
      </defs>
      <rect width={W} height={H} fill="url(#w-sky)" />
      <Clouds {...p} at={[[0.22, 0.2, 0.07, 0.006], [0.7, 0.32, 0.05, 0.004], [0.4, 0.46, 0.04, 0.003]]} />
      {blocks.map((b, i) => {
        const cols = Math.max(2, Math.round(b.w / (S * 0.05))), gap = b.w / (cols + 1);
        const rows = Math.max(0, Math.floor((calm - b.top - S * 0.03) / (S * 0.06)));
        return (
          <g key={i}>
            <rect x={b.x} y={b.top} width={b.w} height={H - b.top} fill={b.tone > 0.5 ? '#a9bccb' : '#93a9bb'}
              stroke={line} strokeWidth={lw} />
            {Array.from({length: cols * rows}, (_, j) => (
              <rect key={j} x={b.x + gap * (1 + (j % cols)) - S * 0.011} y={b.top + S * 0.03 + Math.floor(j / cols) * S * 0.06}
                width={S * 0.022} height={S * 0.03} rx={S * 0.003} fill={hash(i * 31 + j) > 0.75 ? '#f6e7b8' : '#d7e3ec'} />
            ))}
          </g>
        );
      })}
    </>
  );
};

const hill = (W: number, H: number, base: number, amp: number, seed: number) => {
  const pts: string[] = [];
  for (let i = 0; i <= 40; i++) {
    const u = i / 40;
    const y = base - amp * (0.6 * Math.sin(u * Math.PI * (1.1 + hash(seed) * 0.7) + hash(seed + 1) * 6)
      + 0.4 * Math.sin(u * Math.PI * (2.4 + hash(seed + 2)) + hash(seed + 3) * 6));
    pts.push(`${(u * W).toFixed(1)},${y.toFixed(1)}`);
  }
  return `M0,${H} L${pts.join(' L')} L${W},${H} Z`;
};

const Field: React.FC<P> = (p) => {
  const {W, H, line, lw} = p;
  const S = Math.min(W, H);
  return (
    <>
      <defs>
        <linearGradient id="w-fsky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#a9d4f2" /><stop offset="0.7" stopColor={TABLE.field.ground} />
        </linearGradient>
      </defs>
      <rect width={W} height={H} fill="url(#w-fsky)" />
      <circle cx={W * 0.8} cy={H * 0.13} r={S * 0.07} fill="#f7d26a" stroke={line} strokeWidth={lw} />
      <Clouds {...p} at={[[0.2, 0.18, 0.06, 0.005], [0.6, 0.26, 0.045, 0.003]]} />
      {[[0.66, 0.05, '#b9dc95', 3], [0.75, 0.04, '#9cc97a', 7], [0.85, 0.03, '#86b866', 13]].map(([b, a, c, s], i) => (
        <path key={i} d={hill(W, H, H * (b as number), H * (a as number), s as number)} fill={c as string}
          stroke={line} strokeWidth={lw} strokeLinejoin="round" />
      ))}
    </>
  );
};

const Room: React.FC<P> = ({W, H, line, lw, band}) => {
  const S = Math.min(W, H);
  const floorY = Math.min(H * 0.78, H - band - S * 0.02);
  const planks = Math.max(4, Math.round(W / (S * 0.18)));
  const win = {x: W * 0.62, y: H * 0.1, w: W * 0.28, h: H * 0.22};
  return (
    <>
      <rect width={W} height={H} fill={TABLE.room.ground} />
      <rect x={win.x} y={win.y} width={win.w} height={win.h} fill="#bfe0f5" stroke={line} strokeWidth={lw * 1.4} />
      <line x1={win.x + win.w / 2} y1={win.y} x2={win.x + win.w / 2} y2={win.y + win.h} stroke={line} strokeWidth={lw} />
      <line x1={win.x} y1={win.y + win.h / 2} x2={win.x + win.w} y2={win.y + win.h / 2} stroke={line} strokeWidth={lw} />
      <rect x={0} y={floorY} width={W} height={H - floorY} fill="#c9a77c" stroke={line} strokeWidth={lw} />
      <rect x={0} y={floorY - S * 0.018} width={W} height={S * 0.018} fill="#e2d4bf" stroke={line} strokeWidth={lw * 0.8} />
      {Array.from({length: planks}, (_, i) => (
        <line key={i} x1={(i + 0.5) * (W / planks)} y1={floorY} x2={(i + 0.5) * (W / planks) + (i - planks / 2) * S * 0.04}
          y2={Math.min(H, H - band)} stroke={mix('#c9a77c', line, 0.35)} strokeWidth={lw * 0.7} />
      ))}
    </>
  );
};

const DRAW: Record<string, React.FC<P>> = {orbit: Orbit, sky: Sky, field: Field, room: Room};

/** Behind a beat's register: its place, or the film's own ground when it names none (the register's same-tone ground
 *  is made transparent by the style pass when `surface.world` is 'place', so something must be under it). */
export const WorldBackdrop: React.FC<{place?: string | null; safe?: SafeProfile | null}> = ({place, safe}) => {
  const style = useStyle();
  const dna = useDNA();
  const f = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  if ((style?.surface as {world?: string} | undefined)?.world !== 'place' || !dna) return null;
  if (place && !DRAW[place]) throw new Error(`beat names place "${place}", which runtime/places.json does not hold ` +
    `(${PLACES.join(', ')})`);
  const S = Math.min(W, H);
  const lw = Math.max(2, S * 0.004);
  const line = mix(String(dna.bg), String(dna.fg), 0.6);
  const Draw = place ? DRAW[place] : null;
  // WHERE THE CAPTION ACTUALLY IS. On a platform-safe 9:16 film the caption is lifted with the register's frame
  // (runtime/safeZone), above the platform's UI — measured on the first sky, the plain band left the lifted caption
  // sitting on lit windows. The calm band starts at the caption's real top.
  const capTop = safe ? safe.y0 * H + safe.k * H - safe.k * captionBand(W, H) : H - captionBand(W, H);
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} data-world={place ?? 'none'}
      style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      {Draw ? <Draw W={W} H={H} t={f / fps} line={line} lw={lw} band={H - capTop} />
        : <rect width={W} height={H} fill={String(dna.bg)} />}
    </svg>
  );
};
