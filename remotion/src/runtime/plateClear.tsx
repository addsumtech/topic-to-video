// THE PLATE-CLEAR CENSUS — per frame, every line of a shot's own type against every Blender plate object's box.
//
// A Blender plate's objects are pixels of a video, so no DOM gate sees them: the first plate (a GPS satellite,
// 2026-11-04) put its wing tip under the label 我在哪 with every gate green. runtime/blenderPlate.tsx marks each
// object's box on each frame (`data-plate-object`); this measures the type over it, on the frames the Film really
// renders, and scripts/plate_qa.py judges the census. The CAPTION (Film's `[data-caption]`) is judged too: it is
// nobody's own type, so it is checked against the plate on screen (its window is one beat's sole-visible window), and
// its hits carry a 1 so the judge names the object as the thing to move (GPS beat 2: the Earth's limb under it).
//
// Mounted only by the Film when `plateClear` is set (Film.tsx), never imported by a register.
import React from 'react';
import {continueRender, delayRender, useCurrentFrame} from 'remotion';

export const PLATE_CLEAR_TAG = 'PLATE-CLEAR ';
const MIN_OPACITY = 0.25;                       // fainter than this the type is arriving or leaving

const shown = (el: Element): boolean => {
  let op = 1;
  for (let e: Element | null = el; e; e = e.parentElement) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    op *= parseFloat(cs.opacity || '1');
  }
  return op >= MIN_OPACITY;
};

type Rect = {x0: number; y0: number; x1: number; y1: number};

const overlap = (a: Rect, b: Rect) =>
  Math.max(0, Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0)) * Math.max(0, Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0));

export const censusPlateClear = (root: HTMLElement) => {
  // each beat is its own [data-beat] wrapper: during a dissolve two beats are mounted, and the leaving beat's type over
  // the arriving beat's plate is a cross-fade, not a layout — a line is judged against the plates of its own beat only
  const beatOf = (el: Element) => el.closest('[data-beat]') ?? root;
  // a 9:16 film mounts each register twice: scaled in its frame, and full-frame in the margin echo (Film `SafeEcho`,
  // only its ground shows). The echo's plate is not a picture anyone sees: judged against it, the glass film's caption
  // 'sat 100% over' a glass drawn well above it
  const plates = Array.from(root.querySelectorAll('[data-plate]')).filter((el) => !el.closest('[data-echo]')).map((el) => {
    const r = el.getBoundingClientRect();
    const boxes: Rect[] = [];
    el.querySelectorAll('[data-plate-object]').forEach((o) => {
      const b = o.getBoundingClientRect();
      if (b.width >= 1 && b.height >= 1) boxes.push({x0: b.left, y0: b.top, x1: b.right, y1: b.bottom});
    });
    return {el, beat: beatOf(el), id: el.getAttribute('data-plate') || '?', f: Number(el.getAttribute('data-plate-frame')),
      pw: Number(el.getAttribute('data-plate-w')), ph: Number(el.getAttribute('data-plate-h')), r, boxes};
  });
  const hits: [string, string, number, number[], number][] = [];
  let texts = 0;
  const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = (n.textContent || '').trim();
    const el = n.parentElement;
    if (!t || !el || !shown(el)) continue;
    const range = root.ownerDocument.createRange();
    range.selectNodeContents(n);
    const r = range.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    texts += 1;
    const box = {x0: r.left, y0: r.top, x1: r.right, y1: r.bottom};
    const mine = beatOf(el);
    const cap = el.closest('[data-caption]') !== null;
    for (const p of plates) {
      if ((cap ? p.beat === root : p.beat !== mine) || !p.boxes.some((b) => overlap(box, b) > 0)) continue;
      const kx = p.pw / Math.max(1, p.r.width), ky = p.ph / Math.max(1, p.r.height);
      hits.push([t.slice(0, 40), p.id, p.f, [(box.x0 - p.r.left) * kx, (box.y0 - p.r.top) * ky,
        (box.x1 - p.r.left) * kx, (box.y1 - p.r.top) * ky].map((v) => Math.round(v * 10) / 10), cap ? 1 : 0]);
    }
  }
  return {hits, texts, objects: plates.reduce((m, p) => m + p.boxes.length, 0)};
};

export const PlateClearAudit: React.FC = () => {
  const frame = useCurrentFrame();
  const ref = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const handle = delayRender(`plate-clear census, frame ${frame}`, {timeoutInMilliseconds: 60000});
    let released = false;
    const release = () => {
      if (!released) {
        released = true;
        continueRender(handle);
      }
    };
    requestAnimationFrame(() => {
      if (!released && ref.current) {
        // eslint-disable-next-line no-console
        console.log(PLATE_CLEAR_TAG + JSON.stringify({f: frame, ...censusPlateClear(ref.current.ownerDocument.body)}));
      }
      release();
    });
    return release;
  }, [frame]);
  return <div ref={ref} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}} />;
};
