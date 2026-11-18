"""film_qc — the director path's picture checks in one command, quiet unless something is wrong.

    python3 scripts/film_qc.py <film_dir>        # reads <film_dir>/final.mp4 and <film_dir>/_plan.json

Runs, in order: flash_qa (a frame unlike both neighbours), rewind_qa (the picture going back after a cut, read
against the plan's cuts), picture_glide_qa (a picture stepping instead of gliding under a moving camera),
empty_frame_qa (a blank hold of a second or more), shake_qa (the whole frame vibrating instead of travelling) and
caption_size_qa (burned captions too small to read on a phone); with a film.html, page_overlap_qa (words or
controls colliding on the page over time) and film_copy_qa (every word shown comes from the sources or is declared);
with a stage3d page, stage_contacts_qa (nothing passes through anything); pan_speed_qa (no camera whip that strobes); with a shot_plan.json, also shot_plan_qa (the craft
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

HERE = os.path.dirname(os.path.abspath(__file__))


def checks(d, video, plan):
    py = sys.executable
    base = [
        ("flash", [py, os.path.join(HERE, "flash_qa.py"), video]),
        ("rewind", [py, os.path.join(HERE, "rewind_qa.py"), video, "--plan", plan]),
        ("glide", [py, os.path.join(HERE, "picture_glide_qa.py"), d, "--video=" + video]),
        ("empty", [py, os.path.join(HERE, "empty_frame_qa.py"), video]),
        ("shake", [py, os.path.join(HERE, "shake_qa.py"), video]),
        ("captions", [py, os.path.join(HERE, "caption_size_qa.py"), video]),
    ]
    page = os.path.isfile(os.path.join(d, "film.html"))
    out = list(base)
    if page:
        out += [("overlaps", [py, os.path.join(HERE, "page_overlap_qa.py"), d]),
                ("copy", [py, os.path.join(HERE, "film_copy_qa.py"), d])]
    if _uses_stage3d(d):
        out.append(("contacts", [py, os.path.join(HERE, "stage_contacts_qa.py"), d]))
    out.append(("pan speed", [py, os.path.join(HERE, "pan_speed_qa.py"), d]))
    if os.path.isfile(os.path.join(d, "shot_plan.json")):
        out += [("shot plan", [py, os.path.join(HERE, "shot_plan_qa.py"), d]),
                ("seams", [py, os.path.join(HERE, "seam_qa.py"), d])]
    return out


def _uses_stage3d(d):
    page = os.path.join(d, "film.html")
    return os.path.isfile(page) and "stage3d" in open(page, encoding="utf-8", errors="replace").read()


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    d = os.path.abspath(argv[0])
    plan = os.path.join(d, "_plan.json")
    if not os.path.isfile(plan):
        print("film_qc: %s has no _plan.json — the renderer must write it (see this script's doc)" % d, file=sys.stderr)
        return 2
    video = os.path.join(d, json.load(open(plan, encoding="utf-8")).get("video", "final.mp4"))
    if not os.path.isfile(video):
        print("film_qc: no video at %s" % video, file=sys.stderr)
        return 2
    red = []
    for name, cmd in checks(d, video, plan):
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            print("OK   %s" % name)
        else:
            red.append(name)
            print("RED  %s (exit %d)\n%s" % (name, r.returncode, "\n".join("     " + l for l in out.splitlines()[-25:])))
    print("film_qc: %s" % ("CLEAN" if not red else "RED — " + ", ".join(red)))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
