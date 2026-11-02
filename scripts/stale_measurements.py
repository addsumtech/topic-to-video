#!/usr/bin/env python3
"""stale_measurements — which measured rows no longer describe their register, in every manifest, and the command
that re-measures them. No renders: a few seconds.

    python3 scripts/stale_measurements.py

WHY. A register's measured rows (energy, prop reach, ground reach, ground luma) are keyed by the hash of its source
AND everything it imports, so editing one runtime file stales every register that imports it — runtime/gesture.tsx
gaining `fingerPx` staled five registers in all four manifests. Each manifest has its own no-render check, but four
separate checks were not run before committing: three times the full suite found the stale rows after a push. Run
this after ANY edit under remotion/src, before committing; exit 1 names each stale register under its manifest
with the exact command, and a missing manifest is an error, never "fresh".
"""
import collections
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

import _common as _c  # noqa: E402

Check = collections.namedtuple("Check", "label module manifest command")
CHECKS = [
    Check("register_energy", "register_energy", os.path.join(_ROOT, "remotion", "register_energy.json"),
          "python3 scripts/register_energy.py --only {names}"),
    Check("prop_reach", "prop_reach", os.path.join(_ROOT, "remotion", "prop_reach.json"),
          "python3 scripts/prop_reach.py --only={names}"),
    Check("ground_reach", "measure_ground_reach", os.path.join(_ROOT, "remotion", "_ground_reach.json"),
          "python3 scripts/measure_ground_reach.py --only={names} --emit"),
    Check("ground_luma", "measure_ground_luma", os.path.join(_ROOT, "remotion", "_ground_luma.json"),
          "python3 scripts/measure_ground_luma.py --only={names} --record"),
]
Found = collections.namedtuple("Found", "label stale missing rows")


def find(paths=None):
    """[Found] in CHECKS order. `stale` is the manifest's own `stale(data)` — [(register, why)] — never a copy
    of its logic. `paths` ({label: path}) reads other copies of the manifests (tests)."""
    import importlib
    out = []
    for c in CHECKS:
        path = (paths or {}).get(c.label, c.manifest)
        if not os.path.exists(path):
            out.append(Found(c.label, [], True, 0))
            continue
        data = json.load(open(path, encoding="utf-8"))
        rows = data.get("registers") or data.get("table") or data.get("rows") or {}
        out.append(Found(c.label, list(importlib.import_module(c.module).stale(data)), False, len(rows)))
    return out


_USAGE = "usage: stale_measurements.py"


def main(argv, paths=None):
    _c.refuse_unknown(argv, valued=(), switches=(), usage=_USAGE)
    bad = 0
    for f, c in zip(find(paths), CHECKS):
        if f.missing:
            bad += 1
            print("[%s] MISSING  %s — nothing can say its rows are fresh" % (f.label, os.path.relpath(c.manifest, _ROOT)))
            continue
        if not f.stale:
            print("[%s] OK  %d row(s) describe their source" % (f.label, f.rows))
            continue
        bad += 1
        names = sorted({n for n, _ in f.stale})
        print("[%s] STALE  %d row(s):" % (f.label, len(f.stale)))
        for n, why in f.stale:
            print("    %-24s %s" % (n, why))
        print("  re-measure: " + c.command.format(names=",".join(names)))
    print("[stale_measurements] %s" % ("FAIL — re-measure before committing" if bad else "OK  all manifests fresh"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
