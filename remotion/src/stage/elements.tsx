// Element primitives: pre-composed content blocks placed in scene-space.
// Each element renders at an absolute (x, y, z) position in the stage.

import React from 'react';
import {Img, staticFile} from 'remotion';
import type {Theme} from '../Video';
import {textStyle} from '../theme/typography';
import {KineticText} from '../theme/KineticText';

export type ElementKind = 'panel' | 'image' | 'textblock' | 'callout' | 'grid' | 'floor' | 'hero' | 'fill';

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
}> = ({element, theme, frame, reducedMotion}) => {
  const {kind, position} = element;
  const [x, y, z] = position;

  // Element container: absolute position in 3D space
  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    transformStyle: 'preserve-3d',
    transform: `translate3d(${x}px, ${y}px, ${z}px)`,
  };

  // ENTER FADE (P4 fix): a CONTENT element materialises as the camera arrives on it (its enterAtFrame,
  // auto-derived from the shot that frames it) — NOT from frame 0. Without this an empty glass card floats
  // in space before its text reveals (mystery furniture). Pure backgrounds (grid/floor/fill) are the world
  // and stay constant. Opacity is on an INNER wrapper so it never flattens the element's place in the 3D rig.
  const isBackground = kind === 'grid' || kind === 'floor' || kind === 'fill';
  const enter = element.enterAtFrame ?? 0;
  const op = isBackground || reducedMotion ? 1 : Math.max(0, Math.min(1, (frame - enter) / 8));

  return (
    <div style={containerStyle}>
      <div style={{opacity: op}}>
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
    if (kind === 'floor') {
      gridStyle.transform = 'rotateX(90deg)';
    }
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
      return (
        <div style={{position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)',
                     width: iw, borderRadius: radius, overflow: 'hidden',
                     border: `1px solid ${theme.fg}1f`, background: theme.surface || theme.bg,
                     boxShadow: '0 60px 160px rgba(0,0,0,0.6)'}}>
          {/* browser/window chrome: traffic-light dots + an address/title */}
          <div style={{height: bar, display: 'flex', alignItems: 'center', gap: 10, padding: '0 22px',
                       background: theme.bg, borderBottom: `1px solid ${theme.fg}14`}}>
            {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
              <div key={c} style={{width: 14, height: 14, borderRadius: 7, background: c}} />
            ))}
            {element.frameLabel ? (
              <div style={{marginLeft: 18, flex: 1, height: 28, borderRadius: 8, background: `${theme.fg}0f`,
                           color: theme.muted, fontSize: 22, display: 'flex', alignItems: 'center',
                           padding: '0 16px', fontFamily: theme.fontBody}}>{element.frameLabel}</div>
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
