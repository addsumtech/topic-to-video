// Element primitives: pre-composed content blocks placed in scene-space.
// Each element renders at an absolute (x, y, z) position in the stage.

import React from 'react';
import {Img, staticFile} from 'remotion';
import type {Theme} from '../Video';
import {textStyle} from '../theme/typography';

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
  // TextBlock fields
  text?: string;
  level?: 'display' | 'body' | 'caption';
  // Callout fields
  label?: string;
  // Grid/floor fields (no extra config, size/opacity derived from kind)
  // Hero fields
  heroText?: string;
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

  return (
    <div style={containerStyle}>
      <ElementContent element={element} theme={theme} frame={frame} reducedMotion={reducedMotion} />
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
    return (
      <Img
        src={staticFile(element.src)}
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 1920,
          height: 1080,
          transform: 'translate(-50%, -50%)',
          objectFit: element.fit || 'cover',
          boxShadow: '0 60px 160px rgba(0,0,0,0.6)',
        }}
      />
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
        {element.text || ''}
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
          {element.kicker}
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
          {element.title}
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
          {element.sub}
        </div>
      ) : null}
    </div>
  );
};
