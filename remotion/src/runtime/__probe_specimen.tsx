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
import {CropType} from './textSafe';
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


// CROP SPECIMEN — the end-to-end fixture for the declared-crop decodability floor.
//
// The floor's browser-driven test used to be aimed at CinematicTitle, a production register that had been
// migrated to <CropType> as a demonstration. That migration was reverted (its crop did nothing for a short
// title, its wordmark left its own rail, and it failed shot_proof at default props), and the test went with
// it — which is the wrong coupling either way: a gate's end-to-end proof should not depend on a production
// register keeping a particular design. This specimen declares a crop and nothing else, so the test drives
// the real DOM path through a browser while the library stays free to change.
export const CROP_SPECIMEN_DURATION = 60;

export const CropSpecimen: React.FC<{word?: string; keep?: number; edge?: 'left' | 'right'}> = ({
  word = 'SUPERCALIFRAGILISTICEXPIALIDOCIOUS', keep = 0.25, edge = 'right'}) => (
  <AbsoluteFill style={{background: '#07090f', color: '#eef2f8'}}>
    <div style={{position: 'absolute', top: '30%', left: 0, right: 0}}>
      <CropType reason="the specimen exists to be cropped" keep={keep} edge={edge}
        fontFamily="Inter, system-ui, sans-serif" fontWeight={900} maxSize={320}>
        {word}
      </CropType>
    </div>
  </AbsoluteFill>
);
