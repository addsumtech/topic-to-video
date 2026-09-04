// FILM FINISH — the photographic layer between "rendered" and "shot".
//
// WHY THIS EXISTS. Measured side by side with the four reference launch films (Apple, OpenAI, Figma,
// Anthropic — references/launch-film-study.md), this tier's frames were structurally comparable and still
// read as WEB PAGES: perfectly flat fills, mathematically uniform edges, no optical response anywhere. All
// four references carry the opposite signature — grain over every surface, luminance falling off toward the
// corners, light that arrives from somewhere — because they were either photographed for real or finished to
// read as if they had been. A viewer cannot name any of this; they just call one "a video" and the other
// "slides". The html tier reached the same conclusion years ago and ships a fixed-seed film grain in
// motifs.css; the remotion tier had structure (registers), identity (DNA), material (motif) — and no optics.
//
// THREE ELEMENTS, ALL STATIC:
//   grain     a photographic speckle over the whole frame, from an SVG feTurbulence tile with a FIXED SEED,
//             repeated — deterministic, seekable, identical on every render, cheap (one small tile).
//   vignette  luminance falling off toward the corners. The inner 58% of the field is completely
//             untouched, so content and the caption zone (bottom-centre, well inside) keep their ground.
//   light     a direction for the film's key: a barely-there brightening where the light falls and an even
//             fainter settling opposite. This is what separates "lit" from "filled".
//
// WHAT THIS DELIBERATELY IS NOT. It is not the automatic light ARC that was built and then withdrawn from
// the default path (light_plan.py --write refuses without --accept-risk): that changed the film's luminance
// OVER TIME, a directorial decision. This layer is a static print characteristic, the same on frame 1 and
// frame 3000 — nothing about it can drift, pump, or fight a beat's own ground.
//
// DEFAULTS LIVE IN THE PRESETS, tuned per system (a CRT wants more falloff than a keynote; paper wants more
// tooth than glass). A film opts out with `design_dna.finish: 'none'`; an UN-THEMED film gets nothing at
// all, because the null-DNA rule is that no theming machinery may alter the original look.
import React from 'react';
import type {DesignDNA} from './dna';

export type FilmFinish = {
  /** 0..1 — opacity of the grain tile. 0.04–0.08 is film; past ~0.12 it reads as damage. */
  grain?: number;
  /** 0..1 — the black alpha reached at the far corners. The inner 58% stays untouched. */
  vignette?: number;
  /** where the key light falls; 'none' = an unlit, even field (a terminal, a scanner bed) */
  light?: 'top' | 'bottom' | 'none';
};

// ONE fixed seed, forever. The grain must be the same on every render of every film — it is a print
// characteristic, not content — and any variation between two renders of the same frame would break the
// determinism harness (same command, same bytes).
const GRAIN_TILE = 220;
const GRAIN_SVG =
  `<svg xmlns='http://www.w3.org/2000/svg' width='${GRAIN_TILE}' height='${GRAIN_TILE}'>` +
  `<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='2' seed='11' ` +
  `stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter>` +
  `<rect width='${GRAIN_TILE}' height='${GRAIN_TILE}' filter='url(%23g)'/></svg>`;
const GRAIN_URI = `url("data:image/svg+xml,${GRAIN_SVG}")`;

/**
 * The film-wide finish. Mount ABOVE the scenes and the motif, BELOW the caption HUD — grain over burned-in
 * type reads as compression artefacts, and the caption's contrast maths assume the ground it measured.
 * Renders nothing without a themed DNA carrying a finish.
 */
export const FilmFinishLayer: React.FC<{dna?: DesignDNA | null; finish?: FilmFinish | 'none' | null}> = ({
  dna, finish,
}) => {
  const raw = finish ?? dna?.finish;
  const f = raw === 'none' ? null : raw;
  if (!dna || !f) return null;
  const grain = Math.max(0, Math.min(1, f.grain ?? 0));
  const vig = Math.max(0, Math.min(1, f.vignette ?? 0));
  const light = f.light ?? 'none';
  const layers: React.ReactNode[] = [];
  if (light !== 'none') {
    // The key: a whisper of white where the light arrives, a fainter settling of black opposite. Alphas are
    // fixed, not configurable — a stronger version stops being light and starts being a gradient overlay,
    // which is exactly the flat-fill look this layer exists to leave behind.
    const from = light === 'top' ? '180deg' : '0deg';
    layers.push(
      <div key="l" style={{position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `linear-gradient(${from}, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 30%, ` +
                    `rgba(0,0,0,0) 68%, rgba(0,0,0,0.07) 100%)`}} />,
    );
  }
  if (vig > 0) {
    layers.push(
      <div key="v" style={{position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `radial-gradient(120% 120% at 50% 46%, rgba(0,0,0,0) 58%, rgba(0,0,0,${
          (vig * 0.55).toFixed(3)}) 86%, rgba(0,0,0,${vig.toFixed(3)}) 100%)`}} />,
    );
  }
  if (grain > 0) {
    layers.push(
      <div key="g" style={{position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: GRAIN_URI, backgroundSize: `${GRAIN_TILE}px ${GRAIN_TILE}px`,
        mixBlendMode: 'overlay', opacity: grain}} />,
    );
  }
  if (!layers.length) return null;
  return <>{layers}</>;
};

export default FilmFinishLayer;
