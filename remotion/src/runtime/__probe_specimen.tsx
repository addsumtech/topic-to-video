// PROBE — renders one library shot inside a chosen DNA, for the type specimen contact sheet.
//
// Task 9 found this probe gave a FALSE "unchanged" reading for every row: it provides
// DesignDNAContext (so the handful of shots that read `dna?.fontDisplay` etc. directly via the
// useDNA() hook already varied correctly, even before Task 9), but it never reproduced Film.tsx's
// `.dna-film { --f-display: ...; }` <style> injection — the ONLY place that CSS custom property is
// ever set (see Film.tsx). Since the codemod's whole mechanism is shots reading
// `var(--f-body, <original>)`, and that variable is unset outside `.dna-film`, every codemod-touched
// shot rendered through this probe fell back to its ORIGINAL hardcoded family regardless of which
// `dnaId` was requested — a specimen sheet that would look byte-identical to Task 5's no matter what
// Task 9 did. Wrapping in the same `.dna-film` class + <style> block Film.tsx uses fixes that: this
// probe is now a faithful (if minimal) stand-in for the real Film pipeline's type layer.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {DesignDNAContext, DNA_PRESETS} from './dna';
import {REGISTRY} from '../registry';

export const DURATION = 150;

export const TypeSpecimen: React.FC<{shot?: string; dnaId?: string}> = ({
  shot = 'EdStat', dnaId = 'editorial'}) => {
  const C = REGISTRY[shot];
  const dna = DNA_PRESETS[dnaId] ?? null;
  return (
    <AbsoluteFill style={{background: dna?.bg ?? '#000'}}>
      <DesignDNAContext.Provider value={dna}>
        {dna ? <style>{`.dna-film { --f-display: ${dna.fontDisplay}; --f-body: ${dna.fontBody}; --f-mono: ${dna.fontMono}; }`}</style> : null}
        {dna?.uniformType ? <style>{`.dna-film, .dna-film * { font-family: ${dna.fontMono} !important; }`}</style> : null}
        <AbsoluteFill className="dna-film">{C ? <C /> : null}</AbsoluteFill>
      </DesignDNAContext.Provider>
    </AbsoluteFill>
  );
};
export default TypeSpecimen;

