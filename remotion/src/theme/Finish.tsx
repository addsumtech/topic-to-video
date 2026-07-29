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
const GRADE_FAMILIES: Record<string, string> = {
  warm: 'linear-gradient(122deg, rgba(30,60,110,0.14) 0%, rgba(255,180,120,0.08) 100%)',   // cinematic warm/cool split
  cool: 'linear-gradient(135deg, rgba(20,40,80,0.12) 0%, rgba(90,150,200,0.05) 100%)',      // technical / blueprint
  neon: 'linear-gradient(122deg, rgba(120,40,180,0.13) 0%, rgba(40,200,220,0.09) 100%)',    // cyberpunk / vaporwave
  soft: 'linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.02) 100%)',               // clean/minimal
};
const STYLE_TO_FAMILY: Record<string, keyof typeof GRADE_FAMILIES> = {
  editorial: 'warm', noir: 'warm', cinematic: 'warm', artdeco: 'warm', watercolor: 'warm',
  blueprint: 'cool', terminal: 'cool', cartographic: 'cool', brutalism: 'cool',
  cyberpunk: 'neon', vaporwave: 'neon', memphis: 'neon',
  swiss: 'soft', bauhaus: 'soft', glassmorphism: 'soft', claymorphism: 'soft', risograph: 'soft', manga: 'soft',
};

// The full finishing stack, in cinematographer's order: KEY LIGHT (lift the centred subject) -> GRADE
// (mood tint) -> GRAIN (unify) -> VIGNETTE (darken edges, draw the eye). Key-light + a MODERATED vignette
// = exposure discipline: the focal subject (the camera centres it) stays bright and legible while the
// edges fall off, instead of a heavy vignette crushing content into murk. Vignette is here (one place),
// not duplicated per scene. All layers are OUTER 2D — never on a preserve-3d ancestor.
export const Finish: React.FC<{frame: number; theme: Theme}> = ({frame, theme}) => {
  const grainAmount = Math.max(0, Math.min(0.2, parseFloat(theme.grainAmount || '0') || 0));
  const grade = GRADE_FAMILIES[STYLE_TO_FAMILY[theme.style] || 'warm'];  // unknown/empty style -> cinematic warm
  const off = (frame * 11) % 200; // deterministic grain scroll

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
      {/* Graded wash */}
      <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'soft-light', background: grade}} />
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
      {/* VIGNETTE — moderated (edges only): wider clear centre + gentler falloff than a heavy crush */}
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background: 'radial-gradient(135% 135% at 50% 46%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.30) 100%)',
        }}
      />
    </>
  );
};
