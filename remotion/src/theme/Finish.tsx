import React from 'react';
import {AbsoluteFill} from 'remotion';
import type {Theme} from './tokens';

// Finishing pass (OUTER 2D — never on a preserve-3d ancestor): style-driven graded wash + moving film grain.
// This is the single biggest "premium / filmic" uplift and it is deterministic (grain scroll = f(frame)).

const NOISE =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E" +
  "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E" +
  "%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E\")";

// Per-MOOD colour grade, keyed off the deck's real visual style (theme.py emits one of ~18 names).
// Styles are grouped into grade families so every named style gets an intentional wash — not a silent
// fallback. A cool/neutral 'technical' wash for blueprint/terminal/swiss; a warm cinematic split for
// editorial/noir/cinematic; a saturated push for cyberpunk/vaporwave; a soft neutral for clean styles.
// Per-REGISTER colour grade, keyed off the deck's real visual style (theme.py emits one of 18 names). Each
// style gets a distinct split-tone so two videos LOOK like different films — not the old fold-to-4-washes,
// where 18 styles collapsed to a single tint. Kept subtle (alpha <=0.18, soft-light) so it grades, never
// tints. GLOBAL per video (not per shot). Unknown/empty style -> the cinematic split.
const STYLE_TO_GRADE: Record<string, string> = {
  // FILMIC — cool/steel shadow -> warm highlight
  cinematic:   'linear-gradient(122deg, rgba(18,52,92,0.16) 0%, rgba(255,176,112,0.10) 100%)',
  noir:        'linear-gradient(122deg, rgba(30,40,60,0.18) 0%, rgba(210,205,190,0.06) 100%)',
  editorial:   'linear-gradient(120deg, rgba(60,30,40,0.12) 0%, rgba(240,225,205,0.08) 100%)',
  artdeco:     'linear-gradient(122deg, rgba(20,55,50,0.14) 0%, rgba(214,176,90,0.11) 100%)',
  watercolor:  'linear-gradient(115deg, rgba(60,95,110,0.10) 0%, rgba(230,200,175,0.09) 100%)',
  // TECH / NEON — saturated complements
  cyberpunk:   'linear-gradient(122deg, rgba(110,30,170,0.15) 0%, rgba(40,210,225,0.12) 100%)',
  vaporwave:   'linear-gradient(120deg, rgba(255,80,190,0.12) 0%, rgba(60,150,255,0.12) 100%)',
  terminal:    'linear-gradient(180deg, rgba(0,40,10,0.14) 0%, rgba(60,255,120,0.07) 100%)',
  blueprint:   'linear-gradient(135deg, rgba(10,40,90,0.16) 0%, rgba(150,200,240,0.06) 100%)',
  brutalism:   'linear-gradient(180deg, rgba(20,20,20,0.14) 0%, rgba(200,255,0,0.05) 100%)',
  // CLEAN / GEOMETRIC — near-neutral + a signature kick
  swiss:       'linear-gradient(180deg, rgba(10,20,40,0.06) 0%, rgba(230,60,50,0.03) 100%)',
  bauhaus:     'linear-gradient(122deg, rgba(20,40,120,0.08) 0%, rgba(240,180,40,0.06) 100%)',
  memphis:     'linear-gradient(120deg, rgba(255,80,120,0.09) 0%, rgba(0,200,190,0.08) 100%)',
  risograph:   'linear-gradient(120deg, rgba(255,90,60,0.10) 0%, rgba(50,110,220,0.08) 100%)',
  manga:       'linear-gradient(180deg, rgba(20,20,25,0.10) 0%, rgba(255,255,255,0.04) 100%)',
  cartographic:'linear-gradient(120deg, rgba(50,90,70,0.09) 0%, rgba(200,150,90,0.07) 100%)',
  // SOFT MATERIAL — cool -> violet/rose, dreamy
  glassmorphism:'linear-gradient(145deg, rgba(40,80,160,0.10) 0%, rgba(180,140,240,0.08) 100%)',
  claymorphism: 'linear-gradient(145deg, rgba(120,100,240,0.09) 0%, rgba(255,150,180,0.08) 100%)',
};
const FALLBACK_GRADE = STYLE_TO_GRADE.cinematic;

// The full finishing stack, in cinematographer's order: KEY LIGHT (lift the centred subject) -> GRADE
// (mood tint) -> GRAIN (unify) -> VIGNETTE (darken edges, draw the eye). Key-light + a MODERATED vignette
// = exposure discipline: the focal subject (the camera centres it) stays bright and legible while the
// edges fall off, instead of a heavy vignette crushing content into murk. Vignette is here (one place),
// not duplicated per scene. All layers are OUTER 2D — never on a preserve-3d ancestor.
// PER-BEAT grade (was GLOBAL/frame-invariant — the audit's axis C). `energy` is the beat's HEAT 0..1
// (calm..climax): a bold/climax beat runs HOTTER (a stronger wash + a warm amber lift), a calm beat cools
// and softens (a steel drift). `dur` lets the grade gently SWELL toward the middle so it breathes instead
// of sitting dead. When `energy` is undefined the grade is EXACTLY the old global look (opacity 1, no
// warm/cool, no swell) — zero regression for any scene that doesn't opt in.
export const Finish: React.FC<{frame: number; theme: Theme; energy?: number; dur?: number; post?: string}> = ({frame, theme, energy, dur, post}) => {
  // Grain FLOOR (video tier only): theme.py leaves --grain-amount 0 on ~12 of 18 styles (incl. the
  // filmic 'cinematic'/'editorial'), which the HTML tier wants crisp — but a moving video composites
  // separate planes and a soft-light grade that BAND without a little sensor texture. A subtle 0.03 floor
  // (well below the printed-style values) unifies the frame and hides banding, without touching theme.py.
  // POST profile (from the ATMOSPHERE): 'crt' = a CRT terminal world (scanlines + rolling scan + phosphor);
  // 'clean' = a crisp product world (grain off, vignette softened); undefined/'film' = the default look.
  const isCrt = post === 'crt';
  const isClean = post === 'clean';
  const grainBase = Math.max(0.03, Math.min(0.2, parseFloat(theme.grainAmount || '0') || 0));
  const grainAmount = isClean ? 0 : (isCrt ? Math.max(grainBase, 0.06) : grainBase);
  const scanRoll = (frame * 3) % 100; // deterministic CRT scan roll
  const grade = STYLE_TO_GRADE[theme.style] || FALLBACK_GRADE;  // per-register split-tone (unknown -> cinematic)
  const off = (frame * 11) % 200; // deterministic grain scroll

  const hasHeat = energy != null;
  const heat = hasHeat ? Math.max(0, Math.min(1, energy as number)) : 0.5;
  const D = dur && dur > 1 ? dur : null;
  // subtle swell (deterministic): peaks mid-beat, so the wash breathes rather than freezing (only when heated)
  const swell = hasHeat && D ? 1 + 0.08 * Math.sin(Math.PI * Math.max(0, Math.min(1, frame / D))) : 1;
  // heat 0 -> 0.72, 0.5 -> 1.0 (== old neutral), 1 -> 1.28. Undefined energy -> exactly 1.0 (byte-identical).
  const gradeOpacity = hasHeat ? (0.72 + 0.56 * heat) * swell : 1;
  const warm = hasHeat ? Math.max(0, heat - 0.5) * 2 : 0;   // ->1 toward a climax
  const cool = hasHeat ? Math.max(0, 0.5 - heat) * 2 : 0;   // ->1 toward a calm beat

  return (
    <>
      {/* KEY LIGHT — a soft central lift so the framed subject reads (legibility), subtle so it's not a hotspot */}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          mixBlendMode: 'soft-light',
          background: 'radial-gradient(70% 58% at 50% 44%, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0) 60%)',
        }}
      />
      {/* Graded wash — opacity scales with the beat's HEAT (+ a gentle swell); default 1 = the old look */}
      <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'soft-light', background: grade, opacity: gradeOpacity}} />
      {/* WARM lift on a hot/climax beat (amber) — the payoff runs warmer; soft-light so it grades, never tints */}
      {warm > 0.02 ? (
        <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'soft-light', opacity: 0.15 * warm,
          background: 'radial-gradient(85% 72% at 50% 46%, rgba(255,178,96,0.9) 0%, rgba(255,150,60,0) 70%)'}} />
      ) : null}
      {/* COOL drift on a calm beat (steel) — intros/close-outs cool down */}
      {cool > 0.02 ? (
        <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'soft-light', opacity: 0.12 * cool,
          background: 'linear-gradient(180deg, rgba(70,110,170,0.85) 0%, rgba(40,60,110,0.5) 100%)'}} />
      ) : null}
      {/* Film grain */}
      {grainAmount > 0 && (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
            mixBlendMode: 'overlay',
            opacity: grainAmount,
            backgroundImage: NOISE,
            backgroundRepeat: 'repeat',
            backgroundPosition: `${off}px ${off}px`,
          }}
        />
      )}
      {/* VIGNETTE — moderated but REAL: the falloff must start INSIDE the frame. The old 135%/60% radii
          put every visible corner below the first (transparent) stop, so it darkened zero pixels; here the
          clear centre ends at 40% and the corners (~0.62 of the gradient radius) fall to ~0.12 alpha —
          a gentle exposure roll-off that draws the eye, not a heavy crush. Verified from a corner pixel. */}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background: !isClean
            ? 'radial-gradient(118% 118% at 50% 47%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.34) 100%)'    // film/crt
            : 'radial-gradient(125% 125% at 50% 47%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.18) 100%)',   // clean: airy but still darkens corners to 0.18
        }}
      />
      {/* CRT terminal post (the 'crt' atmosphere): fixed SCANLINES (multiply) + a slow rolling scan band +
          a faint phosphor-green cast. All deterministic (roll = f(frame)); a 2D overlay, never on a 3D
          ancestor, so the preserve-3d depth is untouched. */}
      {isCrt ? (
        <>
          <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'multiply', opacity: 0.55,
            background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.55) 0px, rgba(0,0,0,0.55) 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 3px)'}} />
          <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'overlay', opacity: 0.05,
            background: `linear-gradient(180deg, rgba(120,255,170,0) ${Math.max(0, scanRoll - 12)}%, rgba(120,255,170,0.9) ${scanRoll}%, rgba(120,255,170,0) ${Math.min(100, scanRoll + 12)}%)`}} />
          <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'soft-light', opacity: 0.10,
            background: 'radial-gradient(80% 70% at 50% 46%, rgba(80,255,150,0.7) 0%, rgba(80,255,150,0) 72%)'}} />
        </>
      ) : null}
    </>
  );
};
