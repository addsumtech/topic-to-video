// SHOT · Cube Rotate — content lives on the four side FACES of a 3D cube; the camera orbits, landing on and
// holding each face in turn (3/4 tilt, floor reflection, rim light). Pure CSS 3D (preserve-3d) — no WebGL.
// The "one subject, several sides" spatial register (family B). Deterministic (orbit angle = fn of t).
//
// PALETTE — every chromatic colour is derived from the DNA. The face BADGE used to blend its tone into a
// hardcoded blue (#2b3ac6), so on a green+amber `data` film the chip shipped teal-to-BLUE on one beat and
// amber-to-BLUE-PURPLE on the next (hues 195-240 deg, a colour that film never declares). The chip is now a
// tint-to-shade step of its OWN tone, so it can only ever land inside the film's hues, and its ink flips on
// the chip's measured luminance so a dark derived tone still carries a legible label. Ground / ink / edge /
// face-fill read DNA tokens too; the *_D0 constants below are the register's identity for the no-DNA case.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, lerp, clamp01, easeInOutCubic, easeOutCubic} from '../runtime/motion';
import {useDNA, dnaPalette, mix, tint, shade} from '../runtime/dna';
import {TITLE_Y, CONTENT_TOP, contentBottom} from '../runtime/layout';
import {fitTextOnNLines} from '@remotion/layout-utils';

export const DURATION = 165; // 5.5s

// no-DNA fallbacks (the register's own identity; used verbatim when no DesignDNA is provided)
const BG_D0 = '#080a11';
const GRAD_D0 = `radial-gradient(120% 100% at 50% 36%, #12162c, ${BG_D0} 70%)`;
const TONES_D0 = ['#5b8cff', '#c07bff', '#ff6f91', '#31c9a6'];
const FACE_D0 = 'linear-gradient(155deg, #161a2b, #0d1018)';
const EDGE_D0 = '#252a40';
const DIM_D0 = '#aeb6ca';
const INK_D0 = '#eef2ff';
const ONDARK_D0 = '#0b0f18';

// Relative luminance of a hex colour. Achromatic maths - it picks WHICH of the system's two inks reads on a
// chip, it never introduces a colour. Anything unparseable returns 1 (so the dark ink), which is the safe
// default on this register's bright accents.
const lum = (c: string): number => {
  const raw = String(c).trim().replace('#', '');
  const h = raw.length === 3 ? raw.split('').map((x) => x + x).join('') : raw;
  if (h.length < 6) return 1;
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  if (!Number.isFinite(r + g + b)) return 1;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
};

// "A - B" splits into a badge "A" + a label "B". En/em dashes count too, so copy written with a longer dash
// splits the same way instead of dumping the whole string into the label line.
const FACE_SPLIT = /\s[-–—]\s/;

export const CubeRotate: React.FC<{faces?: string[]; title?: string}> = ({
  faces: FACES = ['Plan', 'Build', 'Ship', 'Learn'], title: TITLE = 'The loop'} = {}) => {
  const t = useT();
  const dna = useDNA();
  const TONES = dnaPalette(dna, 4) ?? TONES_D0;
  const INK = dna?.fg ?? INK_D0, DIM = dna?.dim ?? DIM_D0, EDGE = dna?.surfaceBorder ?? EDGE_D0;
  const FACE_BG = dna ? `linear-gradient(155deg, ${dna.surface}, ${dna.bg})` : FACE_D0;
  const RADIUS = dna?.radius ?? 22, BORDER = dna?.borderWidth ?? 1;
  const dispFace = dna?.fontDisplay ?? 'Inter, system-ui, sans-serif';
  const monoFace = dna?.fontMono ?? '"JetBrains Mono", monospace';
  const {width: W, height: H} = useVideoConfig();

  // GEOMETRY IN FRACTIONS so the shot reflows at 9:16 / 1:1 / 4:5 / 4:3. At 16:9 this resolves to the
  // register's original 660px cube. A narrow frame must cap the cube by WIDTH, because the orbit is widest
  // mid-turn: measured on a render, the assembly (both visible faces + the rim glow) spans ~1.25x the face,
  // so a width-blind size would swing into the action-safe border. 0.68*W leaves ~80px each side at 1080.
  const zoneTop = CONTENT_TOP, zoneBot = contentBottom(W, H);
  const zoneH = Math.max(1, zoneBot - zoneTop);
  const wf = W / H < 1.4 ? 0.68 : 0.344;
  const SIZE = Math.round(Math.min(zoneH * 0.875, W * wf));
  // The -10deg tilt drops the FRONT face and exposes the back face's top edge, so the assembly is NOT
  // symmetric about the cube's centre. Bias it up ~5% of the face so it sits evenly inside the content zone
  // instead of leaning into the burned-caption band.
  const cy = zoneTop + zoneH / 2 - SIZE * 0.05;
  const pad = Math.round(SIZE * 0.109);
  const inner = SIZE - pad * 2;
  const chipH = Math.round(SIZE * 0.145);

  const sides = (FACES ?? []).map((s) => String(s ?? '')).filter((s) => s.length > 0).slice(0, 4);
  const n = Math.max(1, sides.length);
  const key = sides.join('');
  const faceData = sides.map((label, i) => {
    const parts = label.split(FACE_SPLIT);
    return {big: parts.length > 1 ? parts[0] : String(i + 1),
      small: parts.length > 1 ? parts.slice(1).join(' - ') : label};
  });

  // A LOOP closes when a later face REPEATS an earlier statement ("回到起点 - <the first face's line>"). Give
  // that face the tone of the face it returns to, so the colour states the closure instead of spending a
  // fourth category on content that only has three. Distinct statements keep their own tone, as before.
  const toneIdx: number[] = [];
  const firstSeen = new Map<string, number>();
  faceData.forEach((f, i) => {
    const prev = f.small ? firstSeen.get(f.small) : undefined;
    if (prev === undefined) {
      if (f.small) firstSeen.set(f.small, i);
      toneIdx.push(i);
    } else {
      toneIdx.push(toneIdx[prev]);
    }
  });

  // TYPE IS WIDTH-FITTED, not hardcoded. The register was tuned on 4-letter English words ("Plan"/"Ship");
  // real copy is a 7-9 character Chinese clause, which a fixed 52px runs to the face edge. ONE size for every
  // face (the min) so several PEER statements read as peers instead of as a hierarchy.
  const chipCap = Math.round(SIZE * 0.0667);
  const chipSize = React.useMemo(() => {
    const s = faceData.map((f) => fitTextOnNLines({
      text: f.big, maxLines: 1, maxBoxWidth: Math.max(40, inner * 0.86), fontFamily: dispFace,
      fontWeight: 800, maxFontSize: chipCap,
    }).fontSize);
    return s.length ? Math.min(...s) : chipCap;
  }, [key, inner, dispFace, chipCap]);
  const labelCap = Math.round(SIZE * 0.097);
  const labelSize = React.useMemo(() => {
    const s = faceData.map((f) => fitTextOnNLines({
      text: f.small, maxLines: 2, maxBoxWidth: inner, fontFamily: dispFace, fontWeight: 800, maxFontSize: labelCap,
    }).fontSize);
    return s.length ? Math.min(...s) : labelCap;
  }, [key, inner, dispFace, labelCap]);
  // The title is letter-spaced, which fitTextOnNLines does not measure - fit inside 72% of the frame so the
  // tracking still lands well clear of the action-safe border at every aspect.
  const titleCap = Math.round(Math.min(W, H) * 0.0278);
  const titleSize = React.useMemo(() => fitTextOnNLines({
    text: String(TITLE ?? ''), maxLines: 1, maxBoxWidth: W * 0.72, fontFamily: monoFace,
    fontWeight: 700, maxFontSize: titleCap,
  }).fontSize, [TITLE, W, monoFace, titleCap]);

  // present each face in its own time-slot: rotate IN during the first 45%, HOLD the rest.
  const p = clamp01(t) * n;                        // 0..n
  const k = Math.min(n - 1, Math.floor(p));        // face being presented
  const arrive = easeInOutCubic(clamp01((p - k) / 0.45));
  const angle = lerp(-(k - 1) * 90, -k * 90, arrive); // from previous face to this one, then hold
  const titleIn = easeOutCubic(seg(t, 0.03, 0.16));
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? GRAD_D0, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: TITLE_Y, left: 0, right: 0, textAlign: 'center', opacity: titleIn,
        color: DIM, font: `700 ${titleSize}px/1.1 ${monoFace}`, letterSpacing: dna?.labelSpacing ?? '0.3em',
        textTransform: dna && !dna.uppercaseLabels ? 'none' : 'uppercase'}}>{TITLE}</div>

      <div style={{position: 'absolute', left: 0, right: 0, top: cy - SIZE / 2, height: SIZE,
        display: 'flex', alignItems: 'center', justifyContent: 'center', perspective: Math.round(SIZE * 3.18)}}>
        <div style={{width: SIZE, height: SIZE, position: 'relative', transformStyle: 'preserve-3d',
          transform: `translateZ(${-SIZE / 2}px) rotateX(-10deg) rotateY(${angle}deg)`}}>
          {faceData.map((f, i) => {
            const tone = TONES[toneIdx[i] % TONES.length];
            const active = i === k && arrive > 0.6;
            // The chip is a LIGHT-to-DARK step of its own tone: one hue, so it cannot leave the palette.
            const chipA = tint(tone, 0.16), chipB = shade(tone, 0.28);
            // The un-themed original set this face's headline to pure '#fff'; keep that exact literal as the
            // no-DNA fallback so an unthemed film still renders identically (null-DNA guarantee).
            const chipInk = lum(mix(chipA, chipB, 0.5)) > 0.5 ? (dna?.onAccent ?? ONDARK_D0) : (dna?.fg ?? '#ffffff');
            return (
              <div key={i} style={{position: 'absolute', width: SIZE, height: SIZE, boxSizing: 'border-box', padding: pad,
                transform: `rotateY(${i * 90}deg) translateZ(${SIZE / 2}px)`,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
                background: FACE_BG,
                border: `${BORDER}px solid ${active ? tone : EDGE}`, borderRadius: RADIUS,
                boxShadow: active
                  ? `inset 0 0 ${Math.round(SIZE * 0.242)}px ${tone}22, 0 0 ${Math.round(SIZE * 0.09)}px ${tone}44`
                  : `inset 0 0 ${Math.round(SIZE * 0.182)}px #0006`}}>
                <div style={{minWidth: chipH, height: chipH, borderRadius: RADIUS,
                  marginBottom: Math.round(SIZE * 0.045), padding: `0 ${Math.round(SIZE * 0.03)}px`,
                  background: `linear-gradient(150deg, ${chipA}, ${chipB})`,
                  boxShadow: `0 0 ${Math.round(SIZE * 0.06)}px ${tone}66`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: chipInk, font: `800 ${chipSize}px/1 ${dispFace}`, whiteSpace: 'nowrap'}}>{f.big}</div>
                <div style={{color: INK, font: `800 ${labelSize}px/1.18 ${dispFace}`,
                  letterSpacing: '-0.02em', maxWidth: inner}}>{f.small}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* floor contact wash - achromatic (a shadow is physically correct under any DNA), fraction height */}
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: Math.round(H * 0.222),
        background: 'linear-gradient(#0000, #000000aa)'}} />
    </AbsoluteFill>
  );
};
export default CubeRotate;
