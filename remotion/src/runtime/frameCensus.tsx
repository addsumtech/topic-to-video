// ONE CENSUS PER FRAME, after what it measures is drawn. PlateClearAudit and MediaResAudit (and the type-glide census)
// each carried this loop: hold the frame (delayRender), wait, measure, log one tagged line, release. They waited for
// different things, and the plate census waited for nothing — it judged a plate "clear" on frames where a KineticText
// had not drawn its glyphs yet (audit 2026-11-15, step 6). What to wait for is now said once:
//   fonts    the BUNDLED faces (kineticDom facesReady) — never `document.fonts.ready`, which resolves before they are
//            even added (fonts.ts), so a census then measured the fallback face
//   kinetic  every KineticText has measured and drawn (kineticDom kineticIdle)
//   images   every <img> decoded (one still decoding reports a natural size of 0 and would be skipped)
import React from 'react';
import {continueRender, delayRender, useCurrentFrame} from 'remotion';
import {facesReady, kineticIdle} from './kineticDom';

export type CensusWaits = {fonts?: boolean; kinetic?: boolean; images?: boolean};

export const useFrameCensus = (label: string, tag: string, measure: (host: HTMLDivElement) => object,
  waits: CensusWaits = {fonts: true, kinetic: true}): React.RefObject<HTMLDivElement | null> => {
  const frame = useCurrentFrame();
  const ref = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const handle = delayRender(`${label}, frame ${frame}`, {timeoutInMilliseconds: 60000});
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
        if (waits.fonts) {
          try { await facesReady(); } catch { /* the font gate reports a face that failed */ }
        }
        if (waits.kinetic) await kineticIdle();
        if (waits.images) await Promise.all(Array.from(host.ownerDocument.images).map((im) => im.decode().catch(() => null)));
        await new Promise((res) => requestAnimationFrame(() => res(null)));
      }
      if (!released && ref.current) {
        // eslint-disable-next-line no-console
        console.log(tag + JSON.stringify({f: frame, ...measure(ref.current)}));
      }
      release();
    })();
    return release;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame]);
  return ref;
};
