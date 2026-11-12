// THE ID SCOPE — every beat's SVG ids are its own.
//
// An SVG id is global to the document, and `url(#x)` / `href="#x"` resolve to the FIRST element in it with that id. A
// register written with a literal id (48 files in this library do: `url(#og)`, `url(#neon)`, `url(#arrow)`…) is fine
// alone and wrong the moment two beats are mounted at once — every seam. Measured on WorkBuddy (2026-11-11): beats 9
// and 10 both draw the lit workspace, whose light pool is `url(#ws-pool)` fading in over the beat. Through the
// 12-frame seam beat 10's pool resolved to beat 9's (fully lit), and when beat 9 unmounted it fell back to its own (not
// yet lit): the light switched off in one frame, six frames after the cut. No gate measured it; the eye did.
//
// So each beat's subtree is scoped: on every frame, after React has written the DOM and before any layout effect of
// the beat reads it (an earlier sibling's layout effect runs first, and the commit's DOM is complete by then), every
// `id` under the scope gets the scope's suffix and every reference to one of those ids — paint and effect attributes,
// `href`, inline `style` — is rewritten to match. A reference to an id the beat does not define is left alone (a
// document-level def, fonts.ts's `lining-figures`). Copies of the register inside the same beat (coverage's echo and
// probes, the safe-frame echo) share the scope; they draw the same register, and the first of them in the document is
// the one on the live frame or a copy of it.
import React, {useLayoutEffect, useRef} from 'react';

const REF_ATTRS = ['fill', 'stroke', 'filter', 'mask', 'clip-path', 'marker-start', 'marker-mid', 'marker-end', 'style'];
const URL_RE = /url\(\s*(['"]?)#([^'")\s]+)\1\s*\)/g;

/** Scope every id under `root` with `suffix` and rewrite the references to them. Idempotent; returns the ids scoped. */
export const scopeIds = (root: Element, suffix: string): number => {
  const tag = `__${suffix}`;
  const ids = new Set<string>();
  root.querySelectorAll('[id]').forEach((el) => {
    const id = el.getAttribute('id') || '';
    if (!id) return;
    const base = id.endsWith(tag) ? id.slice(0, -tag.length) : id;
    ids.add(base);
    if (base === id) el.setAttribute('id', base + tag);
  });
  if (!ids.size) return 0;
  const scoped = (id: string) => (ids.has(id) ? id + tag : id);
  root.querySelectorAll('*').forEach((el) => {
    for (const a of REF_ATTRS) {
      const v = el.getAttribute(a);
      if (!v || v.indexOf('url(') < 0) continue;
      const w = v.replace(URL_RE, (m, q: string, id: string) => (ids.has(id) ? `url(${q}#${id + tag}${q})` : m));
      if (w !== v) el.setAttribute(a, w);
    }
    for (const a of ['href', 'xlink:href']) {
      const v = el.getAttribute(a);
      if (v && v[0] === '#' && ids.has(v.slice(1))) el.setAttribute(a, '#' + scoped(v.slice(1)));
    }
  });
  return ids.size;
};

const Runner: React.FC<{suffix: string}> = ({suffix}) => {
  const mark = useRef<HTMLSpanElement>(null);
  // no deps: React re-writes an attribute whose prop changed (a fill that animates, a style that moves), so the scope
  // is re-applied on every commit
  useLayoutEffect(() => {
    const root = mark.current?.parentElement;
    if (root) scopeIds(root, suffix);
  });
  return <span ref={mark} data-id-scope-mark="" hidden />;
};

/** Scope the ids of everything inside to `scope` (a beat, a stage run). Adds no box: the wrapper is display:contents. */
export const IdScope: React.FC<{scope: string; children: React.ReactNode}> = ({scope, children}) => {
  const suffix = scope.replace(/[^A-Za-z0-9_-]/g, '');
  if (!suffix) throw new Error(`IdScope: the scope '${scope}' has no id-safe characters`);
  return (
    <div data-id-scope={suffix} style={{display: 'contents'}}>
      <Runner suffix={suffix} />
      {children}
    </div>
  );
};
