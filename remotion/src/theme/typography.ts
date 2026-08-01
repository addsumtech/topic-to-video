import type {CSSProperties} from 'react';
import {fitText, measureText} from '@remotion/layout-utils';
import type {Theme} from './tokens';

// Type scale aligned with theme.py's _TYPE_SCALE: [display, body, caption, small]
export const TYPE_SCALE = {
  display: 110, // headlines, titles
  body: 56, // default content
  caption: 44, // annotations, labels
  small: 32, // fine print
};

export type TypeLevel = keyof typeof TYPE_SCALE;

// Get font family for a typography role
export function getFontFamily(theme: Theme, role: 'display' | 'body' | 'number'): string {
  if (role === 'display') return theme.fontDisplay;
  if (role === 'number') return theme.fontNumber;
  return theme.fontBody;
}

// Fit text to a width at a given type level (returns fontSize to use)
export function fitTextToWidth(
  text: string,
  withinWidth: number,
  theme: Theme,
  role: 'display' | 'body' | 'number' = 'body',
): number {
  const fontFamily = getFontFamily(theme, role);
  const baseSize = TYPE_SCALE.body;
  const letterSpacing = `${parseFloat(theme.trackScale) * 0.01}em`;

  const {fontSize} = fitText({
    text,
    withinWidth,
    fontFamily,
    letterSpacing,
    fontVariantNumeric: role === 'number' ? 'lining-nums tabular-nums' : 'lining-nums',
    validateFontIsLoaded: true,
  });

  return fontSize;
}

// Measure text dimensions at a given size
export function getTextDimensions(
  text: string,
  fontSize: number,
  theme: Theme,
  role: 'display' | 'body' | 'number' = 'body',
): {width: number; height: number} {
  const fontFamily = getFontFamily(theme, role);
  const letterSpacing = `${parseFloat(theme.trackScale) * 0.01}em`;

  return measureText({
    text,
    fontFamily,
    fontSize,
    letterSpacing,
    fontVariantNumeric: role === 'number' ? 'lining-nums tabular-nums' : 'lining-nums',
    validateFontIsLoaded: true,
  });
}

// Common text style object for React components
export function textStyle(
  theme: Theme,
  level: TypeLevel,
  role: 'display' | 'body' | 'number' = 'body',
): CSSProperties {
  const fontFamily = getFontFamily(theme, role);
  const fontSize = TYPE_SCALE[level];
  const lineHeight = level === 'display' ? parseFloat(theme.lhDisplay) : 1.4;
  const letterSpacing = `${parseFloat(theme.trackScale) * 0.01}em`;

  return {
    fontFamily,
    fontSize,
    lineHeight,
    letterSpacing,
    // LINING FIGURES ALWAYS (standing rule): force lining numerals on EVERY role so digits never render
    // in an old-style/text-figure face (e.g. Georgia/Playfair defaults, where '4' drops below the baseline).
    // Tabular alignment only where numbers are the point (role 'number'); proportional lining reads more
    // naturally in headlines/body. This is the enforcement the HTML tier does in CSS — the cinematic tier
    // never passed role 'number', so without this every stat rendered old-style.
    fontVariantNumeric: role === 'number' ? 'lining-nums tabular-nums' : 'lining-nums',
  };
}
