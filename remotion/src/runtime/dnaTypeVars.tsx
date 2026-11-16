// THE FILM'S TYPE RULES, as one element — every place a register is drawn under a DNA mounts this, so a gate that
// renders a shot on its own measures the type the film ships. There were three copies: Film.tsx, Root.tsx's
// DnaPreview and the type specimen, and DnaPreview (which shot_proof, text_safe and the type-collision gates render
// through) had neither the uniformType mono rule nor the Han/Latin autospace — the per-shot gates measured other
// type than the film (audit 2026-11-15, step 6).
import React from 'react';
import type {DesignDNA as DNA} from './dna';

export const DnaTypeVars: React.FC<{dna: DNA | null | undefined; autospace?: boolean}> = ({dna, autospace = false}) => (
  <>
    {dna ? <style>{`.dna-film { --f-display: ${dna.fontDisplay}; --f-body: ${dna.fontBody}; --f-mono: ${dna.fontMono}; }`}</style> : null}
    {dna?.uniformType ? <style>{`.dna-film, .dna-film * { font-family: ${dna.fontMono} !important; }`}</style> : null}
    {/* Chrome's text-autospace: the gap between Han and Latin or digits (Film.tsx says why `normal`) */}
    {autospace ? <style>{`.dna-film { text-autospace: normal; }`}</style> : null}
  </>
);
