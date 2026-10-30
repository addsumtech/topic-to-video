// THE MEDIA-RESOLUTION CENSUS — per frame, every raster on screen and how far it is magnified past its own pixels.
//
// A product film shipped with its hero UI soft: the product's 1000 px demo frames sat in a 3D slab drawn ~1.5x
// larger, and a camera push magnified them again. Every type gate was green, because none of them looks at an
// IMAGE's pixels: they measure text in the DOM. The browser knows the answer exactly — an <img>'s natural size
// and the box it is drawn in — so this asks it, on the frames the film really renders (seams, cameras and pushes
// included), and scripts/media_res_qa.py judges the census across frames.
//
// Mounted only by the Film when `mediaRes` is set (Film.tsx), never imported by a register, so no register's source
// hash moves because it exists.
import React from 'react';
import {continueRender, delayRender, useCurrentFrame} from 'remotion';

export const MEDIA_RES_TAG = 'MEDIA-RES ';

// below this on-screen size an image is an icon-sized mark, not a picture to read
const MIN_DRAWN_PX = 48;

const blurOf = (el: Element | null): number => {
  // the largest CSS blur on the element or any ancestor: a picture drawn blurred on purpose cannot look soft
  let worst = 0;
  for (let e: Element | null = el; e; e = e.parentElement) {
    const f = getComputedStyle(e).filter;
    if (f && f !== 'none') {
      const m = /blur\(([\d.]+)px\)/.exec(f);
      if (m) worst = Math.max(worst, parseFloat(m[1]));
    }
  }
  return worst;
};

const opacityOf = (el: Element | null): number => {
  let o = 1;
  for (let e: Element | null = el; e; e = e.parentElement) {
    const v = parseFloat(getComputedStyle(e).opacity);
    if (Number.isFinite(v)) o *= v;
  }
  return o;
};

const shortSrc = (s: string): string => {
  const clean = s.split('?')[0];
  const parts = clean.split('/');
  return parts.slice(-2).join('/').slice(-80);
};

type Row = [string, string, number, number, number, number, string, number, number, number];

/** [kind, src, natural w, natural h, drawn w, drawn h, object-fit, magnification, opacity, blur px] for every raster
 *  drawn at least MIN_DRAWN_PX and at least partly inside the frame. Magnification follows object-fit: `cover`
 *  and `fill` show the larger axis' stretch, `contain`/`scale-down` the smaller one. The box is the client rect, so
 *  a rotated or tilted picture reads somewhat larger than it is (its bounding box): it can only over-report. */
export const censusMedia = (root: HTMLElement, frame: DOMRect): {n: number; m: Row[]} => {
  const dpr = window.devicePixelRatio || 1;
  const rows: Row[] = [];
  let n = 0;
  const consider = (el: Element, kind: string, src: string, nw: number, nh: number) => {
    if (!nw || !nh) return;
    const r = el.getBoundingClientRect();
    if (r.width < MIN_DRAWN_PX && r.height < MIN_DRAWN_PX) return;
    const ix = Math.min(r.right, frame.right) - Math.max(r.left, frame.left);
    const iy = Math.min(r.bottom, frame.bottom) - Math.max(r.top, frame.top);
    if (ix <= 0 || iy <= 0) return;
    n += 1;
    const fit = el instanceof HTMLImageElement || el instanceof HTMLVideoElement
      ? (getComputedStyle(el).objectFit || 'fill') : 'fill';
    const sx = (r.width * dpr) / nw, sy = (r.height * dpr) / nh;
    const s = fit === 'contain' || fit === 'scale-down' ? Math.min(sx, sy) : Math.max(sx, sy);
    rows.push([kind, shortSrc(src), nw, nh, Math.round(r.width), Math.round(r.height), fit,
      Math.round(s * 1000) / 1000, Math.round(opacityOf(el) * 100) / 100, blurOf(el)]);
  };
  root.querySelectorAll('img').forEach((img) => {
    const src = img.currentSrc || img.src || '';
    if (/\.svg(\?|$)/i.test(src) || src.startsWith('data:image/svg')) return;   // vector: no pixels to run out of
    consider(img, 'img', src, img.naturalWidth, img.naturalHeight);
  });
  root.querySelectorAll('video').forEach((v) => consider(v, 'video', v.currentSrc || v.src || '', v.videoWidth,
    v.videoHeight));
  root.querySelectorAll('canvas').forEach((c) => consider(c, 'canvas', c.getAttribute('data-media') || 'canvas',
    c.width, c.height));
  return {n, m: rows};
};

export const MediaResAudit: React.FC = () => {
  const frame = useCurrentFrame();
  const ref = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const handle = delayRender(`media-resolution census, frame ${frame}`, {timeoutInMilliseconds: 60000});
    let released = false;
    const release = () => {
      if (!released) {
        released = true;
        continueRender(handle);
      }
    };
    (async () => {
      const host = ref.current;
      if (host) {
        // an image still decoding reports a natural size of 0 and would be skipped as if it were not there
        await Promise.all(Array.from(host.ownerDocument.images).map((im) => im.decode().catch(() => null)));
        await new Promise((res) => requestAnimationFrame(() => res(null)));
      }
      if (!released && ref.current) {
        const rec = censusMedia(ref.current.ownerDocument.body, ref.current.getBoundingClientRect());
        // eslint-disable-next-line no-console
        console.log(MEDIA_RES_TAG + JSON.stringify({f: frame, ...rec}));
      }
      release();
    })();
    return release;
  }, [frame]);
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};
