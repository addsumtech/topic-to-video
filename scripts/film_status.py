#!/usr/bin/env python3
"""film_status — where a director-path film stands, read from its folder: what is done, what is stale, what is next.

    python3 scripts/film_status.py <film_dir> [--json]

Reads only what the steps leave on disk (SKILL.md steps 2-8): brief.json, content_plan.json, script.json,
timeline.json, design/ (story, concepts, keyframes, treatment, animatic), shot_plan.json, film.html, work/frames,
audio/mix.wav, final.mp4 (+ .share.mp4, .srt, out.cover.png) and _qc.json, the record film_qc leaves of its last run. A
step whose output is OLDER than what it was made from is stale (the script edited after the voice was made, shot code
edited after the frames were rendered, frames re-rendered after the encode, the film re-encoded after its check), and
the first missing or stale step is NEXT, with the command for the mechanical ones. The film's own clock (the earliest
and latest file it wrote) is said, and the measured cost of the mechanical steps left (frames ~0.03 s each with 4
pages, an encode ~2 min, film_qc ~5 min for a 2-minute film); the steps an agent does (research, design, building) are
never given a number nobody measured.

WHY. The MRI film's run (2026-11-19) stopped at a usage limit in the middle of its fix round: shots fixed, two Blender
clips re-rendered, the frames, encode and check not yet redone. Picking it up meant reading two transcripts to learn
what was done; a run that resumes must be able to read that off the folder in one command, and never start over.
Exit 0 (the report; a film with nothing left says DONE), 2 usage error / not a film folder.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = "usage: film_status.py <film_dir> [--json]"
SKIPPABLE = ("5b animatic",)   # a sign-off a run may skip; the checks never are
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = "python3 %s/scripts/" % SKILL.replace(os.path.expanduser("~"), "~")


def _m(d, *rel):
    """Newest mtime among the paths (globs allowed) under d, or None."""
    ts = [os.path.getmtime(p) for r in rel for p in glob.glob(os.path.join(d, r)) if os.path.isfile(p)]
    return max(ts) if ts else None


def _oldest(d, rel):
    ts = [os.path.getmtime(p) for p in glob.glob(os.path.join(d, rel))]
    return min(ts) if ts else None


def status(d):
    plan = {}
    if os.path.isfile(os.path.join(d, "_plan.json")):
        plan = json.load(open(os.path.join(d, "_plan.json"), encoding="utf-8"))
    video = plan.get("video", "final.mp4")
    stem = os.path.splitext(video)[0]
    frames = glob.glob(os.path.join(d, "work", "frames", "f_*.jpg"))
    page_src = ("film.html", "shots/*", "lib/*", "*.js", "media/*", "clips/*.mp4", "img/*")
    qc = {}
    if os.path.isfile(os.path.join(d, "_qc.json")):
        qc = json.load(open(os.path.join(d, "_qc.json"), encoding="utf-8"))
    steps = []

    def step(name, done, stale=None, next_cmd=None, note=None):
        steps.append({"step": name, "state": "stale" if done and stale else ("done" if done else "todo"),
                      "why": stale, "next": next_cmd, "note": note})

    step("2 research", _m(d, "brief.json") is not None)
    step("2 content plan", _m(d, "content_plan.json") is not None)
    sj, tl = _m(d, "script.json"), _m(d, "timeline.json")
    step("3 script", sj is not None)
    step("4 voice + timeline", tl is not None,
         "script.json changed after the voice was made: re-voice the changed lines" if sj and tl and sj > tl + 1 else None)
    step("5 design", all(_m(d, "design/" + f) for f in ("concepts.md", "keyframes.jpg")) or _m(d, "design/keyframes/*") is not None,
         note=None if _m(d, "design/treatment.md") else "no design/treatment.md")
    step("5b animatic", _m(d, "design/animatic.mp4") is not None, next_cmd=S + "animatic.py %s" % d)
    built = _m(d, "film.html") is not None
    step("6 build (film page)", built)
    n_plan, src = int(plan.get("frames") or 0), _m(d, *page_src)
    stale = None
    if frames and n_plan and len(frames) < n_plan:
        stale = "%d of %d frames rendered" % (len(frames), n_plan)
    elif frames and src and src > _oldest(d, "work/frames/f_*.jpg") + 1:
        newer = sorted({os.path.relpath(p, d) for r in page_src for p in glob.glob(os.path.join(d, r))
                        if os.path.isfile(p) and os.path.getmtime(p) > _oldest(d, "work/frames/f_*.jpg") + 1})
        stale = ("some frames were rendered before the page last changed (%s%s): re-render the shots those files draw, "
                 "or all of them (~%d min)" % (", ".join(newer[:5]), ", …" if len(newer) > 5 else "", max(1, round(0.03 * (n_plan or 3600) / 60))))
    step("6 frames", bool(frames), stale, S + "film_frames.py %s --workers 4" % d,
         note=None if n_plan else "no _plan.json yet (write it with the cut frames)")
    mix = _m(d, "audio/mix.wav")
    step("7 sound (audio/mix.wav)", mix is not None)
    fv = _m(d, video)
    newest_in = max([t for t in (_m(d, "work/frames/f_*.jpg"), mix) if t] or [0])
    step("8 encode (%s)" % video, fv is not None,
         "frames or the mix changed after the encode" if fv and newest_in > fv + 1 else None,
         S + "film_deliver.py %s --encode" % d)
    qc_ok = qc and fv and qc.get("video_mtime", 0) >= fv - 1 and not qc.get("only") and not qc.get("frames")
    step("8 film_qc", bool(qc_ok) and not qc.get("red"),
         None, S + "film_qc.py %s" % d,
         note=("red: %s (fix, or prove a red wrong in NOTES.md)" % ", ".join(qc["red"])) if qc_ok and qc.get("red")
         else ("last run was before the current encode, or partial" if qc and not qc_ok else None))
    step("8 deliver (.share.mp4, .srt, cover)", all(_m(d, f) for f in (stem + ".share.mp4", stem + ".srt", "out.cover.png")),
         "the film was re-encoded after its share copy" if _m(d, stem + ".share.mp4") and fv and fv > _m(d, stem + ".share.mp4") + 1 else None,
         S + "film_deliver.py %s" % d)
    # a step left undone while later steps went ahead was skipped on purpose (a non-interactive run's animatic,
    # a design kept in NOTES.md): said, never sent back to
    for i, s in enumerate(steps):
        if s["step"] in SKIPPABLE and s["state"] == "todo" and any(x["state"] != "todo" for x in steps[i + 1:]):
            s["state"] = "skipped"
    nxt = next((s for s in steps if s["state"] not in ("done", "skipped")), None)
    # what the mechanical steps left would cost, from their measured rates (never the agent's own steps)
    left = 0.0
    for s in steps[steps.index(nxt):] if nxt else []:
        if s["step"] == "6 frames":
            left += 0.03 * (n_plan or 3600)
        elif s["step"].startswith("8 encode"):
            left += 120
        elif s["step"] == "8 film_qc":
            left += 300
    # the film's own clock: from the first thing the run wrote to the newest file (material copied in keeps its own
    # old dates, so input/ and sources/ do not start it)
    first = [t for t in (_m(d, f) for f in ("NOTES.md", "brief.json", "content_plan.json", "script.json")) if t]
    files = [p for p in glob.glob(os.path.join(d, "**"), recursive=True)
             if os.path.isfile(p) and not os.path.relpath(p, d).startswith(("input" + os.sep, "sources" + os.sep))]
    clock = (min(first), max(map(os.path.getmtime, files))) if first and files else None
    prog = None
    if os.path.isfile(os.path.join(d, "_progress.json")):      # a long step under way (scripts/progress.py)
        import progress
        try:
            prog = progress.line(json.load(open(os.path.join(d, "_progress.json"), encoding="utf-8")))
        except (OSError, ValueError):
            prog = None
    return {"steps": steps, "next": nxt, "mechanical_left_s": round(left) if nxt else 0,
            "clock_h": round((clock[1] - clock[0]) / 3600, 2) if clock else None, "progress": prog}


def main(argv):
    _c.refuse_unknown(argv, switches=("json",), usage=_USAGE)
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    if not any(os.path.exists(os.path.join(d, f)) for f in ("brief.json", "script.json", "timeline.json", "film.html", "NOTES.md")):
        print("film_status: %s is not a film folder (no brief, script, timeline, page or NOTES.md)" % d, file=sys.stderr)
        return 2
    r = status(d)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    mark = {"done": "✓", "stale": "~", "todo": "·", "skipped": "-"}
    for s in r["steps"]:
        print("  %s %-38s %s" % (mark[s["state"]], s["step"], "; ".join(x for x in (s["why"], s["note"]) if x)))
    if r["progress"]:
        print("  now: %s" % r["progress"])
    if r["next"]:
        n = r["next"]
        print("NEXT: %s%s" % (n["step"], (" — " + n["next"]) if n["next"] and n["step"][0] in "568" else ""))
        if r["mechanical_left_s"]:
            print("      the mechanical steps from here (render, encode, check) take ~%d min; the film's own clock so far %.1f h"
                  % (round(r["mechanical_left_s"] / 60), r["clock_h"] or 0))
    else:
        print("DONE: checked and delivered (the film's own clock %.1f h)" % (r["clock_h"] or 0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
