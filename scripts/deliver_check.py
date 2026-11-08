#!/usr/bin/env python3
"""deliver_check — every delivery gate a film needs, run as one and recorded against the film it measured.

    python3 scripts/deliver_check.py <out_dir>            # the FAST tier (~30 s): the gates that read out.mp4
    python3 scripts/deliver_check.py <out_dir> --full     # + the gates that render a census (~10 min): the final cut

WHY THIS EXISTS. The skill has twenty-odd gates and no one command ran the blocking ones. On the topic-to-video promo
(2026-11-03) they were run from memory, film_energy_qa was missed, and a film that measured as a slideshow (motion p75
0.0027 against a 0.0037 floor) reached the user's Desktop — deliver.py copied it although the render had written
NOT_DELIVERED.md. Measured on that 137 s film: check_av 2 s, flash 5 s, film_energy 11 s, rhythm 9 s, seam_ledger ~5 s
(the FAST tier, ~30 s); media_res 65 s, text_safe ~4 min, jitter ~6 min (the census tier). deliver.py runs the fast tier
on every hand-off; the full tier is asked for once, for the cut that ships.

A RESULT IS KEYED BY THE FILM: out.mp4's bytes and the board's. An unchanged film is never re-checked, and a re-render
invalidates the record. A gate that exits 1 FAILS; one that exits 2 (it could not measure) is NOT MEASURED, which is
not a pass. The board may waive a gate by name with a reason — `meta.delivery_waivers: {"jitter_qa": "the figure's
warp is the beat"}` — and the waiver is printed with the result, never silent.

Written to <out_dir>/_delivery_check.json. Exit 0 when every gate passed or is waived, 1 otherwise.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = "_delivery_check.json"

# (gate, tiers it runs in, renderers it applies to). The fast gates read out.mp4; the full ones render a census.
GATES = (
    ("check_av", "fast", ("remotion", "local")),
    ("flash_qa", "fast", ("remotion", "local")),
    ("film_energy_qa", "fast", ("remotion",)),
    ("rhythm_qa", "fast", ("remotion", "local")),
    ("seam_ledger", "fast", ("remotion",)),
    ("named_objects_qa", "fast", ("remotion",)),
    ("media_res_qa", "full", ("remotion",)),
    ("text_safe_qa", "full", ("remotion",)),
    ("jitter_qa", "full", ("remotion",)),
)


def _renderer(meta):
    r = str((meta or {}).get("renderer") or "local")
    return "remotion" if r == "remotion" else "local"


def gates_for(meta, tier="fast"):
    """The gates a film of this renderer runs in `tier` (fast ⊂ full), in order."""
    r = _renderer(meta)
    return [g for g, t, rs in GATES if r in rs and (tier == "full" or t == "fast")]


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_gate(gate, out_dir):
    """(exit code, its last summary line) — the gate run as the pipeline runs it."""
    r = subprocess.run([sys.executable, os.path.join(_HERE, gate + ".py"), out_dir], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True)
    lines = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
    summary = next((ln for ln in reversed(lines) if ln.lstrip().startswith("[")), lines[-1] if lines else "")
    return r.returncode, summary.strip()[:300]


def _load(out_dir):
    try:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def check(out_dir, full=False, run=None, force=False):
    """The record: {film, board, tier, ok, gates: [{name, status: pass|fail|not measured|waived, rc, seconds, summary,
    waiver?}]}. Reuses a record for the same film and board at the same or a fuller tier."""
    run = run or _run_gate
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        raise SystemExit("deliver_check: %s has no out.mp4 — render the film first" % out_dir)
    board = _load(out_dir)
    meta = board.get("meta") or {}
    film, bsha = _sha(mp4), hashlib.sha256(json.dumps(board, sort_keys=True).encode("utf-8")).hexdigest()
    tier = "full" if full else "fast"
    path = os.path.join(out_dir, RECORD)
    if not force and os.path.exists(path):
        try:
            old = json.load(open(path, encoding="utf-8"))
            if old.get("film") == film and old.get("board") == bsha and (old.get("tier") == "full" or tier == "fast"):
                return old
        except (OSError, ValueError):
            pass
    waivers = meta.get("delivery_waivers") or {}
    rows = []
    for g in gates_for(meta, tier):
        t0 = time.time()
        rc, summary = run(g, out_dir)
        status = "pass" if rc == 0 else "not measured" if rc == 2 else "fail"
        row = {"name": g, "rc": rc, "status": status, "seconds": round(time.time() - t0, 1), "summary": summary}
        if status != "pass" and isinstance(waivers.get(g), str) and waivers[g].strip():
            row["status"], row["waiver"] = "waived", waivers[g].strip()
        rows.append(row)
    rec = {"film": film, "board": bsha, "tier": tier, "ok": all(r["status"] in ("pass", "waived") for r in rows),
           "gates": rows, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def report(rec):
    for r in rec["gates"]:
        print("[deliver_check] %-14s %-12s %5.1fs  %s%s" % (r["name"], r["status"].upper(), r["seconds"], r["summary"],
                                                           ("  (waived: %s)" % r["waiver"]) if r.get("waiver") else ""))
    print("[deliver_check] %s — %s tier, %d gate(s)%s" % (
        "OK" if rec["ok"] else "FAIL", rec["tier"], len(rec["gates"]),
        "" if rec["tier"] == "full" else "; the census gates (media_res, text_safe, jitter) run with --full, once, "
                                         "for the cut that ships"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--full", action="store_true", help="add the gates that render a census (~10 min)")
    ap.add_argument("--force", action="store_true", help="re-run even when the film and board are unchanged")
    a = ap.parse_args(argv)
    rec = check(a.out_dir, full=a.full, force=a.force)
    report(rec)
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
