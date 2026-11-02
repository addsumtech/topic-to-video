// PARTICLES, drawn. `useTextMark` sets a word on an offscreen canvas in the film's own face and returns both its
// picture (so the settled word is shown as exactly the pixels the particles were taken from — no misregistration
// between the solid word and its dust) and its sampled points; `<Dust>` draws a set of particles as SVG circles.
// The numbers are runtime/particles.ts.
//
// The canvas waits for the face: a word sampled from a fallback font and drawn later in the real one would put its
// dust in the wrong shape, so the render is held (delayRender) until `document.fonts.load` has the face. The result is
// cached by its inputs (text, face, box, step) — a pure function of them, so the cache cannot change a frame.
import React from 'react';
import {continueRender, delayRender} from 'remotion';
import {sampleMask, type Pt} from './particles';

export type Mark = {src: string; w: number; h: number; px: number; pts: Pt[]};

const CACHE = new Map<string, Mark>();

const measure = (text: string, weight: number, family: string, maxW: number, maxH: number) => {
  const c = document.createElement('canvas').getContext('2d') as CanvasRenderingContext2D;
  let px = Math.floor(maxH * 0.82);
  for (; px > 12; px -= 2) {
    c.font = `${weight} ${px}px ${family}`;
    if (c.measureText(text).width <= maxW * 0.96) break;
  }
  return px;
};

/** The word, set in `family` to fit (maxW x maxH), as a picture and as points every `step` px. */
export const useTextMark = (text: string, family: string, maxW: number, maxH: number, o: {weight?: number;
  step?: number; ink?: string} = {}): Mark | null => {
  const weight = o.weight ?? 800, step = o.step ?? 5, ink = o.ink ?? '#ffffff';
  const W = Math.max(1, Math.round(maxW)), H = Math.max(1, Math.round(maxH));
  const key = JSON.stringify([text, family, W, H, weight, step, ink]);
  const [mark, setMark] = React.useState<Mark | null>(() => CACHE.get(key) ?? null);
  const [handle] = React.useState(() => (CACHE.has(key) || !text ? null
    : delayRender(`particles: setting "${text}"`, {timeoutInMilliseconds: 30000})));
  React.useEffect(() => {
    if (!handle) return;
    let live = true;
    (async () => {
      try {
        const probe = `${weight} ${Math.round(H * 0.5)}px ${family}`;
        await document.fonts.load(probe, text);
        await document.fonts.ready;
        const px = measure(text, weight, family, W, H);
        const cv = document.createElement('canvas');
        cv.width = W; cv.height = H;
        const g = cv.getContext('2d') as CanvasRenderingContext2D;
        g.font = `${weight} ${px}px ${family}`;
        g.fillStyle = ink;
        g.textAlign = 'center';
        g.textBaseline = 'middle';
        g.fillText(text, W / 2, H / 2);
        const data = g.getImageData(0, 0, W, H).data;
        const alpha = new Uint8ClampedArray(W * H);
        for (let i = 0; i < W * H; i++) alpha[i] = data[i * 4 + 3];
        const m: Mark = {src: cv.toDataURL('image/png'), w: W, h: H, px, pts: sampleMask(alpha, W, H, step)};
        CACHE.set(key, m);
        if (live) setMark(m);
      } finally {
        continueRender(handle);
      }
    })();
    return () => { live = false; };
  }, [handle, key]);   // eslint-disable-line react-hooks/exhaustive-deps
  return mark;
};

/** Particles as circles, in the coordinates of an absolutely placed box. */
export const Dust: React.FC<{pts: (Pt & {alpha?: number})[]; r: number; color: (i: number) => string; glow?: number;
  style?: React.CSSProperties}> = ({pts, r, color, glow = 0, style}) => {
  const id = 'dg' + React.useId().replace(/[^a-zA-Z0-9]/g, '');
  return (
    <svg style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', ...style}} width={1} height={1}>
      {glow > 0 ? (
        <filter id={id} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={glow} result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      ) : null}
      <g filter={glow > 0 ? `url(#${id})` : undefined}>
        {pts.map((p, i) => (p.alpha === 0 ? null
          : <circle key={i} cx={p.x} cy={p.y} r={r} fill={color(i)} opacity={p.alpha ?? 1} />))}
      </g>
    </svg>
  );
};
