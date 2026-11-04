// THE PLATE-CLEAR CENSUS — per frame, every line of a shot's own type against every Blender plate object's box.
//
// A Blender plate's objects are pixels of a video, so no DOM gate sees them: the first plate (a GPS satellite,
// 2026-11-04) put its wing tip under the label 我在哪 with every gate green. runtime/blenderPlate.tsx marks each
// object's box on each frame (`data-plate-object`); this measures the type over it, on the frames the Film really
// renders, and scripts/plate_qa.py judges the census.
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
  const objects: [string, Rect][] = [];
  root.querySelectorAll('[data-plate-object]').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width >= 1 && r.height >= 1) objects.push([el.getAttribute('data-plate-object') || '?', {x0: r.left, y0: r.top, x1: r.right, y1: r.bottom}]);
  });
  const hits: [string, string, number, number][] = [];
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
    const area = r.width * r.height;
    for (const [name, ob] of objects) {
      const o = overlap(box, ob);
      if (o > 0) hits.push([t.slice(0, 40), name, Math.round(o), Math.round(area)]);
    }
  }
  return {hits, texts, objects: objects.length};
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
