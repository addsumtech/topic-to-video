// SHOT · Page Write — a REAL page, captured, writing itself out block by block behind a caret.
//
// WHAT IT ARGUES, and why nothing drawn can argue it. Every other register in this library, including the
// ones added this week, DRAWS the product: a window with the topic's nav in it, a card with the topic's
// title on it. That is honest and it is still a drawing, and a drawing cannot make the one claim a document
// shot exists to make — that this is the actual artefact, laid out by the actual product, with the real
// typesetting and the real sidebar. So the page is baked from a live render (`scripts/capture_page.py`) and
// filmed. The persuasive weight is entirely in it being real; a mock here would be worse than no shot.
//
// WHY A LAYOUT AND NOT JUST THE PICTURE. A screenshot can be panned across; that is a slideshow with a
// camera. What makes it a SHOT is the boxes: knowing which rectangle is the third paragraph lets the page
// UNCOVER in reading order, which is the difference between "here is a document" and "this document is being
// written". The boxes come from the same page load as the pixels, so they cannot disagree — a hand-marked
// layout is wrong the first time the page changes, and wrong invisibly.
//
// THE MASK IS PAINTED IN THE PAGE'S OWN GROUND, recorded by the capture for exactly this reason. Any other
// colour and the reveal is a grey bar travelling across the document instead of text arriving.

import React from 'react';
import {AbsoluteFill, useVideoConfig, staticFile} from 'remotion';
import {useT, seg, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA} from '../runtime/dna';
import {requireEvidence} from '../runtime/evidence';
import {captionBand} from '../runtime/layout';
import {PageCam2D, camAt, pageToScreen, fitScale, clampToPage, type CamKey} from '../runtime/pageCam2D';

export const DURATION = 165; // 5.5s

const ACC_D0 = '#f0a500';
export type PageBlock = {x: number; y: number; w: number; h: number; tag?: string; text?: string};

// A block small enough to be a nav entry or a date is furniture, not a line being written: revealing every
// one of them spends the shot's whole clock on the sidebar. The page's own body column is what writes.
const WRITES = (b: PageBlock, pageW: number) => b.w > pageW * 0.18 && b.h >= 10;

export const PageWrite: React.FC<{
  src?: string;
  pageW?: number;
  pageH?: number;
  bg?: string;
  blocks?: PageBlock[];
}> = ({src, pageW = 1400, pageH = 900, bg = '#ffffff', blocks = []} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  // THE CAMERA FILLS THE CONTENT ZONE, NOT THE FRAME. A page camera that covers the whole frame puts the
  // page's own type into the caption band, and the burned subtitle then lands on it — measured on a real
  // film, this shot's band ground read 0.95 mid-beat (a white page) against a film that declares itself
  // dark, so the caption was white on white and unreadable, and one beat later the same band was 0.03.
  // No static declaration can follow a ground that flips inside one shot; reserving the band means the
  // caption always sits on the film's own ground, which is the contract every other register keeps.
  const VIEW_H = H - captionBand(W, H);
  const ACC = dna?.accent ?? ACC_D0;
  // The premise IS the real page. Without one this draws a camera move over an empty rectangle, which
  // composes perfectly and says nothing — so it refuses, in the library's own words.
  const texture = requireEvidence('PageWrite', 'src', src,
    'the captured page it films (scripts/capture_page.py writes it into public/textures/)');
  const body = blocks.filter((b) => WRITES(b, pageW)).sort((a, b) => a.y - b.y || a.x - b.x);
  if (!body.length) {
    throw new Error(
      'PageWrite needs `blocks` from the capture — the layout json written beside the texture. With the ' +
      'picture and no boxes it can only pan across a screenshot, which is a slideshow with a camera on it.');
  }

  // THE WRITING IS BUDGETED BEFORE IT IS ANIMATED. Twenty blocks at a comfortable pace do not fit in five
  // seconds, and the way that fails is silent: the last third of the document never appears and the frame
  // looks like a page that stops halfway. So the per-block cue is derived from the count.
  const WRITE_END = 0.72;                       // the rest of the clip reads the finished page
  const step = (WRITE_END - 0.06) / body.length;
  const span = Math.min(0.16, step * 2.2);      // one block's own wipe, overlapping its neighbour's

  // The camera opens on the first block and pulls out to the whole page as the writing lands, so the shot
  // ends on the document entire — which is the frame that says "this is a real page", and it has to be the
  // one left on screen.
  const first = body[0];
  const keys: CamKey[] = [
    {at: 0, x: first.x + first.w / 2, y: first.y + first.h / 2,
     s: Math.min(W * 0.72 / Math.max(1, first.w), fitScale(W, VIEW_H, pageW, pageH) * 2.6)},
    {at: 0.10, x: first.x + first.w / 2, y: first.y + first.h / 2,
     s: Math.min(W * 0.72 / Math.max(1, first.w), fitScale(W, VIEW_H, pageW, pageH) * 2.6)},
    {at: 0.80, x: pageW / 2, y: pageH / 2, s: fitScale(W, VIEW_H, pageW, pageH)},
    {at: 1, x: pageW / 2, y: pageH / 2, s: fitScale(W, VIEW_H, pageW, pageH)},
  ];
  const cam = clampToPage(camAt(keys, t, easeInOutCubic), W, VIEW_H, pageW, pageH);

  // the caret rides the leading edge of whichever block is being written — ONE of them, ever. Two carets on
  // a page is two people typing, which is not what the shot is claiming.
  let writing = -1;
  for (let i = 0; i < body.length; i++) {
    const a = 0.06 + i * step;
    if (t >= a && t <= a + span) writing = i;
  }

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? '#0b0d12', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: VIEW_H, overflow: 'hidden'}}>
      <PageCam2D cam={cam} W={W} H={VIEW_H} pageW={pageW} pageH={pageH}>
        <img src={staticFile(texture)} width={pageW} height={pageH} alt=""
          style={{display: 'block', width: pageW, height: pageH}} />
        {body.map((b, i) => {
          // the mask RETRACTS to the right, so the block appears the way it was written
          const u = easeOutCubic(clamp01(seg(t, 0.06 + i * step, 0.06 + i * step + span)));
          if (u >= 1) return null;
          return (
            <div key={i} style={{position: 'absolute', left: b.x + b.w * u, top: b.y - 2,
              width: Math.max(0, b.w * (1 - u)) + 4, height: b.h + 4, background: bg}} />
          );
        })}
      </PageCam2D>
      </div>

      {/* the caret is SCREEN space and a fixed width, so it stays a pen nib rather than growing with the
          page as the camera pulls out */}
      {writing >= 0 ? (() => {
        const b = body[writing];
        const u = easeOutCubic(clamp01(seg(t, 0.06 + writing * step, 0.06 + writing * step + span)));
        const p = pageToScreen(cam, W, VIEW_H, b.x + b.w * u, b.y + b.h / 2);
        const h = Math.max(6, b.h * cam.s * 0.92);
        return <div style={{position: 'absolute', left: p.x - 1, top: p.y - h / 2,
          width: Math.max(2, Math.round(Math.min(W, H) * 0.0035)), height: h, background: ACC}} />;
      })() : null}
    </AbsoluteFill>
  );
};
export default PageWrite;
