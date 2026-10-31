// THE STYLE SPEC — a drawing style as values on fixed, general axes (meta.style → Film's `style` prop).
//
// The axes are one table, ./styleAxes.json, which scripts/style_spec.py validates against and style_qa measures
// against: parity by construction, not by a test that two copies agree. A null spec means the film draws exactly
// as its registers do — nothing in the style engine mounts (runtime/style.tsx).
import {createContext, useContext} from 'react';
import axes from './styleAxes.json';

type Param = {kind: string; default: unknown};
type Value = string | number | boolean;

export type StyleSpec = {
  name: string;
  refs: {src: string; from: 'user' | 'found'; credit?: string}[];
  refs_missing?: string;
  notes?: string;
  shortfalls?: {axis: string; wanted: string; got: string; why: string}[];
} & {[group: string]: unknown};

/** Every axis group with every parameter filled — what the engine draws from. `texture` is not part of the spec:
 *  it is the GENERATED medium's tiles the render resolved (render_remotion.style_texture_props), served URLs. */
export type ResolvedStyle = StyleSpec & Record<string, Record<string, Value>> & {texture?: {light: string; dark: string}};

const TABLE = Object.fromEntries(Object.entries(axes).filter(([k]) => !k.startsWith('_'))) as
  Record<string, Record<string, Param>>;

export const AXIS_DEFAULTS: Record<string, Record<string, Value>> = Object.fromEntries(
  Object.entries(TABLE).map(([g, ps]) => [g, Object.fromEntries(Object.entries(ps).map(([n, p]) => [n, p.default as Value]))]));

export const resolveStyle = (spec: StyleSpec, texture?: {light: string; dark: string} | null): ResolvedStyle => {
  const out: Record<string, unknown> = {...spec};
  for (const [g, defs] of Object.entries(AXIS_DEFAULTS)) {
    const own = spec[g];
    out[g] = {...defs, ...(own && typeof own === 'object' ? own as Record<string, Value> : {})};
  }
  if (texture) out.texture = texture;
  return out as ResolvedStyle;
};

export const StyleContext = createContext<ResolvedStyle | null>(null);
export const useStyle = (): ResolvedStyle | null => useContext(StyleContext);
