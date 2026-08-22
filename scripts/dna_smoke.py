#!/usr/bin/env python3
"""dna_smoke — render EVERY registered shot once, under a themed DNA, in ONE film.

Why this exists: the audit tools are static. `dna_audit` can only see that a shot calls (and imports) useDNA — it
cannot see that the call landed in the WRONG SCOPE (a hook inserted into a module-scope subcomponent while the
background it feeds lives in the exported component → `dna is not defined` at render time). TypeScript does not
catch it either, because remotion's bundler strips types without checking them. Only a render catches it, so this
renders the whole library as one film: any ReferenceError in any shot fails the run.

Usage:  python scripts/dna_smoke.py [--template terminal-technical] [--frames 14] [--out /tmp/dna_smoke.mp4]
Exit 0 = every registered shot rendered under that DNA. Exit 1 = a shot is broken (the error names it).
"""
import json, os, subprocess, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import dna_audit


def main(argv):
    def opt(name, default):
        return argv[argv.index(name) + 1] if name in argv else default
    template = opt("--template", "terminal-technical")
    frames = int(opt("--frames", "14"))
    out = opt("--out", os.path.join(tempfile.gettempdir(), "dna_smoke.mp4"))
    shots = sorted(dna_audit.registered_shots())
    if not shots:
        print("no registered shots found"); return 1
    props = {"template": template, "captions": False,
             "scenes": [{"shot": s, "durF": frames} for s in shots]}
    pf = os.path.join(tempfile.gettempdir(), "dna_smoke_props.json")
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh)
    remotion = os.path.join(os.path.dirname(_HERE), "remotion")
    print(f"rendering {len(shots)} shots under the '{template}' DNA -> {out}")
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Film", out,
                        f"--props={pf}", "--gl=angle"], cwd=remotion,
                       capture_output=True, text=True)
    blob = (r.stdout or "") + (r.stderr or "")
    bad = [l for l in blob.split("\n")
           if "is not defined" in l or "Cannot read propert" in l or "Cannot access" in l or "An error occurred" in l]
    if r.returncode != 0 or bad:
        print("SMOKE FAILED — a shot cannot render under this DNA:")
        for l in bad[:12]:
            print("   " + l.strip())
        for l in blob.split("\n"):
            if "at " in l and "shots/" in l:
                print("   " + l.strip())
        return 1
    print(f"OK — all {len(shots)} registered shots rendered under '{template}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
