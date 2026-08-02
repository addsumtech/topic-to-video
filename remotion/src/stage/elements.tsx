// Element primitives: pre-composed content blocks placed in scene-space.
// Each element renders at an absolute (x, y, z) position in the stage.

import React from 'react';
import {Img, staticFile} from 'remotion';
import type {Theme} from '../Video';
import {textStyle} from '../theme/typography';
import {KineticText} from '../theme/KineticText';

export type ElementKind = 'panel' | 'image' | 'textblock' | 'callout' | 'grid' | 'floor' | 'hero' | 'fill' | 'metaphor' | 'display';
export type TypeAttitude = 'rise' | 'tracking-in' | 'blur-in'; // the entrance personality of a display statement

// MATERIALIZED METAPHOR (the highest-yield topic-locked novelty): a beat's MEANING encoded as a visual
// PROPERTY that only THIS subject would use, summarizable by one VERB. Each concept is a frame-driven
// primitive (pure fn of useCurrentFrame — no CSS transition/keyframes/RAF, which freeze off-thread).
export type MetaphorConcept = 'widening-gap' | 'physical-fall' | 'filling-vessel' | 'diverging-pair' | 'converging-scatter';

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);      // decel: a fill / a settle
const easeGravity = (t: number) => t * t;                   // accel: a fall speeds up
// deterministic pseudo-scatter in [0,1) — a frame-STABLE hash, never a per-frame RNG (which would re-roll
// every frame and strobe the dots).
const hash1 = (i: number, salt: number) => {
  const s = Math.sin((i + 1) * 12.9898 + salt * 78.233) * 43758.5453;
  return s - Math.floor(s);
};
// counts a number 0->target over [fire, fire+span], eased; lining figures (grouped) — never old-style.
function counted(frame: number, fire: number, span: number, target: number, unit: string, reduced: boolean) {
  const u = reduced ? 1 : clamp01((frame - fire) / span);
  const v = target * easeOut(u);
  const body = Math.abs(v) >= 100 ? Math.round(v).toLocaleString('en-US')
    : (Math.abs(v - Math.round(v)) < 0.05 ? String(Math.round(v)) : v.toFixed(1));
  return body + (unit || '');
}

// Element data schema (from storyboard.json stage.elements[])
export type ElementData = {
  id: string;
  kind: ElementKind;
  position: [number, number, number]; // [x, y, z] in stage units
  // Panel fields
  title?: string;
  kicker?: string;
  sub?: string;
  align?: 'left' | 'center';
  // Image fields
  src?: string; // relative path (staticFile)
  fit?: 'cover' | 'contain';
  size?: [number, number]; // [w,h] px in stage space (default 1600x1000); frames a screenshot properly
  frame?: 'none' | 'browser' | 'window'; // device/browser chrome around the image (product-UI framing)
  frameLabel?: string; // the browser chrome's address/title text
  // TextBlock fields
  text?: string;
  level?: 'display' | 'body' | 'caption';
  // Callout fields
  label?: string;
  // Grid/floor fields (no extra config, size/opacity derived from kind)
  // Hero fields
  heroText?: string;
  // Materialized-metaphor fields (kind:'metaphor'): the verb + its data + timing.
  concept?: MetaphorConcept;
  values?: number[]; // the numbers the verb encodes (arity depends on concept)
  valueLabels?: string[]; // optional labels for the values
  unit?: string; // appended to the counted number (e.g. '%')
  attitude?: TypeAttitude; // display statement entrance (rise | tracking-in | blur-in)
  atFrame?: number; // scene-local frame the VERB fires (default enter+10)
  verbSpan?: number; // frames the verb takes (default 30)
  accentIndex?: number;
  // Kinetic typography: the scene-local frame at which this element's text reveals in (default 0).
  enterAtFrame?: number;
};

// Render an element at its stage position (inside a positioned div with translateZ).
// The parent SceneStage handles the perspective rig and camera; this just renders content.
export const Element: React.FC<{
  element: ElementData;
  theme: Theme;
  frame: number;
  reducedMotion: boolean;
  blur?: number; // rack-focus DoF (px) — applied on the INNER leaf, never above the depth node
}> = ({element, theme, frame, reducedMotion, blur = 0}) => {
  const {kind, position} = element;
  const [x, y, z] = position;

  // Element container: ONE node, the DIRECT child of the preserve-3d `world`. It carries preserve-3d AND
  // the translate3d depth (plus the floor's rotateX so the floor lays down IN the 3D space). CRITICAL:
  // never put a filter/opacity/flat node ABOVE this container — a flat ancestor collapses every descendant
  // translateZ to one plane, which silently kills all per-element depth (parallax/size-by-distance/dolly-
  // past). That was the bug; enter-opacity + DoF blur now live on an inner LEAF instead (below).
  const isFloor = kind === 'floor';
  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    transformStyle: 'preserve-3d',
    transform: `translate3d(${x}px, ${y}px, ${z}px)${isFloor ? ' rotateX(90deg)' : ''}`,
  };

  // ENTER FADE (P4): a CONTENT element materialises as the camera arrives on it (its enterAtFrame, auto-
  // derived from the shot that frames it) — NOT from frame 0. Pure backgrounds (grid/floor/fill) are the
  // world and stay constant. Opacity + rack-focus blur sit on this INNER leaf (flat is fine here — the
  // content has no translateZ of its own), so they never flatten the depth node above.
  const isBackground = kind === 'grid' || kind === 'floor' || kind === 'fill';
  const enter = element.enterAtFrame ?? 0;
  const op = isBackground || reducedMotion ? 1 : Math.max(0, Math.min(1, (frame - enter) / 8));

  return (
    <div style={containerStyle}>
      <div style={{opacity: op, filter: blur > 0 ? `blur(${blur}px)` : undefined}}>
        <ElementContent element={element} theme={theme} frame={frame} reducedMotion={reducedMotion} />
      </div>
    </div>
  );
};

// Render the element's visual content (matches Camera.tsx PlaneContent kinds where applicable)
const ElementContent: React.FC<{
  element: ElementData;
  theme: Theme;
  frame: number;
  reducedMotion: boolean;
}> = ({element, theme, frame, reducedMotion}) => {
  const {kind} = element;
  const enter = element.enterAtFrame ?? 0; // scene-local frame this element's text reveals in

  if (kind === 'fill') {
    // Radial gradient background fill (large, centered on origin)
    return (
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 3200,
          height: 2200,
          transform: 'translate(-50%, -50%)',
          background: `radial-gradient(120% 120% at 50% 40%, ${theme.bg} 0%, ${theme.bg} 55%, #00000055 100%)`,
        }}
      />
    );
  }

  if (kind === 'grid' || kind === 'floor') {
    const strong = kind === 'floor';
    const gridStyle: React.CSSProperties = {
      position: 'absolute',
      left: strong ? -1400 : -900,
      top: strong ? -1400 : -600,
      width: strong ? 4600 : 3720,
      height: strong ? 4600 : 2280,
      opacity: strong ? 0.5 : 0.14,
      backgroundImage: `linear-gradient(${strong ? theme.accent + '55' : theme.muted} ${strong ? 2 : 1}px, transparent ${strong ? 2 : 1}px), linear-gradient(90deg, ${strong ? theme.accent + '55' : theme.muted} ${strong ? 2 : 1}px, transparent ${strong ? 2 : 1}px)`,
      backgroundSize: strong ? '170px 170px' : '120px 120px',
    };
    // NOTE: the floor's rotateX(90deg) is applied on the element CONTAINER (Element above), not here —
    // it must live on the preserve-3d depth node so the floor lays down in the 3D world, not on this flat leaf.
    return <div style={gridStyle} />;
  }

  if (kind === 'hero') {
    const heroStyle = textStyle(theme, 'display', 'body');
    return (
      <div
        style={{
          ...heroStyle,
          position: 'absolute',
          left: -760,
          top: -280,
          width: 1520,
          textAlign: 'center',
          color: theme.fg,
          opacity: 0.09,
          fontSize: 420,
          fontWeight: 800,
          letterSpacing: -6,
        }}
      >
        {element.heroText || element.text || ''}
      </div>
    );
  }

  if (kind === 'image' && element.src) {
    // Sized (not full-frame) so a screenshot frames properly; optional browser/device chrome (product UI).
    const [iw, ih] = element.size && element.size.length === 2 ? element.size : [1600, 1000];
    const radius = parseInt(theme.radius || '14px', 10);
    const img = (
      <Img src={staticFile(element.src)}
           style={{display: 'block', width: iw, height: ih, objectFit: element.fit || 'cover'}} />
    );
    if (element.frame === 'browser' || element.frame === 'window') {
      const bar = 56;
      const isBrowser = element.frame === 'browser';
      return (
        <div style={{position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)',
                     width: iw, borderRadius: radius, overflow: 'hidden',
                     border: `1px solid ${theme.fg}1f`, background: theme.surface || theme.bg,
                     boxShadow: '0 60px 160px rgba(0,0,0,0.6)'}}>
          {/* chrome: traffic-light dots + EITHER a browser address bar OR a native-window centered title */}
          <div style={{height: bar, display: 'flex', alignItems: 'center', gap: 10, padding: '0 22px',
                       position: 'relative', background: theme.bg, borderBottom: `1px solid ${theme.fg}14`}}>
            {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
              <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c}} />
            ))}
            {isBrowser && element.frameLabel ? (
              // browser: an address/URL pill
              <div style={{marginLeft: 18, flex: 1, height: 28, borderRadius: 8, background: `${theme.fg}0f`,
                           color: theme.muted, fontSize: 22, display: 'flex', alignItems: 'center',
                           padding: '0 16px', fontFamily: theme.fontBody}}>{element.frameLabel}</div>
            ) : null}
            {!isBrowser && element.frameLabel ? (
              // native app window: a CENTERED title, no URL pill (a URL on an app window mislabels it)
              <div style={{position: 'absolute', left: 0, right: 0, textAlign: 'center', color: theme.muted,
                           fontSize: 22, fontFamily: theme.fontBody, pointerEvents: 'none'}}>{element.frameLabel}</div>
            ) : null}
          </div>
          {img}
        </div>
      );
    }
    // bare sized image (a framed float, not a full-frame bitmap)
    return (
      <div style={{position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)',
                   width: iw, height: ih, borderRadius: radius, overflow: 'hidden',
                   boxShadow: '0 60px 160px rgba(0,0,0,0.6)'}}>
        {img}
      </div>
    );
  }

  if (kind === 'textblock') {
    const level = element.level || 'body';
    const style = textStyle(theme, level, 'body');
    return (
      <div
        style={{
          ...style,
          position: 'absolute',
          left: -400,
          top: -100,
          width: 800,
          color: theme.fg,
          textAlign: element.align || 'left',
        }}
      >
        <KineticText text={element.text || ''} frame={frame} startFrame={enter} split="line" reduced={reducedMotion} />
      </div>
    );
  }

  if (kind === 'callout') {
    const style = textStyle(theme, 'caption', 'body');
    return (
      <div
        style={{
          ...style,
          position: 'absolute',
          left: -120,
          top: -30,
          padding: '8px 16px',
          background: theme.accent,
          color: theme.onAccent,
          borderRadius: parseInt(theme.radius || '6px', 10),
          fontSize: 24,
          fontWeight: 700,
          whiteSpace: 'nowrap',
        }}
      >
        {element.label || ''}
      </div>
    );
  }

  // GIANT DISPLAY STATEMENT — full-strength kinetic type staged as an OBJECT the camera pushes into/through
  // (the native manifesto-monolith vehicle; not the 9%-opacity hero watermark). Entrance = `attitude`.
  if (kind === 'display') {
    const u = reducedMotion ? 1 : clamp01((frame - enter) / 18);
    const e = easeOut(u);
    const att = element.attitude || 'rise';
    const dstyle = textStyle(theme, 'display', 'display');
    const box: React.CSSProperties = {
      ...dstyle, position: 'absolute', left: -840, top: -180, width: 1680, textAlign: element.align || 'center',
      color: theme.fg, fontSize: 200, fontWeight: 800, lineHeight: 1.02, letterSpacing: -2,
      textShadow: '0 8px 44px rgba(0,0,0,0.55)',
    };
    const txt = element.text || element.heroText || '';
    if (att === 'rise') {
      return <div style={box}><KineticText text={txt} frame={frame} startFrame={enter} split="word" reduced={reducedMotion} /></div>;
    }
    if (att === 'tracking-in') {          // the word CONDENSES into place (wide tracking -> tight)
      return <div style={{...box, opacity: e, letterSpacing: (1 - e) * 44 - 2}}>{txt}</div>;
    }
    return <div style={{...box, opacity: e, filter: `blur(${(1 - e) * 22}px)`}}>{txt}</div>; // blur-in: rack into focus
  }

  // MATERIALIZED METAPHOR — the beat's meaning as a physical action (one VERB), driven purely by frame.
  if (kind === 'metaphor') {
    const fire = element.atFrame ?? (enter + 10), span = element.verbSpan ?? 30;
    const u = reducedMotion ? 1 : clamp01((frame - fire) / span);
    const acc = theme.accent, base = theme.muted, gapc = theme.accent2, numFont = theme.fontNumber;

    if (element.concept === 'filling-vessel') {
      // a container FILLS = adoption / progress / capacity.
      const raw = element.values?.[0] ?? 0;
      const pct = clamp01(raw > 1 ? raw / 100 : raw);
      const W = 360, H = 520, r = 28, fillH = easeOut(u) * pct * H;
      return (
        <div style={{position: 'absolute', left: -W / 2, top: -H / 2, width: W, height: H}}>
          <div style={{position: 'absolute', inset: 0, border: `3px solid ${base}`, borderRadius: r, overflow: 'hidden', background: `${theme.bg}66`}}>
            <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: fillH, background: `linear-gradient(180deg,${acc} 0%,${gapc} 100%)`}} />
            <div style={{position: 'absolute', left: 0, right: 0, bottom: fillH - 2, height: 4, background: `${theme.fg}cc`, opacity: fillH > 2 ? 1 : 0}} />
          </div>
          <div style={{position: 'absolute', left: 0, right: 0, top: '50%', transform: 'translateY(-50%)', textAlign: 'center', fontFamily: numFont, fontVariantNumeric: 'lining-nums tabular-nums', fontWeight: 800, fontSize: 120, color: theme.fg, textShadow: '0 4px 24px rgba(0,0,0,.5)'}}>{counted(frame, fire, span, pct * 100, element.unit ?? '%', reducedMotion)}</div>
          {element.label ? <div style={{position: 'absolute', left: 0, right: 0, top: H + 16, textAlign: 'center', fontFamily: theme.fontBody, letterSpacing: 4, textTransform: 'uppercase', color: base, fontSize: 26}}>{element.label}</div> : null}
        </div>
      );
    }

    if (element.concept === 'widening-gap') {
      // two tracks separate; the growing GAP is the loss / divergence.
      const a = element.values?.[0] ?? 0, b = element.values?.[1] ?? 0;
      const delta = Math.abs(b - a), denom = Math.max(1e-6, Math.abs(a), Math.abs(b));
      const W = 620, gapPx = easeOut(u) * (delta / denom) * 300, half = gapPx / 2, cy = 260, lw = 6;
      return (
        <div style={{position: 'absolute', left: -W / 2, top: -260, width: W, height: 520}}>
          <div style={{position: 'absolute', left: 0, width: W, height: lw, top: cy - half, background: acc, borderRadius: lw}} />
          <div style={{position: 'absolute', left: 0, width: W, height: lw, top: cy + half, background: base, borderRadius: lw}} />
          <div style={{position: 'absolute', left: W + 18, top: cy - half, width: 2, height: gapPx, background: gapc}} />
          <div style={{position: 'absolute', left: W + 34, top: cy, transform: 'translateY(-50%)', fontFamily: numFont, fontVariantNumeric: 'lining-nums tabular-nums', fontWeight: 800, fontSize: 88, color: gapc}}>{counted(frame, fire, span, delta, element.unit ?? '', reducedMotion)}</div>
          {element.valueLabels?.[1] ? <div style={{position: 'absolute', left: 0, top: cy - half - 40, fontFamily: theme.fontBody, color: acc, fontSize: 28}}>{element.valueLabels[1]}</div> : null}
          {element.valueLabels?.[0] ? <div style={{position: 'absolute', left: 0, top: cy + half + 12, fontFamily: theme.fontBody, color: base, fontSize: 28}}>{element.valueLabels[0]}</div> : null}
        </div>
      );
    }

    if (element.concept === 'physical-fall') {
      // a value FALLS off a shelf = the cliff (accelerating, not eased).
      const before = element.values?.[0] ?? 0, after = element.values?.[1] ?? 0;
      const dropPx = ((before - after) / Math.max(1e-6, Math.abs(before))) * 360;
      const g = reducedMotion ? 1 : easeGravity(clamp01((frame - fire) / span));
      const cy = 260, restY = -160, y = restY + g * Math.max(0, dropPx);
      const tokVal = Math.round(before + (after - before) * g);
      return (
        <div style={{position: 'absolute', left: -260, top: -260, width: 520, height: 560}}>
          <div style={{position: 'absolute', left: 60, top: cy + restY, width: 200, height: 0, borderTop: `2px dashed ${base}`, opacity: 0.6}} />
          <div style={{position: 'absolute', left: 0, top: cy, width: 240, height: 6, background: base, borderRadius: 3}} />
          <div style={{position: 'absolute', left: 70, top: cy + y, width: 180, height: 110, borderRadius: 16, background: acc, color: theme.onAccent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: numFont, fontVariantNumeric: 'lining-nums tabular-nums', fontWeight: 800, fontSize: 64, boxShadow: '0 30px 60px rgba(0,0,0,.5)'}}>{String(tokVal) + (element.unit ?? '')}</div>
          <div style={{position: 'absolute', left: 300, top: cy + restY, width: 2, height: Math.max(0, dropPx), background: gapc}} />
          <div style={{position: 'absolute', left: 316, top: cy + restY + dropPx / 2, transform: 'translateY(-50%)', fontFamily: numFont, fontVariantNumeric: 'lining-nums tabular-nums', fontWeight: 800, fontSize: 72, color: gapc}}>{'-' + counted(frame, fire, span, before - after, element.unit ?? '', reducedMotion)}</div>
        </div>
      );
    }

    if (element.concept === 'diverging-pair') {
      // two paths SPLIT from one origin — the divergence is the choice / the two outcomes. Drawn on via
      // strokeDashoffset with an ANALYTICAL Math.hypot length (a DOM path measure is 0/unstable off-thread).
      const a = element.values?.[0] ?? 0, b = element.values?.[1] ?? 0;
      const W = 640, H = 440, x1 = 44, y0 = H / 2, x2 = W - 44;
      const denom = Math.max(1e-6, Math.abs(a), Math.abs(b));
      const upY = y0 - (Math.abs(b) / denom) * (H / 2 - 34);
      const dnY = y0 + (Math.abs(a) / denom) * (H / 2 - 34);
      const lenU = Math.hypot(x2 - x1, upY - y0), lenD = Math.hypot(x2 - x1, dnY - y0);
      const e = easeOut(u);
      return (
        <div style={{position: 'absolute', left: -W / 2, top: -H / 2, width: W, height: H}}>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
            <line x1={x1} y1={y0} x2={x2} y2={upY} stroke={acc} strokeWidth={6} strokeLinecap="round" strokeDasharray={lenU} strokeDashoffset={(1 - e) * lenU} />
            <line x1={x1} y1={y0} x2={x2} y2={dnY} stroke={base} strokeWidth={6} strokeLinecap="round" strokeDasharray={lenD} strokeDashoffset={(1 - e) * lenD} />
            <circle cx={x1} cy={y0} r={10} fill={theme.fg} />
            {e > 0.98 ? <circle cx={x2} cy={upY} r={9} fill={acc} /> : null}
            {e > 0.98 ? <circle cx={x2} cy={dnY} r={9} fill={base} /> : null}
          </svg>
          {element.valueLabels?.[1] ? <div style={{position: 'absolute', left: x2 - 30, top: upY - 48, fontFamily: theme.fontBody, color: acc, fontSize: 26}}>{element.valueLabels[1]}</div> : null}
          {element.valueLabels?.[0] ? <div style={{position: 'absolute', left: x2 - 30, top: dnY + 18, fontFamily: theme.fontBody, color: base, fontSize: 26}}>{element.valueLabels[0]}</div> : null}
        </div>
      );
    }

    if (element.concept === 'converging-scatter') {
      // scattered points CONVERGE to one node = consolidation. Starts are deterministic (hash1), never RNG.
      const total = element.values?.[0] ?? 0;
      const N = 22, R = 250;
      const nodeOp = clamp01((u - 0.62) / 0.38);
      return (
        <div style={{position: 'absolute', left: -300, top: -300, width: 600, height: 600}}>
          {Array.from({length: N}).map((_, i) => {
            const sx = (hash1(i, 1) - 0.5) * R * 2, sy = (hash1(i, 2) - 0.5) * R * 2;
            const e = easeOut(clamp01(u * 1.15 - i * 0.014));
            return <div key={i} style={{position: 'absolute', left: 300 + sx * (1 - e) - 7, top: 300 + sy * (1 - e) - 7, width: 14, height: 14, borderRadius: 7, background: i % 3 === 0 ? gapc : acc, opacity: 0.85}} />;
          })}
          <div style={{position: 'absolute', left: 0, right: 0, top: '50%', transform: 'translateY(-50%)', textAlign: 'center', fontFamily: numFont, fontVariantNumeric: 'lining-nums tabular-nums', fontWeight: 800, fontSize: 110, color: theme.fg, opacity: nodeOp, textShadow: '0 4px 24px rgba(0,0,0,.6)'}}>{counted(frame, fire, span, total, element.unit ?? '', reducedMotion)}</div>
          {element.label ? <div style={{position: 'absolute', left: 0, right: 0, top: 452, textAlign: 'center', fontFamily: theme.fontBody, letterSpacing: 4, textTransform: 'uppercase', color: base, fontSize: 26, opacity: nodeOp}}>{element.label}</div> : null}
        </div>
      );
    }
    return null; // unknown concept — coercion/validate already guard this
  }

  // Panel: floating glass card (ported from Camera.tsx PlaneContent)
  const centre = element.align === 'center';
  const kickerStyle = textStyle(theme, 'caption', 'body');
  const titleStyle = textStyle(theme, 'display', 'display');
  const subStyle = textStyle(theme, 'body', 'body');
  const radius = parseInt(theme.radius || '14px', 10);

  return (
    <div
      style={{
        position: 'absolute',
        left: -520,
        top: -200,
        width: 1040,
        padding: '44px 52px',
        boxSizing: 'border-box',
        textAlign: centre ? 'center' : 'left',
        background: `linear-gradient(158deg, ${theme.bg}f2 0%, ${theme.bg}cc 100%)`,
        border: `1.5px solid ${theme.accent}40`,
        borderRadius: radius,
        boxShadow: `0 54px 150px rgba(0,0,0,0.62), inset 0 1.5px 0 ${theme.fg}26, inset 0 0 100px ${theme.accent}0e`,
      }}
    >
      {element.kicker ? (
        <div
          style={{
            ...kickerStyle,
            color: theme.accent2,
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: 4,
            textTransform: 'uppercase',
            marginBottom: 20,
          }}
        >
          <KineticText text={element.kicker} frame={frame} startFrame={enter} split="none" reduced={reducedMotion} />
        </div>
      ) : null}
      {element.title ? (
        <div
          style={{
            ...titleStyle,
            color: theme.fg,
            fontSize: 80,
            fontWeight: 800,
            lineHeight: 1.08,
            letterSpacing: -1,
            textShadow: '0 6px 30px rgba(0,0,0,0.45)',
          }}
        >
          {/* title reveals word-by-word after the kicker */}
          <KineticText text={element.title} frame={frame} startFrame={enter + 4} split="word" reduced={reducedMotion} />
        </div>
      ) : null}
      {element.sub ? (
        <div
          style={{
            ...subStyle,
            color: theme.muted,
            fontSize: 34,
            lineHeight: 1.34,
            marginTop: 22,
          }}
        >
          {/* sub follows the title */}
          <KineticText text={element.sub} frame={frame} startFrame={enter + 12} split="word" staggerFrames={2} reduced={reducedMotion} />
        </div>
      ) : null}
    </div>
  );
};
