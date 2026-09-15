// SHOT · FallbackPath — one action, two routes, and the whole claim is that the second is only reached
// when the first misses.
//
// The action lands on the left. Two routes leave it. The PREFERRED one lights and is travelled; the other
// stays an outline, with the condition that would send you down it written on the road itself. At the close
// the preferred route's destination is the only thing lit, because that is what usually happens.
//
// WHY IT IS NOT `InOrder`. A sequence says "then". A fallback says "only if not", and those are different
// claims about the same two boxes: in a sequence you reach step 2 by finishing step 1, and here you reach
// route 2 by route 1 FAILING. Drawn as an ordered pair of steps, "it looks for the tab you already have
// open, and only opens a link when it cannot find one" becomes "it looks for the tab, then opens a link",
// which is the opposite of the argument — it describes a product that opens a second tab every time.
//
// WHY IT WAS BUILT RATHER THAN CAST. A film about a desktop companion declared this form for a beat —
// "一次点击回到会话的路径" — and settled for a rack-focus between two text slots. An independent reviewer
// called it the content-fit test answered in the worst direction: five pieces of type and nothing else,
// every pixel except the glyphs topic-independent, and asked the question that decides it — would this beat
// look identical on a different topic with only the words changed? Literally yes. The beat's claim is a
// MECHANISM with real parts in it, so there was something to draw.
//
// AND IT IS A FORM, NOT A PRODUCT. A cache and its origin, a retry and its backoff, a font and its
// fallback, a fast path and a slow one: what it carries is "this is tried first, that is what happens when
// it is not there, and the difference between them is the point".
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic} from '../runtime/motion';
import {useDNA, readableOn} from '../runtime/dna';
import {CONTENT_TOP, contentBottom, fitTextPx, wrapLines, inkBlockH} from '../runtime/layout';
import {leading} from '../runtime/cjkType';

export const DURATION = 190; // ~6.3s

type Route = {label?: string; when?: string};

export const FallbackPath: React.FC<{
  /** what you DO — the one action both routes leave from */
  action?: string;
  /** the route that is tried first: where it goes, and (optionally) the condition that keeps you on it */
  first?: Route;
  /** the fallback: where it goes, and the condition that sends you down it. This is the one that must read
   *  as conditional, or the form has said "then" instead of "only if not". */
  then?: Route;
  /** one line under the fork */
  note?: string;
}> = ({
  // DEMO DEFAULTS, because every register in this library must be standalone-renderable — `npx remotion
  // still src/index.ts FallbackPath out.png` is how a shot is looked at, and it is also how the three
  // measurement scripts render one. Without them this shot threw, and `measure_ground_luma` /
  // `measure_ground_reach` recorded RENDER FAILED, which is a hole in the luminance guard rather than a
  // reading about the register. The guard below still bites where it is meant to: a FILM passes explicit
  // props, and one that names a single route is refused.
  action: ACTION = 'One click', first: FIRST = {label: 'Go to the one already open', when: 'if it is there'},
  then: THEN = {label: 'Open a new one', when: 'only when it is not'}, note: NOTE = '',
} = {}) => {
  const dna = useDNA();
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const U = Math.min(W, H);

  const action = String(ACTION ?? '').trim();
  const a = {label: String(FIRST?.label ?? '').trim(), when: String(FIRST?.when ?? '').trim()};
  const b = {label: String(THEN?.label ?? '').trim(), when: String(THEN?.when ?? '').trim()};
  if (!action || !a.label || !b.label) {
    throw new Error(
      'FallbackPath needs an `action` and BOTH routes (`first.label`, `then.label`). With one route there ' +
      'is no fallback and the form is an arrow; the whole claim is that the second is reached only when ' +
      'the first misses.');
  }
  const note = String(NOTE ?? '').trim();

  const BG = dna?.bgGrad ?? dna?.bg ?? 'radial-gradient(120% 110% at 42% 40%, #141a26, #080a0f 74%)';
  const FG = dna?.fg ?? '#eef2f8';
  const DIM = dna?.dim ?? '#7c8699';
  const ACC = dna?.accent ?? '#3dd6a4';
  const SURF = dna?.surface ?? '#131a26';
  const LINE = dna?.surfaceBorder ?? dna?.line ?? '#243149';
  const MONO = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';

  // THE MOMENTS. The fork is drawn before either route is taken, so the viewer sees that there ARE two
  // before being told which one happens — a route lit first and a second revealed after reads as two steps.
  const land = easeOutCubic(clamp01(seg(t, 0.04, 0.20)));
  const fork = easeOutCubic(clamp01(seg(t, 0.18, 0.40)));
  const take = easeInOutCubic(clamp01(seg(t, 0.44, 0.68)));
  const cond = easeOutCubic(clamp01(seg(t, 0.62, 0.82)));
  const noteIn = easeOutCubic(clamp01(seg(t, 0.74, 0.92)));

  const zTop = CONTENT_TOP, zBot = contentBottom(W, H);
  const portrait = H > W * 1.1;

  const notePx = Math.round(U * 0.020);
  const noteH = note ? Math.round(inkBlockH(notePx) * wrapLines(note, notePx, W * 0.86)) : 0;
  const zoneH = Math.max(U * 0.3, zBot - zTop - noteH - U * 0.03);
  const cy = zTop + zoneH / 2;

  const boxW = Math.round(W * (portrait ? 0.74 : 0.30));
  const pad = Math.round(U * 0.022);
  const actPx = fitTextPx(action, boxW - pad * 2, Math.round(U * 0.030), {usable: 1});
  const routePx = Math.round(U * 0.026);
  const whenPx = Math.round(U * 0.019);

  // Portrait stacks: the action on top, the two routes beneath it, because two boxes side by side in a
  // 1080-wide frame are each 400px and the type inside them wraps to four lines.
  const gapY = Math.round(zoneH * (portrait ? 0.20 : 0.26));
  const actX = portrait ? (W - boxW) / 2 : Math.round(W * 0.07);
  const actY = portrait ? zTop + Math.round(zoneH * 0.04) : Math.round(cy - inkBlockH(actPx) * 0.9);
  const colX = portrait ? (W - boxW) / 2 : Math.round(W * 0.52);
  const yA = portrait ? actY + Math.round(zoneH * 0.30) : Math.round(cy - gapY);
  const yB = portrait ? actY + Math.round(zoneH * 0.62) : Math.round(cy + gapY * 0.6);

  const routeBox = (r: Route, lit: number, isFallback: boolean, y: number) => {
    const ink = isFallback ? DIM : readableOn(dna?.bg ?? '#0b0f17', ACC, FG);
    return (
      <div style={{position: 'absolute', left: colX, top: y, width: boxW,
        padding: pad, boxSizing: 'border-box', borderRadius: Math.round(U * 0.014),
        background: isFallback ? 'transparent' : SURF,
        border: `${isFallback ? 1 : 2}px ${isFallback ? 'dashed' : 'solid'} ${isFallback ? LINE : ACC}`,
        opacity: fork * (isFallback ? 0.55 + 0.45 * (1 - take) : 1),
        transform: `translateX(${(1 - fork) * U * 0.02}px) scale(${1 + lit * 0.012})`,
        boxShadow: isFallback ? 'none' : `0 0 ${Math.round(U * 0.05 * lit)}px ${ACC}${lit > 0.5 ? '33' : '11'}`}}>
        <div style={{color: ink, textWrap: 'balance',
          font: `700 ${routePx}px/${leading(r.label ?? '', 1.25)} var(--f-display, Inter, system-ui, sans-serif)`}}>
          {r.label}
        </div>
        {r.when ? (
          <div style={{marginTop: Math.round(U * 0.010), color: DIM, opacity: cond, textWrap: 'balance',
            font: `500 ${whenPx}px/${leading(r.when, 1.3)} ${MONO}`, letterSpacing: '0.02em'}}>
            {r.when}
          </div>
        ) : null}
      </div>
    );
  };

  // The two roads. The preferred one is drawn as a solid rule that FILLS as it is taken; the fallback as a
  // dashed one that never fills — the ink on the road is the argument, not a decoration between boxes.
  const road = (y: number, isFallback: boolean) => {
    if (portrait) return null;
    const x0 = actX + boxW, x1 = colX;
    const midY = Math.round(cy);
    const toY = y + Math.round(U * 0.03);
    return (
      <React.Fragment>
        <div style={{position: 'absolute', left: x0, top: Math.min(midY, toY), width: 2,
          height: Math.abs(toY - midY), background: isFallback ? LINE : ACC,
          opacity: fork * (isFallback ? 0.5 : 1)}} />
        <div style={{position: 'absolute', left: x0, top: toY, height: 2,
          width: (x1 - x0) * (isFallback ? 1 : take),
          background: isFallback ? 'transparent' : ACC, opacity: fork,
          borderTop: isFallback ? `2px dashed ${LINE}` : 'none'}} />
      </React.Fragment>
    );
  };

  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      {/* THE ACTION — one thing you do, and both roads leave from it */}
      <div style={{position: 'absolute', left: actX, top: actY, width: boxW,
        padding: pad, boxSizing: 'border-box', borderRadius: Math.round(U * 0.014),
        background: SURF, border: `1px solid ${LINE}`, opacity: land,
        transform: `translateY(${(1 - land) * U * 0.02}px)`}}>
        <div style={{color: FG, textWrap: 'balance',
          font: `700 ${actPx}px/${leading(action, 1.2)} var(--f-display, Inter, system-ui, sans-serif)`}}>
          {action}
        </div>
      </div>

      {road(yA, false)}
      {road(yB, true)}
      {routeBox(a, take, false, yA)}
      {routeBox(b, 0, true, yB)}

      {note ? (
        <div style={{position: 'absolute', left: W * 0.07, top: zBot - noteH, width: W * 0.86,
          opacity: noteIn, color: DIM, textWrap: 'balance',
          font: `500 ${notePx}px/${leading(note, 1.35)} var(--f-body, system-ui, sans-serif)`}}>{note}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export default FallbackPath;
