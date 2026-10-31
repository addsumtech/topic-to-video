// STYLE HOOKS — axes a register draws ITSELF, so the engine (runtime/style.tsx) leaves them alone on its beat.
//
// A register that can draw an axis better than a rewrite of its DOM can (its own boiling line, its own cel shading)
// exports `STYLE_HOOKS = ['line.wobble', ...]` and reads the spec with `useStyle()`. This map is how Film finds them;
// tests/test_style_coverage.py fails when a register declares hooks and is missing here. None does yet.
import type {ResolvedStyle} from './styleSpec';
import {AXIS_DEFAULTS} from './styleSpec';

export const STYLE_HOOKS_BY_SHOT: Record<string, string[] | undefined> = {};

/** `spec` with the named axes (a group, `fill`, or one parameter, `line.wobble`) put back to their defaults. */
export const withoutAxes = (spec: ResolvedStyle, skip: string[] | undefined): ResolvedStyle => {
  if (!skip || !skip.length) return spec;
  const out: Record<string, unknown> = {...spec};
  for (const a of skip) {
    const [g, p] = a.split('.');
    if (!AXIS_DEFAULTS[g]) continue;
    out[g] = p ? {...(out[g] as object), [p]: AXIS_DEFAULTS[g][p]} : {...AXIS_DEFAULTS[g]};
  }
  return out as ResolvedStyle;
};
