#!/usr/bin/env python3
"""Assemble everything a shot-critic needs into ONE file, so its pass is spent on judgment.

  python3 scripts/critic_brief.py <out_dir>        # writes <out_dir>/_critic_brief.md

WHY. A review used to cost a full render plus a long pass that opened 37 keyframes one at a time and
re-read a 1200-line contract and catalogue — most of it to re-derive things a script had already decided.
The mechanical half is now gated before the render (validate, shot_proof, frame_safe_qa, keyframe_qa,
check_av, voice_qa), so the critic's job is the half a script cannot do: does the design ENCODE the beat,
is the number sourced, does the register fit, is the film's shape right.

The brief carries:
  * the machine verdicts, already run — with an explicit list of what NOT to re-judge
  * a CONTACT SHEET of every beat (one image instead of thirty-seven; full frames on demand)
  * only the catalogue entries for the registers this film actually uses
  * the repetition, family and growth facts, computed rather than eyeballed

It deliberately does NOT summarise the beats' meaning. That is the judgment being asked for, and handing
over a summary of it would answer the question the critic is there to ask.
"""
import collections
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")


def _run(script, out_dir, *args, timeout=240):
    """Run one gate and return its output. A gate that hangs must not take the brief with it — the brief
    is what a reviewer waits on, and six unbounded subprocesses is six ways to wait forever."""
    try:
        r = subprocess.run([sys.executable, os.path.join(_HERE, script), out_dir, *args],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "[%s] TIMED OUT after %ds — run it yourself before trusting this brief" % (script, timeout)
    except OSError as e:
        return "[%s] could not run: %s" % (script, e)
    return (r.stdout or "").strip() or (r.stderr or "").strip()[:400]


def _library_entries(shots):
    """The catalogue lines for just these registers — not the whole 348-line file."""
    try:
        src = open(os.path.join(_REM, "LIBRARY.md"), encoding="utf-8").read()
    except OSError:
        return {}
    out = {}
    for line in src.split("\n"):
        m = re.match(r"^\d+\. \*\*(\w+)\*\*", line)
        if m and m.group(1) in shots:
            out[m.group(1)] = line.strip()
    return out


def build(out_dir):
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    slides = board.get("slides", [])
    meta = board.get("meta", {})
    shots = [s.get("shot") for s in slides if s.get("shot")]
    used = collections.Counter(shots)

    sys.path.insert(0, _HERE)
    import shot_director as sd
    import workshop as _ws
    # A FILM'S OWN SHOT BELONGS TO NO LIBRARY FAMILY. Counted with the library's, its family comes back None and
    # the census cannot sort None against the family letters — a crash on exactly the films that built a shot.
    film_shots = _ws.shot_names(out_dir)
    fams = collections.Counter(sd.FAMILY.get(s) or "?" for s in shots if s not in film_shots)
    built_shots = collections.Counter(s for s in shots if s in film_shots)
    fam_size = collections.Counter(sd.FAMILY.values())

    L = []
    L.append("# Critic brief — %s" % os.path.basename(os.path.abspath(out_dir)))
    L.append("")
    L.append("%d beats · %s · aspect %s · direction `%s` · audacity `%s`"
             % (len(slides), meta.get("language", "?"), meta.get("aspect", "16:9"),
                meta.get("shot_template", "-"), meta.get("audacity", "balanced")))
    L.append("")
    if str(meta.get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        L.append("> **This deck is not a `remotion` film** (`renderer` = %r). The register, family and "
                 "growth sections below are empty by construction, and the shot-tier gates no-op. Use "
                 "`design-critic` for the HTML tier." % meta.get("renderer"))
        L.append("")
    L.append("## 1 · Already decided by machine — do NOT re-judge these")
    L.append("")
    L.append("Read the verdicts; spend your pass on section 3.")
    L.append("")
    for label, script, args in [("validate", "validate.py", ()),
                                ("A/V", "check_av.py", ()),
                                ("keyframes", "keyframe_qa_remotion.py", ()),
                                # THE AUTHORITATIVE TYPE GATE GOES FIRST, AND IT WAS MISSING ENTIRELY.
                                # This brief shipped `frame_safe_qa` — the border-ink measure whose own
                                # header records it as INVERTED (it passes every genuinely-cut case and
                                # blocks every deliberate full-bleed) — and omitted `text_safe_qa`, which
                                # asks the DOM whether any TYPE is actually cut off and is what decides.
                                # Measured on the film that found this: the critic was handed a 4-error
                                # FAIL, checked all four against the pixels, and found every one was the
                                # inverted measure (a full-bleed diagonal read as 63% caption-band ink, a
                                # display word its own source documents as "cropped by the frame on
                                # purpose"). It then had to run the right gate itself. That critic caught
                                # it; the next one would have filed four revisions against frames that are
                                # correct, while nothing measured the failure that actually destroys type.
                                ("TYPE cut off (authoritative)", "text_safe_qa.py", ()),
                                ("frame-safe (ADVISORY — border ink; known inverted, see above)",
                                 "frame_safe_qa.py", ()),
                                ("proof sheet", "shot_proof.py", ()),
                                ("voice", "voice_qa.py", ())]:
        L.append("**%s**" % label)
        L.append("```")
        L.append(_run(script, out_dir, *args))
        L.append("```")
    L.append("")
    L.append("Those cover: action-safe overflow · ink in the caption band · colour outside the film's "
             "palette · a dead (narrow AND off-centre) frame · an empty frame · a register's demo default "
             "left in props · two beats on the same prop shape · a figure still moving at the frame the "
             "gate captures · A/V drift · blank keyframes · caption craft · the narration's rhythm. "
             "A finding of yours that repeats one of these is a finding the pipeline already had.")
    L.append("")
    L.append("## 2 · The film at a glance")
    L.append("")
    L.append("`_contact_sheet.png` — every beat, numbered, with its register. **Read it first.** Open a "
             "full `_keyframes/scene_NN.png` only for the beats it makes you suspicious of; a 320px cell "
             "shows composition, palette and repetition but not whether a label collides or a figure is "
             "legible.")
    L.append("")
    L.append("| beat | register | family | narration |")
    L.append("|---|---|---|---|")
    # NUMBERED BY POSITION, never by the `index` FIELD. Every board on disk writes `index` 1-BASED, and this
    # read it as 0-based and added one, so every finding named the beat AFTER the one it meant — "beat 3
    # declares a ground on CompanionCard" sends a reader to PortRail. The repo paid for this once already in
    # `contact_sheet.py`, where the same arithmetic mislabelled the sheet a critic reads.
    for _pos, s in enumerate(slides, start=1):
        b = _pos
        sh = s.get("shot") or "-"
        L.append("| %d | %s | %s | %s |" % (b, sh, "built (this film)" if sh in film_shots else sd.FAMILY.get(sh, "?"),
                                            str(s.get("narration", ""))[:60].replace("|", "/")))
    L.append("")
    L.append("## 3 · What only you can judge")
    L.append("")
    L.append("- **MEANING** — hide the caption: does the frame still carry THIS idea, and only this one?")
    L.append("- **CONTENT-FIT** — would this beat look identical on another topic with the words swapped?")
    L.append("- **FAITHFULNESS** — every on-screen number traced to that beat's `source_ref`.")
    L.append("- **REGISTER FIT** — does the register's structure carry the beat's argument, or was it the "
             "closest thing in the catalogue?")
    L.append("- **SHAPE** — the film's arc, its boldness for this audacity, its seam rhythm.")
    L.append("")
    L.append("## 4 · Facts computed for you")
    L.append("")
    rep = [(k, v) for k, v in used.items() if v > 1]
    L.append("**Register reuse** — %s" % (", ".join("%s x%d" % kv for kv in sorted(rep, key=lambda x: -x[1]))
                                          or "every beat on its own register"))
    L.append("")
    L.append("**Families** — %d of %d used: %s%s"
             % (len(fams), len(fam_size), ", ".join("%s x%d" % (f, n) for f, n in sorted(fams.items())),
                ("; and %d beat(s) on this film's own shots (%s), which belong to no library family"
                 % (sum(built_shots.values()), ", ".join(sorted(built_shots)))) if built_shots else ""))
    thin = sorted({f for f in fams if fam_size.get(f, 0) <= 2})
    if thin:
        L.append("")
        L.append("**Thin families used: %s** — each holds %s register(s) in the whole library, so there was "
                 "no room to pick a better fit inside them. If a beat needed that language and the one "
                 "register did not carry its argument, the answer was to BUILD, not to settle."
                 % (", ".join(thin), "/".join(str(fam_size[f]) for f in thin)))
    L.append("")
    fits = [(s.get("shot_fit") or {}).get("verdict") for s in slides]
    built = [i + 1 for i, s in enumerate(slides) if (s.get("shot_fit") or {}).get("verdict") == "build"]
    L.append("**Library growth** — %s"
             % ("this film built %d new register(s): beats %s" % (len(built), built) if built else
                "this film built nothing; every beat came from the existing catalogue"))
    if not any(fits):
        L.append("")
        L.append("No beat recorded a `shot_fit` judgement, so nobody asked whether the catalogue could "
                 "carry these arguments. Say so in your verdict.")
    # THE BUILT THINGS, for S15: each with its purpose and its own test, and its settled frame when one was rendered.
    bl = [e for e in meta.get("build_list") or [] if isinstance(e, dict)]
    if bl:
        L.append("")
        L.append("**Built things** — judge each on S15, against its own `means` and `accept`:")
        for e in bl:
            still = os.path.join("workshop", "_stills", "%s.png" % e.get("id"))
            L.append("- `%s` (%s in `%s`, beats %s%s) — means: %s · accept: %s%s"
                     % (e.get("id"), e.get("kind"),
                        "`, `".join(e["slot"]) if isinstance(e.get("slot"), list) else e.get("slot"), e.get("beats"),
                        ", promoted" if e.get("promoted") else "", e.get("means"), e.get("accept"),
                        " · settled frame: `%s`" % still if os.path.exists(os.path.join(out_dir, still)) else ""))
    L.append("")
    L.append("## 5 · The registers this film uses")
    L.append("")
    for shot, line in sorted(_library_entries(set(shots)).items()):
        L.append("- " + re.sub(r"^\d+\. ", "", line))
    import workshop as _ws
    film_own = _ws.shot_names(out_dir)
    missing = sorted(set(shots) - set(_library_entries(set(shots))) - film_own)
    if film_own & set(shots):
        L.append("")
        L.append("Film-local registers (its workshop — see Built things): %s" % ", ".join(sorted(film_own & set(shots))))
    if missing:
        L.append("")
        L.append("Not in the catalogue (so nothing states what they are for): %s" % ", ".join(missing))
    return "\n".join(L) + "\n"


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir = os.path.abspath(argv[0])
    try:
        import contact_sheet
        sheet, n, size = contact_sheet.build(out_dir)
        made = "%s (%dx%d, %d beats)" % (os.path.basename(sheet), size[0], size[1], n)
    except Exception as e:                                    # noqa: BLE001 — report, never mask
        made = "NOT BUILT (%s)" % e
    text = build(out_dir)
    path = os.path.join(out_dir, "_critic_brief.md")
    open(path, "w", encoding="utf-8").write(text)
    print("[critic_brief] %s  ·  contact sheet: %s" % (path, made))
    print("[critic_brief] %d lines; hand the critic this file and the contact sheet." % len(text.split("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
