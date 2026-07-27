// Extended design tokens matching theme.py emission (colors, typography, style, radius, grain).
export type Theme = {
  bg: string;
  surface: string;
  fg: string;
  muted: string;
  accent: string;
  accent2: string;
  scrim: string;
  onAccent: string;
  onAccent2: string;
  fontDisplay: string; // CSS font stack
  fontBody: string;
  fontNumber: string;
  fontKind: 'sans' | 'serif'; // derived from font family
  style: string; // 'editorial' | 'technical' | 'minimal' | ''
  radius: string; // e.g. '6px'
  grainAmount: string; // 0–1 float as string
  trackScale: string; // letter-spacing multiplier
  lhDisplay: string; // line-height for display text
};

// Type guard for style mood
export function isStyled(theme: Theme): theme is Theme & {style: 'editorial' | 'technical' | 'minimal'} {
  return theme.style !== '';
}
