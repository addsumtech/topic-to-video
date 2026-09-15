#!/usr/bin/env python3
"""Which beats are STARVED, and what the same family offers instead.

    python3 scripts/density_advice.py <out_dir>

WHY THIS AND NOT A PRIMITIVE. The density axis is the one that did not close, and four candidate shared
levers were built and measured and all four failed:

  * the DNA's `surface` token is invisible in all eight presets (within 0.083 of its own ground, under the
    0.10 the instrument can see) — but raising it moved four container-bearing registers by +0.0 to +0.8
    points. The containers are not invisible, they are small or absent.
  * more content saturates: TermTable at 2 stub rows is 1.1%, at 5 real rows 4.0%, at 12 rows across 4
    columns 4.7% — six times the content for 4.3x the ink, still under half the floor. Text at reading size
    barely inks a frame.
  * a divided ground painted UNDER the shot is invisible: 148 of 149 registers paint their own full-frame
    ground from `dna.bg`, so an underlay is covered.
  * a divided ground sent through `bgGrad` — the token 143 registers already paint — IS visible and took a
    beat from 5.7% to 14.4%, over the floor. It was reverted after looking at it: the register's content
    ignores the boundary, so the division renders as a coloured MARGIN around a card. A better number and a
    worse frame is the exact failure this project keeps finding, and a required `reason` string cannot make
    149 registers respect a line they do not know about.

So density is per-register work. What generalises is not a mechanism but DIRECTION: every family holds both
starved and dense registers — family F spans 1.3% (DiffusionDenoise) to 63.9% (AuroraFlow), family A 1.7%
(GrantedTree) to 47.9% (LastLeg), family G 0.0% (ScanReconstruct) to 61.3% (PaperCutout) — so a beat on a
starved register usually has a dense alternative in the SAME design family, which is the one substitution
that does not change the film's visual language.

THIS DOES NOT PICK FOR YOU, and must not. A register is chosen because it ENCODES the beat's idea; swapping
to whatever measures densest is how a film ends up with 49.8% ink of undecodable dashes. This makes the
starvation visible and names the neighbours; the decision stays a design decision.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import film_energy_qa as fe                                      # noqa: E402
import register_energy as re                                     # noqa: E402
import shot_director as sd                                       # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(_ROOT, "remotion", "register_energy.json")


def measured(strict=True):
    """{register: ink_median}, from the committed sweep. Fails loud if the sweep is missing OR STALE.

    Stale is the dangerous one, and it happened: three registers were rewritten to 32.2%, 51.1% and 2.4%
    while the manifest still read 0.6%, 2.0% and 1.0%, so this would have named one of the densest registers
    in the library as a starved beat's problem and offered it alternatives. Advice from a record that no
    longer describes the code is worse than no advice, because it reads as measured.
    """
    if not os.path.exists(MANIFEST):
        raise RuntimeError("no %s — run `python3 scripts/register_energy.py` first; this advises from "
                           "measured pixels, never from an opinion about a register" % MANIFEST)
    d = json.load(open(MANIFEST, encoding="utf-8"))
    rows = {k: v["ink_median"] for k, v in (d.get("registers") or {}).items()}
    if strict:
        bad = re.stale(d)
        if bad:
            raise RuntimeError(
                "%d of %d measured row(s) no longer describe their register's source (%s%s). Re-run "
                "`python3 scripts/register_energy.py` — advice from a stale sweep reads as measured and is "
                "not." % (len(bad), len(rows), ", ".join(n for n, _ in bad[:4]),
                          ", …" if len(bad) > 4 else ""))
    return rows


def alternatives(shot, ink, floor, limit=3):
    """Denser registers in the SAME family, densest first. Same family = the same design shelf, so the
    substitution does not change the film's visual language — a cross-family swap is a different film."""
    fam = sd.FAMILY.get(shot)
    if fam is None:
        return []
    out = [(v, n) for n, v in ink.items()
           if n != shot and sd.FAMILY.get(n) == fam and v >= floor]
    out.sort(reverse=True)
    return out[:limit]


def advise(out_dir):
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    ink = measured()
    floor = fe.INK_FLOOR
    beats, unknown = [], []
    # by POSITION, not the 1-based `index` field this used to add one to — see critic_brief.
    for _pos, s in enumerate(board.get("slides") or [], start=1):
        shot = s.get("shot")
        if not shot:
            continue
        if shot not in ink:
            # An unmeasured register would silently read as "fine" in the median below — the absence-is-a-pass
            # failure this repo keeps finding. Name it instead.
            unknown.append(shot)
            continue
        beats.append((_pos, shot, ink[shot]))
    return beats, unknown, ink, floor


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: density_advice.py <out_dir>")
        return 2
    out_dir = os.path.abspath(argv[0])
    beats, unknown, ink, floor = advise(out_dir)
    if not beats:
        print("[density] no beats with a measured register")
        return 1 if unknown else 0
    vals = sorted(b[2] for b in beats)
    med = vals[len(vals) // 2]
    starved = [b for b in beats if b[2] < floor]
    print("[density] %d beat(s) · median register ink %.1f%% · floor %.0f%% · %d beat(s) under it"
          % (len(beats), med * 100, floor * 100, len(starved)))
    if unknown:
        print("[density] %d register(s) NOT in the sweep, so unmeasured rather than fine: %s"
              % (len(unknown), ", ".join(sorted(set(unknown)))))
    for beat, shot, v in starved:
        alts = alternatives(shot, ink, floor)
        line = "   beat %2d  %-22s %4.1f%%" % (beat, shot, v * 100)
        if alts:
            line += "   same family offers " + ", ".join("%s %.0f%%" % (n, x * 100) for x, n in alts)
        else:
            line += "   no denser register in its family — this beat needs its own composition"
        print(line)
    if starved:
        print("[density] These are CANDIDATES, not instructions. A register is chosen because it encodes the "
              "beat's idea; swapping to whatever measures densest is how a film ends up carrying ink no "
              "viewer can decode.")
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
