// SHOT · ProductPage — the beat SHOWS a real product (or a page, a document) as itself: a 2x capture under a 2.5D
// page camera, its elements landing in their slots, lifting toward the lens, typed into, clicked, called out.
// (references/promo-film.md; the same camera and layers as the promo film, here inside a narrated film.)
//
// WHY A REGISTER. The study of the showcase product films (references/craft-standard.md, promo-film.md) found their
// quality starts from showing the product AS ITSELF — a real capture, sharp at every zoom — where this library drew a
// mock of it. This register brings that into any film: a launch beat, a "here is the paper" beat, a "this is the
// page that says so" beat. The capture is the film's own file (`scripts/promo_capture.py` writes it with the boxes
// of its elements), so nothing on screen is invented: every word is the product's, or a layer's prop.
//
// PROPS. `src` (a file in the film's folder), `w`/`h` its CSS size (pixels / 2), `keys` the camera ({f, cx, cy, zoom,
// rx, ry, rz, ease} — see promo/PageCam), `acts` the page's verbs (pop / lift / focus / ring / type / cursor /
// callout — promo/Layers), all timed in frames over `nominal` (default: the last key's frame); the beat's real
// length stretches that timeline, entrances kept at their authored speed (craftMotion.fitTable). A layer whose
// words the voice speaks lands ON the word: cue key `acts.<i>` (sync binds an act's `text` like any prop).
// The camera frames the zone ABOVE the caption band and the page fades into the film's ground under it, so the
// burned caption sits on the frame's own ground.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useDNA} from '../runtime/dna';
import {useCues} from '../runtime/cue';
import {rows} from '../runtime/rows';
import {requireEvidence} from '../runtime/evidence';
import {SceneDurationContext, SEAM_FRAMES, ENTRY_T} from '../runtime/motion';
import {captionBand, CONTENT_TOP} from '../runtime/layout';
import {LookContext, lookFromDna, alpha} from '../promo/kit';
import {PageCam, Ground, type CamKey} from '../promo/PageCam';
import {Layers, type LayerSpec} from '../promo/Layers';

export const DURATION = 150; // 5s
// the shot frames and moves its own camera: coverage leaves it alone
export const CAMERA = 'directed';
// its camera is one continuous path and its items are cued one by one: the beat's clock is never warped (sync_qa)
export const CLOCK = 'own';

type Props = {src?: string; w?: number; h?: number; keys?: CamKey[]; acts?: LayerSpec[]; nominal?: number; maxZoom?: number};

/** Stretch a timeline authored over `nominal` frames to `dur`: the first 45 % (the entrances) keeps its speed, the
 *  rest takes the extra time — through a SMOOTH map (f + extra * u²), never a corner: a camera move spanning a
 *  piecewise-linear pivot changes speed in one frame, which reads as a stutter. */
const stretch = (f: number, nominal: number, dur: number) => {
  if (dur <= nominal) return (f * dur) / nominal;
  const pivot = nominal * 0.45, extra = dur - nominal;
  const u = Math.min(1, Math.max(0, (f - pivot) / Math.max(1, nominal - pivot)));
  return f + extra * u * u + (f > nominal ? (f - nominal) * (2 * extra) / Math.max(1, nominal - pivot) : 0);
};

export const ProductPage: React.FC<Props> = ({src: srcIn, w = 1440, h = 900, keys: keysIn, acts: actsIn, nominal, maxZoom}) => {
  const src = requireEvidence('ProductPage', 'src', srcIn, 'the real capture of the product or page this beat shows');
  const keys = rows<CamKey>(keysIn, 'keys', 'ProductPage');
  const layers = rows<LayerSpec>(actsIn, 'acts', 'ProductPage');
  const dna = useDNA();
  const look = lookFromDna(dna);
  const {width: W, height: H, durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const dur = sceneDur ?? durationInFrames;
  const cues = useCues();
  const camKeys: CamKey[] = keys.length ? keys : [{f: 0, cx: w / 2, cy: h / 2, zoom: 1.0}, {f: DURATION, cx: w / 2, cy: h / 2, zoom: 1.05, ease: 'smooth'}];
  const nom = nominal ?? Math.max(30, camKeys[camKeys.length - 1].f);
  // the register-t at which the voice speaks a layer's words -> a frame (the same mapping runtime/motion uses)
  const pad = Math.min(SEAM_FRAMES, Math.floor(Math.max(0, dur - 1) / 3));
  const spanF = Math.max(1, dur - 1 - 2 * pad);
  const cueFrame = (i: number): number | null => {
    const r = cues.readT(`acts.${i}`);
    return r === null ? null : pad + ((r - ENTRY_T) / (1 - ENTRY_T)) * spanF;
  };
  const T = (f: number) => stretch(f, nom, dur);
  const timedKeys = camKeys.map((k) => ({...k, f: T(k.f)}));
  const timedLayers = layers.map((l, i) => {
    const cf = cueFrame(i);
    const shift = (at: number) => (cf !== null ? cf - 8 : T(at));      // land ON the word: the entrance leads it a little
    switch (l.kind) {
      case 'cursor': {
        const d = cf !== null ? cf - T(l.path[0].f) : 0;
        return {...l, path: l.path.map((p) => ({...p, f: T(p.f) + d})), clicks: (l.clicks ?? []).map((c) => T(c) + d)};
      }
      case 'lift': {
        const a = shift(l.at);
        return {...l, at: a, until: Math.max(a + 20, T(l.until) + (a - T(l.at)))};
      }
      default: {
        const a = shift((l as {at: number}).at);
        const u = (l as {until?: number}).until;
        return {...l, at: a, ...(u !== undefined ? {until: Math.max(a + 20, T(u) + (a - T((l as {at: number}).at)))} : {})};
      }
    }
  }) as LayerSpec[];
  const zoneBottom = H - captionBand(W, H);
  const focusY = (CONTENT_TOP + zoneBottom) / 2 / H;
  return (
    <LookContext.Provider value={look}>
      <AbsoluteFill style={{background: look.ground}}>
        <Ground light={{x: 0.5, y: 0.25}} />
        {(
          <PageCam src={src} w={w} h={h} keys={timedKeys} maxZoom={maxZoom} focusY={focusY}>
            <Layers layers={timedLayers} src={src} pageW={w} pageH={h} />
          </PageCam>
        )}
        {/* the caption's ground: the page fades into the film's own ground under the burned caption */}
        <AbsoluteFill style={{pointerEvents: 'none', background: `linear-gradient(to bottom, ${alpha(look.ground, 0)} ${(zoneBottom / H) * 100 - 12}%, ${alpha(look.ground, 0.9)} ${(zoneBottom / H) * 100 - 1}%, ${alpha(look.ground, 0.97)} 100%)`}} />
      </AbsoluteFill>
    </LookContext.Provider>
  );
};
export default ProductPage;
