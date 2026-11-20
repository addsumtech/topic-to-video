"""film_qc — the director path's picture checks in one command, quiet unless something is wrong.

    python3 scripts/film_qc.py <film_dir> [--only glide,seams]     # reads <film_dir>/final.mp4 and <film_dir>/_plan.json
    python3 scripts/film_qc.py <film_dir> --frames A-B [--only ...] # one builder's shots, before the film is assembled

The checks run SIDE BY SIDE, each with one maths thread (a check's BLAS starting a thread per core while twelve others
did the same made a 2-minute film's checks take over an hour, 2026-11-18); a 2-minute film checks in a few minutes.
--only re-runs just the named checks (after a fix, the ones that were red); the rest are not re-judged.
--frames A-B judges film frames A..B-1 from work/frames (film_frames.py's output) BEFORE the film exists: they are
encoded as the film will be (film_deliver's encode, grain and all) into work/qc_A-B/ with the plan cut to that stretch,
and the page checks step through only those seconds. The film-wide checks (repetition, mix, shot plan) wait for the
whole film. WHY: the MRI film (2026-11-19) met film_qc only once all four builders were done; seven checks went red
across every builder's shots and the fix round (re-render, re-encode, re-check) cost an hour; each builder checking
its own frames first finds the same defects while the shot is still open. The whole film is still checked at the end.

Runs, in order: flash_qa (a frame unlike both neighbours), rewind_qa (the picture going back after a cut, read
against the plan's cuts), picture_glide_qa (a picture stepping instead of gliding under a moving camera),
empty_frame_qa (a blank hold of a second or more), shake_qa (the whole frame vibrating instead of travelling) and
caption_size_qa (burned captions too small to read on a phone); with a film.html, page_overlap_qa (words or
controls colliding on the page over time, or a readable line cut by the frame's edge), film_copy_qa (every word shown
comes from the sources or is declared) and picture_legibility_qa (a picture on screen that shows almost nothing);
with a stage3d page, stage_contacts_qa (nothing passes through anything); pan_speed_qa (no camera whip that strobes);
repetition_qa (advisory: one staging repeated as the film's device); banding_qa (dark gradients stepping after the
encode; scripts/film_deliver.py --encode adds the grain finish that fixes it); mix (a film with music in audio/ ships
the mix scripts/mix.py made and measured, the music held under the voice); with a shot_plan.json, also shot_plan_qa (the craft
plan is sound) and seam_qa (every seam the plan says is hidden really is).
Prints one line per check — OK, or the check's own findings — and exits 1 if any check is red, so "clean" is a
fact the caller can test, not a reading of the log.

_plan.json (written by the film's own renderer):
  {"video": "final.mp4", "fps": 30, "frames": <total>, "cuts": [<frame of every cut>],
   "segments": [{"start": <frame>, "end": <frame, exclusive>, "kind": "shot" | "loop"}, ...]}
"""
import json
import os
import subprocess
import sys

import _common as _c

HERE = os.path.dirname(os.path.abspath(__file__))


# judged on the whole film only: one staging repeated across the film, the music under the voice, the plan itself
FILM_WIDE = ("repetition", "mix", "shot plan")


def checks(d, video, plan, span=None, page_dir=None):
    """`span` (A, B): `d` is the stretch's own folder (its video and cut plan); the page checks run on `page_dir`, the
    film's folder, limited to those frames."""
    py = sys.executable
    page_dir = page_dir or d
    pspan = ["--frames", "%d-%d" % span] if span else []
    base = [
        ("flash", [py, os.path.join(HERE, "flash_qa.py"), video]),
        ("rewind", [py, os.path.join(HERE, "rewind_qa.py"), video, "--plan", plan]),
        ("glide", [py, os.path.join(HERE, "picture_glide_qa.py"), d, "--video=" + video, "--jobs=%d" % max(2, (os.cpu_count() or 4) // 4)]),
        ("empty", [py, os.path.join(HERE, "empty_frame_qa.py"), video]),
        ("shake", [py, os.path.join(HERE, "shake_qa.py"), video]),
        ("captions", [py, os.path.join(HERE, "caption_size_qa.py"), video]),
    ]
    page = os.path.isfile(os.path.join(page_dir, "film.html"))
    out = list(base)
    if page:
        out += [("overlaps", [py, os.path.join(HERE, "page_overlap_qa.py"), page_dir] + pspan),
                ("copy", [py, os.path.join(HERE, "film_copy_qa.py"), page_dir] + pspan),
                ("pictures", [py, os.path.join(HERE, "picture_legibility_qa.py"), page_dir] + pspan)]
    if _uses_stage3d(page_dir):
        out.append(("contacts", [py, os.path.join(HERE, "stage_contacts_qa.py"), page_dir] + pspan))
    out.append(("pan speed", [py, os.path.join(HERE, "pan_speed_qa.py"), d]))
    out.append(("repetition", [py, os.path.join(HERE, "repetition_qa.py"), d, "--video=" + video]))   # advisory
    out.append(("banding", [py, os.path.join(HERE, "banding_qa.py"), d, "--video", video]))
    out.append(("mix", [py, os.path.join(HERE, "mix.py"), "--check", d]))
    if os.path.isfile(os.path.join(d, "shot_plan.json")):
        out += [("shot plan", [py, os.path.join(HERE, "shot_plan_qa.py"), d]),
                ("seams", [py, os.path.join(HERE, "seam_qa.py"), d])]
    return [c for c in out if not span or c[0] not in FILM_WIDE]


def stretch(d, span):
    """Frames A..B-1 of work/frames encoded as the film will be, in work/qc_A-B/ with _plan.json (and shot_plan.json)
    cut to that stretch and shifted to start at 0. Returns that folder; exits 2 naming missing frames."""
    import film_deliver
    a, b = span
    src = os.path.join(d, "work", "frames")
    missing = [n for n in range(a, b) if not os.path.isfile(os.path.join(src, "f_%05d.jpg" % n))]
    if missing:
        print("film_qc: --frames %d-%d: %d frame(s) not rendered in %s (first %d): render them with film_frames.py --from %d --to %d"
              % (a, b, len(missing), src, missing[0], a, b), file=sys.stderr)
        raise SystemExit(2)
    plan = json.load(open(os.path.join(d, "_plan.json"), encoding="utf-8"))
    fps = float(plan.get("fps", 30))
    out = os.path.join(d, "work", "qc_%d-%d" % span)
    os.makedirs(out, exist_ok=True)
    sub = dict(plan, video="final.mp4", frames=b - a, cuts=[c - a for c in plan.get("cuts") or [] if a < c < b],
               segments=[dict(g, start=max(g["start"], a) - a, end=min(g["end"], b) - a)
                         for g in plan.get("segments") or [] if g["start"] < b and g["end"] > a])
    json.dump(sub, open(os.path.join(out, "_plan.json"), "w"), indent=1)
    sp = os.path.join(d, "shot_plan.json")
    if os.path.isfile(sp):
        shp = json.load(open(sp, encoding="utf-8"))
        t0, t1 = a / fps, b / fps
        shp["shots"] = [dict(x, start=max(float(x["start"]), t0) - t0, end=min(float(x["end"]), t1) - t0)
                        for x in shp.get("shots") or [] if float(x["start"]) < t1 and float(x["end"]) > t0]
        json.dump(shp, open(os.path.join(out, "shot_plan.json"), "w"), indent=1)
    elif os.path.isfile(os.path.join(out, "shot_plan.json")):
        os.remove(os.path.join(out, "shot_plan.json"))
    film_deliver.encode(out, src, None, os.path.join(out, "final.mp4"), 3, start=a, count=b - a)
    return out


def _uses_stage3d(d):
    page = os.path.join(d, "film.html")
    return os.path.isfile(page) and "stage3d" in open(page, encoding="utf-8", errors="replace").read()


def main(argv):
    _c.refuse_unknown(argv, valued=("only", "frames"), usage=__doc__.strip().splitlines()[2].strip())
    span = _c.frame_span(argv)
    only = _c.argflag_list(argv, "only")
    if any(a.split("=", 1)[0] == "--only" for a in argv) and not only:
        print("[film_qc] --only needs check names, e.g. --only glide,seams", file=sys.stderr)
        return 2
    only = None if only is None else set(only)
    flag = [i for i, a in enumerate(argv) if a.split("=", 1)[0] in ("--only", "--frames")]
    taken = set(flag) | {i + 1 for i in flag if "=" not in argv[i]}
    argv = [a for i, a in enumerate(argv) if i not in taken]
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    d = os.path.abspath(argv[0])
    plan = os.path.join(d, "_plan.json")
    if not os.path.isfile(plan):
        print("film_qc: %s has no _plan.json — the renderer must write it (see this script's doc)" % d, file=sys.stderr)
        return 2
    if span:
        n = int(json.load(open(plan, encoding="utf-8")).get("frames") or 0)
        if n and span[1] > n:
            print("film_qc: --frames %d-%d runs past the film's %d frames" % (span[0], span[1], n), file=sys.stderr)
            return 2
        q = stretch(d, span)
        todo = checks(q, os.path.join(q, "final.mp4"), os.path.join(q, "_plan.json"), span, page_dir=d)
    else:
        video = os.path.join(d, json.load(open(plan, encoding="utf-8")).get("video", "final.mp4"))
        if not os.path.isfile(video):
            print("film_qc: no video at %s" % video, file=sys.stderr)
            return 2
        todo = checks(d, video, plan)
    if only is not None:
        unknown = only - {n for n, _ in todo}
        if unknown:
            print("film_qc: no check named %s (checks: %s)" % (", ".join(sorted(unknown)), ", ".join(n for n, _ in todo)),
                  file=sys.stderr)
            return 2
        todo = [(n, c) for n, c in todo if n in only]
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
    from concurrent.futures import ThreadPoolExecutor
    run = lambda cmd: subprocess.run(cmd, capture_output=True, text=True, env=env)   # noqa: E731
    with ThreadPoolExecutor(max(2, (os.cpu_count() or 4) // 2)) as ex:
        results = list(ex.map(lambda nc: (nc[0], run(nc[1])), todo))
    red = []
    for name, r in results:
        out = (r.stdout + r.stderr).strip()
        warns = [l.strip() for l in out.splitlines() if l.lstrip("[").split("]")[-1].strip().startswith("WARN")
                 or " WARN " in l]
        if r.returncode == 2 and "NOT MEASURED" in out:   # this machine cannot measure it: said, never passed off as OK
            print("WARN %s (not measured)\n%s" % (name, "\n".join("     " + l for l in out.splitlines()[-3:])))
        elif r.returncode == 0 and warns:      # an ADVISORY finding: shown, never hidden behind an OK
            print("WARN %s\n%s" % (name, "\n".join("     " + l for l in warns[:6])))
        elif r.returncode == 0:
            print("OK   %s" % name)
        else:
            red.append(name)
            print("RED  %s (exit %d)\n%s" % (name, r.returncode, "\n".join("     " + l for l in out.splitlines()[-25:])))
    print("film_qc: %s%s%s" % ("CLEAN" if not red else "RED — " + ", ".join(red),
                               "" if only is None else "  (only: %s)" % ", ".join(n for n, _ in todo),
                               "" if not span else "  (frames %d-%d only; the whole film is checked once assembled)" % span))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
