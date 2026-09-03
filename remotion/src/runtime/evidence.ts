// EVIDENCE — for registers whose PREMISE is a real artefact, not a diagram of one.
//
// WHY THIS EXISTS. Four registers in this library exist to put a real photograph on the frame — PhotoPlate
// ("the photograph IS the evidence and the film points at parts of it"), RealVersus, ScanReconstruct,
// MuseumLabel — and every one of them was written as `src ? <Img …/> : null`. With no source they render the
// FURNITURE around an absent picture: a bordered empty box, a caption under it, and in PhotoPlate's case two
// callout chips pointing at nothing, reading "what to notice here" and "and here". Measured, they are the
// emptiest registers in the library — RealVersus and ScanReconstruct at 0.0% ink, PhotoPlate at 0.6%.
//
// That is worse than failing. A frame that looks composed and says nothing passes every gate that reads a
// still, and a viewer sees a hole where the evidence was promised. Meanwhile the path works: fetching a
// licence-clean photograph with `scripts/imagefetch.py` into the film's public dir and handing the beat its
// `src` takes PhotoPlate from 0.6% to 30.6% — the picture is simply never supplied, and nothing said so.
//
// So a register whose premise is the artefact REFUSES to draw without it, loudly, naming the prop and the
// tool that gets one. This is the same discipline runtime/icons.tsx runs on an unknown glyph name: a hole a
// layout still reserves space for is a bug nobody notices until delivery.
export function requireEvidence(shot: string, prop: string, value: unknown, what: string): string {
  if (typeof value === 'string' && value.trim()) return value;
  throw new Error(
    `${shot} needs \`${prop}\` — ${what}. This register's whole premise is the real artefact; without it it ` +
    `draws the furniture around an absent picture, which reads as composed and says nothing. Fetch a ` +
    `licence-clean image into the film's public dir:\n` +
    `    python3 scripts/imagefetch.py "<the real subject>" <out_dir>/media/<name>.jpg\n` +
    `then set \`${prop}\` to its path relative to that dir (e.g. "media/<name>.jpg"). If this beat is not ` +
    `about a real artefact, it wants a different register.`);
}
