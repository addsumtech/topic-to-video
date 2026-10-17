#!/usr/bin/env python3
"""Assemble everything the rendered review needs into ONE file, so its pass is spent on judgment — on both tiers.

  python3 scripts/critic_brief.py <out_dir>          # writes <out_dir>/_critic_brief.md (+ the contact sheet)
  python3 scripts/critic_brief.py <out_dir> --gates  # only the delivery gates: run, record, exit 1 on a failure

A remotion film's brief is for agents/shot-critic.md (below). An HTML-tier film's (not remotion, at least one
`type:"html"` page) is for agents/design-critic.md's delivery section, with critic-av's lens: it runs keyframe_qa
FIRST, so the filmstrips the sheet is built from show the pages as they are now, pulls one frame per beat out of
the delivered out.mp4 (`_frames/`, with its burned caption — the A/V lens's evidence), builds the sheet from the
filmstrips, records the render and lists the HTML machine verdicts, the routes and the built components. A board
with no authored page (the 原样配音 tier, or programmatic scenes only) has no ledger; its brief says so.

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

`--gates` runs the same delivery gates (critic_ledger.DELIVERY_GATES, the tier's list) and records their exit codes
against the render id WITHOUT writing a brief: the check before the review-depth question (SKILL.md 9d), and the
record a `none` answer is delivered on — `critic_ledger.py --final` refuses a render whose record is missing a gate
or holds a failure, on every path. It exits 1 when a blocking gate failed, 2 when no render could be recorded.
"""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")


class GateOutput(str):
    """A gate's printed output that also carries its EXIT CODE (`.code`: an int, or "timeout" / "not run"). The brief
    prints the text; main() records the codes in this render's history entry, which `critic_ledger.py --final` reads
    so a review PASS cannot remove NOT_DELIVERED.md from a film its gates refuse. A plain str (a test stub) carries no
    code, and nothing is recorded for it."""
    def __new__(cls, text, code):
        o = str.__new__(cls, text)
        o.code = code
        return o


def _gate_name(script, args):
    import critic_ledger as _cl
    return _cl.gate_name(script, args)


def _run(script, out_dir, *args, timeout=240):
    """Run one gate and return its output (a GateOutput carrying its exit code). A gate that hangs must not take
    the brief with it — the brief is what a reviewer waits on, and six unbounded subprocesses is six ways to wait
    forever."""
    try:
        r = subprocess.run([sys.executable, os.path.join(_HERE, script), out_dir, *args],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return GateOutput("[%s] TIMED OUT after %ds — run it yourself before trusting this brief" % (script, timeout),
                          "timeout")
    except OSError as e:
        return GateOutput("[%s] could not run: %s" % (script, e), "not run")
    return GateOutput((r.stdout or "").strip() or (r.stderr or "").strip()[:400], r.returncode)


# ── a gate already run on THIS render, with nothing it reads changed since, is not run again ──────────────────────
# The check before the review-depth question (`--gates`) runs every delivery gate, and the brief that follows on the
# same render ran them all again: a remotion film's census gates, the CJK sweep and the energy decode, two to three
# and a half minutes, re-measuring a film nobody had touched. Each run now leaves its results in GATE_RUNS with the
# render id and a fingerprint of everything the gates read; a later run on the same render with the same inputs
# prints the recorded verdict and exit code instead of re-running. What counts as an input is decided by EXCLUSION —
# the review's and the gates' own outputs (every `_`/`.`-prefixed name, the delivered files the render id already
# covers) — so a file nobody thought to list is an input, and an unexpected one costs a re-run, never a stale pass.
GATE_RUNS = "_gate_runs.json"
_CACHE = None              # main() sets {"render", "inputs", "gates": {name: {exit, blocking, output}}}
_NOT_INPUTS = {"out.mp4", "out.srt", "sample.mp4", "preview.mp4", "audition.mp3", "NOT_DELIVERED.md", "qa",
               "voice_samples"}
_REVIEW_ONLY_KEYS = ("review", "review_waiver")   # written between `--gates` and the brief; no gate reads them
_SKILL_INPUTS = (("scripts", None), (os.path.join("remotion", "src"), None), ("remotion", ".json"),
                 (os.path.join("assets", "html"), None))


def _skipped(name, film):
    """A FILM's `_`/`.` names are the gates' and the review's own outputs; the SKILL's `_` names are code
    (scripts/_common.py, _cdp.py, remotion/_ground_luma.json) — skipping them there let an edit to _common.py replay a
    gate's old PASS. The skill skips only caches."""
    if film:
        return name.startswith((".", "_"))
    return name.startswith(".") or name in ("__pycache__", "node_modules")


def _hash_tree(h, base, label, ext=None, top_skip=()):
    film = label == "film"
    for dp, dns, fns in os.walk(base):
        dns[:] = sorted(d for d in dns if not _skipped(d, film) and not (dp == base and d in top_skip))
        if ext and dp != base:
            continue                                   # ("remotion", ".json"): its top-level manifests only
        for f in sorted(fns):
            if _skipped(f, film) or (dp == base and f in top_skip) or (ext and not f.endswith(ext)) or \
                    f.endswith(".pyc"):
                continue
            path = os.path.join(dp, f)
            rel = os.path.relpath(path, base)
            if label == "film" and rel == "storyboard.json":
                try:
                    b = json.load(open(path, encoding="utf-8"))
                    meta = {k: v for k, v in (b.get("meta") or {}).items() if k not in _REVIEW_ONLY_KEYS}
                    data = json.dumps(dict(b, meta=meta), sort_keys=True, ensure_ascii=False).encode("utf-8")
                except (OSError, ValueError, AttributeError):
                    data = _read_or_marker(path)
            else:
                data = _read_or_marker(path)
            h.update(("\n%s:%s:" % (label, rel)).encode("utf-8"))
            h.update(hashlib.sha256(data).digest())


def _read_or_marker(path):
    """The file's bytes — or, for one that cannot be read (a dangling link, a permission), a marker naming why, so the
    fingerprint still changes with it and the brief does not crash before any gate runs."""
    try:
        return open(path, "rb").read()
    except OSError as e:
        return ("<unreadable: %s>" % type(e).__name__).encode()


def gate_inputs(out_dir):
    """A fingerprint of everything a delivery gate reads apart from the render itself: the film folder minus the
    review's and the gates' outputs (and the review answer, which no gate reads), plus the skill's own code."""
    h = hashlib.sha256()
    _hash_tree(h, out_dir, "film", top_skip=_NOT_INPUTS)
    root = os.path.join(_HERE, "..")
    for sub, ext in _SKILL_INPUTS:
        _hash_tree(h, os.path.join(root, sub), "skill:" + sub + (ext or ""), ext=ext)
    return h.hexdigest()


def _load_gate_runs(out_dir, rid, inputs):
    """The gate results recorded on this render with these inputs ({name: {exit, blocking, output}}), else {}."""
    try:
        rec = json.load(open(os.path.join(out_dir, GATE_RUNS), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(rec, dict) or rec.get("render") != rid or rec.get("inputs") != inputs:
        return {}
    return rec.get("gates") if isinstance(rec.get("gates"), dict) else {}


def _gate_run(script, out_dir, args=(), timeout=240):
    """Run one delivery gate — or, when main() found it recorded on this render with nothing it reads changed, hand
    back that run's verdict and exit code. Only a real exit code is kept: a timeout or a gate that could not start is
    run again next time."""
    import critic_ledger as _cl
    name = _cl.gate_name(script, args)
    cache = _CACHE
    if cache is not None and name in cache.get("hit", {}):
        g = cache["hit"][name]
        cache["gates"][name] = g
        return GateOutput("(not re-run: recorded on this render by an earlier critic_brief.py run, and nothing it "
                          "reads has changed since — this is that run's verdict)\n" + str(g.get("output", "")),
                          g.get("exit"))
    out = _run(script, out_dir, *args, timeout=timeout)
    code = getattr(out, "code", None)
    # ONLY A PASS IS KEPT. A failure can come from the environment (a browser that flaked, a missing tool), which
    # the fingerprint cannot see — replaying it would hold the film failed after the cause was fixed.
    if cache is not None and code == 0:
        cache["gates"][name] = {"exit": code, "output": str(out)}
    return out


def _save_gate_runs(out_dir):
    if _CACHE is None or not _CACHE.get("render"):
        return
    try:
        json.dump({"render": _CACHE["render"], "inputs": _CACHE["inputs"], "gates": _CACHE["gates"]},
                  open(os.path.join(out_dir, GATE_RUNS), "w", encoding="utf-8"), ensure_ascii=False)
    except OSError as e:
        print("[critic_brief] gate results not kept for reuse (%s) — the next run re-runs them" % e)


def _note(codes, script, args, out):
    """Record one gate's exit code into `codes` (when the output carries one)."""
    code = getattr(out, "code", None)
    if codes is not None and code is not None:
        codes[_gate_name(script, args)] = {"exit": code, "blocking": script not in ADVISORY_GATES}


def _gate_rows(out_dir):
    """This film's delivery gates — critic_ledger.delivery_gates, the list `--final` holds the record to."""
    import critic_ledger as _cl
    return _cl.delivery_gates(out_dir)


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


def _review_depth(meta, how, out_dir=None):
    """The `**Review depth**` line: the tier the user chose and what it means for THIS tier's critics (`how`)."""
    _rv = meta.get("review") if isinstance(meta.get("review"), dict) else {}
    _tier = str(_rv.get("tier") or "").lower()
    pre = ""
    if out_dir:
        import critic_ledger as _cl
        want, why = _cl.preselect(out_dir)
        pre = " Its pre-selected option is computed, not chosen: `%s` (%s)." % (want, why)
    text = dict(how, none="the user waived the review — no critic should be running on this film.").get(
        _tier, "NOT RECORDED — the review-depth question (SKILL.md 9d) has not been asked. Ask it before "
               "dispatching the critic; critic_ledger.py --final refuses a film with no meta.review." + pre)
    return "**Review depth: `%s`** — %s" % (_tier or "?", text)


def _caption_band_line(meta):
    """Where the burned caption sits, in pixels — H4 and keyframe_qa both say "the caption band the renderer really
    reserves", and a delivery critic had to eyeball it. The band is _caption_band.caption_band_px, the one definition
    keyframe_qa's caption-zone check and the renderer read."""
    try:
        import render as _rd
        from _caption_band import caption_band_px
        W, H = _rd._canvas(meta, meta.get("aspect") == "9:16")
        band = caption_band_px(W, H)
    except Exception as e:                                    # noqa: BLE001 — a fact for the critic, never a crash
        return "**Caption band** — could not be computed (%s); read it off the delivered frames." % e
    return ("**Caption band** — the bottom %dpx of the %dx%d frame (y ≥ %d) is where the overlay caption burns; "
            "content that reaches it is keyframe_qa's caption-zone finding, and a page that leaves it empty is "
            "doing its job." % (band, W, H, H - band))


def _load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _refs(raw):
    """[(source id, quote)] from a `source_ref` — "id#quote · id#quote", a list of those, or a bare id."""
    items = raw if isinstance(raw, list) else re.split(r"\s+·\s+", raw) if isinstance(raw, str) else []
    out = []
    for it in items:
        it = str(it).strip()
        if it:
            sid, _, quote = it.partition("#")
            out.append((sid.strip(), quote.strip()))
    return out


def _sources_lines(out_dir, n_beats):
    """WHERE EACH BEAT'S FACTS COME FROM — the faithfulness row's evidence, assembled. Both critics' methods said the
    brief carried it and neither brief did: a delivery critic on the skill's own jev-html traced every page by hand-
    grepping sources/*.txt, and found an invented ticket number and a sentence-level claim no source makes. Read from
    content_plan.json's per-beat `source_ref` (matched to the board BY POSITION — the plan does not carry the board's
    index), brief.json's evidence and sources/index.json; an older plan with no per-beat refs says so instead of
    leaving the section out."""
    plan = _load_json(os.path.join(out_dir, "content_plan.json"), {})
    beats = [b for b in (plan.get("beats") or []) if isinstance(b, dict)] if isinstance(plan, dict) else []
    index = _load_json(os.path.join(out_dir, "sources", "index.json"), {})
    index = index if isinstance(index, dict) else {}
    brief = _load_json(os.path.join(out_dir, "brief.json"), {})
    evidence = [e for e in (brief.get("evidence") or []) if isinstance(e, dict)] if isinstance(brief, dict) else []

    def name(sid):
        if sid in index:
            return "`%s`" % sid
        return "`%s` (NOT in sources/index.json)" % sid

    L = ["**Where each beat's facts come from** — the evidence for the faithfulness row. Each source's text is "
         "`sources/<id>.txt`; grep it for the quote."]
    per_beat = [(pos, _refs(b.get("source_ref"))) for pos, b in enumerate(beats, 1)]
    if any(r for _p, r in per_beat):
        if len(beats) != n_beats:
            L.append("- (content_plan.json has %d beat(s), the board %d — matched by position, so read these with "
                     "care)" % (len(beats), n_beats))
        for pos, refs in per_beat[:n_beats]:
            L.append("- beat %d: %s" % (pos, " · ".join("%s «%s»" % (name(sid), q[:70]) if q else name(sid)
                                                        for sid, q in refs)
                                        if refs else "**no source_ref** in content_plan.json — every fact on this "
                                                     "page needs one from brief.json's evidence below, or it is "
                                                     "unsourced"))
    elif beats:
        L.append("- content_plan.json records NO per-beat `source_ref` (an older plan): trace each page against "
                 "brief.json's evidence and the source texts below.")
    else:
        L.append("- no content_plan.json: trace each page against brief.json's evidence and the source texts below.")
    if evidence:
        L.append("- brief.json evidence (%d claim(s)):" % len(evidence))
        for e in evidence[:24]:
            ids = sorted({sid for sid, _q in _refs(e.get("source_ref"))})
            L.append("  - %s ← %s" % (str(e.get("claim", "")).strip()[:120], ", ".join(name(i) for i in ids) or
                                      "**no source_ref**"))
        if len(evidence) > 24:
            L.append("  - … %d more in brief.json" % (len(evidence) - 24))
    else:
        L.append("- no brief.json evidence on file — say in the H1/S3 row what you traced against.")
    files = []
    for sid, m in sorted(index.items()):
        m = m if isinstance(m, dict) else {}
        txt = os.path.join(out_dir, "sources", "%s.txt" % sid)
        files.append("`%s` %s (%s%s)%s" % (sid, str(m.get("title") or "")[:60], m.get("tier") or "?",
                                           ", as of %s" % m["as_of"] if m.get("as_of") else "",
                                           "" if os.path.exists(txt) else " — **sources/%s.txt is missing**" % sid))
    L.append("- sources on file: %s" % ("; ".join(files) if files else "**none** (no sources/index.json)"))
    return L


def _waiver_lines(out_dir):
    """"Waivers to confirm": each machine-gate finding the board waived, with its stated reason and the dimension
    that owns it. A waiver does not raise the review depth; the critic confirms each in a `waivers` ledger row."""
    import critic_ledger as _cl
    waived = _cl.gate_waivers(out_dir)
    if not waived:
        return ["**Waivers to confirm** — none: the board waives no machine gate's finding."]
    tier = _cl.film_tier(out_dir) or "remotion"
    owners = _cl.waiver_owners(*_cl.SERIES[tier][:2])
    L = ["**Waivers to confirm** — the board waives these machine-gate findings. For each, record a ledger "
         "`waivers` row `{key, holds: true|false, evidence}`: is the stated reason TRUE of the rendered film? "
         "`holds: false` means the finding stands and its owning dimension FAILs."]
    for key, reason in waived:
        L.append("- `meta.%s` (owner: %s) — reason given: %s" % (key, owners.get(key, "NONE DECLARED in the critic's "
                                                                       "file"), reason[:600]))
    return L


def build(out_dir, ran=None, codes=None):
    """The brief's text. `ran` = {script: output} for gates main() already ran (the HTML tier runs keyframe_qa
    before the sheet is built, and must not run it twice); `codes`, when given, collects every gate's exit code."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    sys.path.insert(0, _HERE)
    import critic_ledger as _cl
    tier = _cl.film_tier(out_dir)
    if tier == "html":
        return _build_html(out_dir, board, ran or {}, codes)
    if tier is None:
        return _build_no_pages(out_dir, board)
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
    # THE DEPTH THE USER CHOSE decides the shape of this pass (SKILL.md, the review-depth question). The floors
    # do not move with it: every ledger row, cited evidence, an independent reviewer.
    L.append(_review_depth(meta, {
        "fast": "ONE combined pass carrying the A/V lens too (agents/critic-av.md), ONE round. Fill every "
                "ledger row — a PASS row is one line, its verdict and the frame it rests on (`_contact_sheet.png` "
                "for a whole-film dimension); spend the words on the FAILs. Only your TOP issues by impact are "
                "FAIL rows, each with a FIX; an observation below the top goes in that dimension's `note` on a "
                "pass row, never as a FAIL. A FAIL left "
                "when the round is spent goes back to the USER (one more round, or accept as-is) — you never "
                "decline one, and a faithfulness/sourcing FAIL is always fixed.",
        "standard": "this critic plus agents/critic-av.md, up to TWO rounds; round 2 is a full fresh review. "
                    "A FAIL left after round 2 goes back to the USER, as on fast.",
        "thorough": "the full loop: REVISE → fix → re-render → fresh independent review, until PASS."}, out_dir))
    L.append("")
    L.append("## 1 · Already decided by machine — do NOT re-judge these")
    L.append("")
    L.append("Read the verdicts; spend your pass on section 3.")
    L.append("")
    for label, script, args, timeout, _blocking in _gate_rows(out_dir):
        L.append("**%s**" % label)
        L.append("```")
        out = _gate_run(script, out_dir, args, timeout=timeout)
        _note(codes, script, args, out)
        L.append(out)
        L.append("```")
    L.append("")
    L.append("Those cover: action-safe overflow · ink in the caption band · colour outside the film's "
             "palette · a dead (narrow AND off-centre) frame · an empty frame · a register's demo default "
             "left in props · two beats on the same prop shape · a figure still moving at the frame the "
             "gate captures · A/V drift · blank keyframes · caption craft · the narration's rhythm · CJK type "
             "piled into itself · a film that does not move or has no light (film_energy) · a camera that "
             "vibrates instead of travelling (shake) · flat pacing · a concept used before it is taught. "
             "A finding of yours that repeats one of these is a finding the pipeline already had. A WAIVED "
             "film-energy finding is the exception: whether its stated reason is true is yours (the waiver rows).")
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
    L.append("- **FAITHFULNESS** — every on-screen number traced to its source (below: where each beat's facts "
             "come from).")
    L.append("- **REGISTER FIT** — does the register's structure carry the beat's argument, or was it the "
             "closest thing in the catalogue?")
    L.append("- **SHAPE** — the film's arc, its boldness for this audacity, its seam rhythm.")
    L.append("")
    L.append("## 4 · Facts computed for you")
    L.append("")
    L.extend(_sources_lines(out_dir, len(slides)))
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
    # WHAT was built is the build list's to say: a beat that holds a built OBJECT on a library stage is a build
    # beat too, so counting build beats as "new registers" would tell the critic that a film which drew one
    # object for three beats had grown the library by three registers
    kinds = collections.Counter(e.get("kind") for e in meta.get("build_list") or [] if isinstance(e, dict))
    if built and kinds:
        what = " and ".join("%d %s(s)" % (kinds[k], k) for k in ("shot", "object") if kinds.get(k))
        growth = "this film built %s, used on beats %s" % (what, built)
    elif built:
        growth = "this film built %d new register(s): beats %s" % (len(built), built)
    else:
        growth = "this film built nothing; every beat came from the existing catalogue"
    L.append("**Library growth** — %s" % growth)
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
    # THE ROUTES TO CONFIRM (S14): what validate.py credits as adapted or built, from the board. The critic says,
    # per beat, whether that route is VISIBLE in the frame — a ledger `routes` row each (critic_ledger.py).
    try:
        import validate as _v
        _kept = _v.design_first_keep(meta, slides, "remotion", out_dir)[0]
        _routes = [(n, r, w) for n, r, w in _v.design_routes(meta, slides, out_dir)
                   if r in ("adapted", "built") and n not in _kept]
    except Exception as e:                                    # noqa: BLE001 — report, never mask
        _routes, _rerr = None, e
    L.append("")
    _keep = _cl.kept_line(out_dir)
    if _keep:
        L.append("**%s.** Judge those beats as they are, and say so; every other beat is held to design-first." % _keep)
        L.append("")
    if _routes is None:
        L.append("**Routes to confirm (S14)** — could not be computed (%s); run scripts/validate.py" % _rerr)
    elif _routes:
        L.append("**Routes to confirm (S14)** — validate.py credits these beats; for each, record a ledger "
                 "`routes` row `{beat, route, visible: true|false, evidence}` saying whether the route is VISIBLE "
                 "in the rendered frame. A route you cannot see fails S14.")
        by_pos = {i: sl for i, sl in enumerate(slides, 1)}
        for num, route, why in _routes:
            sl = next((x for i, x in by_pos.items() if x.get("index", i) == num), {})
            fit = sl.get("shot_fit") if isinstance(sl.get("shot_fit"), dict) else {}
            ad = sl.get("shot_adaptation") if isinstance(sl.get("shot_adaptation"), dict) else {}
            ch = ad.get("changes") if isinstance(ad.get("changes"), list) else []
            L.append("- beat %s · %s%s · ideal: %s%s" % (
                num, route.upper(), (" (%s)" % why) if why else "", fit.get("ideal") or "-",
                (" · changes: " + "; ".join("%s — %s" % (c.get("aspect"), c.get("what"))
                                            for c in ch if isinstance(c, dict))) if ch else ""))
    L.append("")
    L.extend(_waiver_lines(out_dir))
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


# gates whose findings are signals, never a refusal: voice_qa always exits 0 by design; frame_safe_qa's border-ink
# measure is known to be inverted (critic_ledger.DELIVERY_GATES says why). Recorded, but `blocking: false`. Derived
# from that list, so a gate cannot be advisory here and blocking at --final.
def _advisory():
    import critic_ledger as _cl
    return {s for rows in _cl.DELIVERY_GATES.values() for _l, s, _a, _t, blocking, _ap in rows if not blocking}


ADVISORY_GATES = _advisory()
FRAMES = "_frames"


def _clear_frames(out_dir):
    fdir = os.path.join(out_dir, FRAMES)
    for f in (os.listdir(fdir) if os.path.isdir(fdir) else []):
        if re.match(r"scene_\d+\.png$", f):
            os.remove(os.path.join(fdir, f))


# ── keyframe_qa only when its input changed ──────────────────────────────────────────────────────────────────────
# Re-shooting every page on every brief costs minutes on a long film, and it exposes the review to a page that does
# not render byte-identically twice: a sheet that differs on an UNCHANGED film gives it a new render id, and a new
# render id is a new review round. So the brief re-runs keyframe_qa only when what it shoots changed — compared by
# CONTENT, not by date (dates are what a copy, a clone or an unzip resets): the pages, the film's theme and motif
# sheets, its workshop components, the skill's own page stylesheets and scripts, the cue timings the sweep follows,
# keyframe_qa itself, and the storyboard minus the keys the review and the user's decisions write (meta.review,
# meta.*_waiver, meta.design_first, meta.script_review). Missing strips, or no record of the last run, re-run it.
KFQA_RECORD = os.path.join("_keyframes", ".keyframe_qa_last.json")
_REVIEW_KEYS = ("review", "design_first", "script_review")


def _sha_file(path):
    import hashlib
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return None


def keyframe_inputs(out_dir):
    """sha256 over everything keyframe_qa's strips are drawn from (see above)."""
    import glob
    import hashlib
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = dict(board.get("meta") or {})
    for k in list(meta):
        if k in _REVIEW_KEYS or (isinstance(k, str) and k.endswith("_waiver")):
            meta.pop(k)
    h = hashlib.sha256(json.dumps(dict(board, meta=meta), sort_keys=True, ensure_ascii=False).encode("utf-8"))
    files = set()
    for s in board.get("slides") or []:
        rel = (s.get("props") or {}).get("html") if isinstance(s, dict) and isinstance(s.get("props"), dict) else None
        if isinstance(rel, str) and rel:
            files.add(os.path.join(out_dir, rel))
    for pat in ("theme.css", "motifs.css", "workshop/html/*", "audio/*.words.json"):
        files.update(glob.glob(os.path.join(out_dir, pat)))
    files.update(glob.glob(os.path.join(_HERE, "..", "assets", "html", "*.css")))
    files.update(glob.glob(os.path.join(_HERE, "..", "assets", "html", "*.js")))
    files.add(os.path.join(_HERE, "keyframe_qa.py"))
    for f in sorted(os.path.abspath(x) for x in files):
        h.update(("\n%s:%s" % (os.path.relpath(f, out_dir) if f.startswith(os.path.abspath(out_dir))
                                else os.path.basename(f), _sha_file(f))).encode("utf-8"))
    return h.hexdigest()


def keyframe_qa(out_dir):
    """keyframe_qa's output for the brief (a GateOutput) — re-run only when its inputs changed or a page's strip is
    missing; otherwise the last run's verdict and exit code, said to be that run's."""
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    need = [s.get("index", pos) for pos, s in enumerate(board.get("slides") or [], 1)
            if isinstance(s, dict) and s.get("type") == "html"]
    strips = all(os.path.exists(os.path.join(out_dir, "_keyframes", "scene_%02d.png" % n)) for n in need)
    fp = keyframe_inputs(out_dir)
    try:
        last = json.load(open(os.path.join(out_dir, KFQA_RECORD), encoding="utf-8"))
    except (OSError, ValueError):
        last = {}
    if strips and isinstance(last, dict) and last.get("inputs") == fp and "exit" in last:
        return GateOutput("(not re-run: no page, theme, motif, component, cue timing, stylesheet or storyboard input "
                          "changed since it last ran — this is that run's verdict)\n" + str(last.get("output", "")),
                          last.get("exit")), False
    out = _run("keyframe_qa.py", out_dir, timeout=900)
    code = getattr(out, "code", None)
    if code is not None:
        os.makedirs(os.path.join(out_dir, "_keyframes"), exist_ok=True)
        json.dump({"inputs": fp, "exit": code, "output": str(out)},
                  open(os.path.join(out_dir, KFQA_RECORD), "w", encoding="utf-8"), ensure_ascii=False)
    return out, True


def html_frames(out_dir, at=0.9):
    """One frame per beat of the DELIVERED out.mp4 — `_frames/scene_NN.png` (NN = the beat's `index`, the HTML
    keyframes' numbering), at `at` of the beat — WITH its burned caption, which the page keyframes never carry. The
    A/V lens (critic-av R7: clipped, overlapping, mis-timed or tofu captions) has nothing to read without it.
    render.py concatenates one clip of exactly `duration` seconds per beat, so a beat's window in out.mp4 is the
    running sum of the board's durations (no seam overlap, unlike remotion). Returns [(number, path)]; old frames
    are cleared first so a beat that no longer exists cannot be cited."""
    # CLEARED FIRST, before any return: frames left from an earlier render would otherwise be counted by the brief
    # ("6 delivered frames") and cited by the critic as THIS film when there is no out.mp4 to pull from at all
    _clear_frames(out_dir)
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.isfile(mp4):
        return []
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    fdir = os.path.join(out_dir, FRAMES)
    os.makedirs(fdir, exist_ok=True)
    out, t = [], 0.0
    for pos, s in enumerate(board.get("slides") or [], start=1):
        dur = s.get("duration") if isinstance(s, dict) else None
        if not isinstance(dur, (int, float)) or dur <= 0:
            raise RuntimeError("beat %s has no duration — out.mp4's beat windows cannot be located (run tts.py)"
                               % pos)
        num = s.get("index", pos)
        png = os.path.join(fdir, "scene_%02d.png" % num)
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % (t + dur * at), "-i", mp4,
                            "-vframes", "1", png], capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(png):
            raise RuntimeError("ffmpeg could not pull beat %s from out.mp4: %s" % (num, (r.stderr or "").strip()[:200]))
        out.append((num, png))
        t += dur
    return out


def _build_html(out_dir, board, ran, codes=None):
    """The HTML tier's brief, for agents/design-critic.md's delivery section (H-dimensions) + critic-av's lens."""
    slides = [x for x in board.get("slides") or [] if isinstance(x, dict)]
    meta = board.get("meta") if isinstance(board.get("meta"), dict) else {}
    L = ["# Critic brief — %s" % os.path.basename(os.path.abspath(out_dir)), ""]
    L.append("%d beats · %s · aspect %s · HTML tier — review with `agents/design-critic.md` (\"Rendered review — "
             "the delivery ledger\", the H-dimensions) · audacity `%s`"
             % (len(slides), meta.get("language", "?"), meta.get("aspect", "16:9"), meta.get("audacity", "balanced")))
    L.append("")
    L.append(_review_depth(meta, {
        "fast": "ONE pass by agents/design-critic.md's delivery section, carrying agents/critic-av.md's lens (H7), "
                "ONE round. Fill every ledger row — a PASS row is one line, its verdict and the frame it rests on "
                "(`_contact_sheet.png` for a whole-film dimension); spend the words on the FAILs. Only your TOP "
                "issues by impact are FAIL rows, each with a FIX; an "
                "observation below the top goes in that dimension's `note` on a pass row, never as a FAIL. A FAIL "
                "left when the round is spent goes back to the USER (one more round, or accept as-is) — you never "
                "decline one, and a faithfulness/sourcing FAIL (H1) is always fixed.",
        "standard": "agents/design-critic.md with agents/critic-av.md beside it (its findings are filed under H7), "
                    "up to TWO rounds; round 2 is a full fresh review. A FAIL left after round 2 goes back to the "
                    "USER, as on fast.",
        "thorough": "design-critic + critic-av in the full loop: REVISE → fix → re-render → fresh independent "
                    "review, until PASS."}, out_dir))
    L.append("")
    L.append("## 1 · Already decided by machine — do NOT re-judge these")
    L.append("")
    L.append("Read the verdicts; spend your pass on section 3.")
    L.append("")
    for label, script, args, timeout, _blocking in _gate_rows(out_dir):
        L.append("**%s**" % label)
        L.append("```")
        out = ran[script] if script in ran else _gate_run(script, out_dir, args, timeout=timeout)
        _note(codes, script, args, out)
        L.append(out)
        L.append("```")
    L.append("")
    L.append("Those cover: a missing page/asset/audio · the design-first floor (built + bespoke pages ≥ half) · "
             "uncued multi-point pages · a blank page · content overflowing the canvas or resting in the caption "
             "band · type stepping a pixel at a time while it moves · text landing late against its spoken word · "
             "A/V drift and non-uniform clip rates · flat pacing · a concept used before it is taught · the "
             "narration's rhythm. A finding of yours that repeats one of these is a finding the pipeline already had.")
    L.append("")
    L.append("## 2 · The film at a glance")
    L.append("")
    L.append("`_contact_sheet.png` — every page's FILMSTRIP, numbered, labelled with its design route: five tiles = "
             "the page at 0/25/50/75/100% of its beat (keyframe_qa's default, as this brief runs it) on the timeline that ships (right tile = the beat's END); the "
             "SETTLED frame a viewer holds is `_frames/scene_NN.png` (90% of the beat, from out.mp4) — where the two "
             "disagree, something lands in the beat's last tenth (H6). **Read it first.** Open a full "
             "`_keyframes/scene_NN.png` only for the pages it makes you suspicious of.")
    L.append("")
    L.append(_caption_band_line(meta))
    frames = sorted(f for f in os.listdir(os.path.join(out_dir, FRAMES)) if re.match(r"scene_\d+\.png$", f)) \
        if os.path.isdir(os.path.join(out_dir, FRAMES)) else []
    L.append("")
    L.append(("`%s/scene_NN.png` — each beat as DELIVERED (%d frame(s), from `out.mp4` at 90%% of the beat, with its "
              "burned caption): the evidence for H7." % (FRAMES, len(frames))) if frames else
             "**No `%s/` frames** — `out.mp4` is missing or could not be read, so nothing shows the burned "
             "captions: H7 cannot be judged until the film is rendered and this brief re-run." % FRAMES)
    L.append("")
    import validate as _v
    try:
        routes = {num: (r, w, rel) for num, r, w, rel in _v.html_design_routes(meta, slides, out_dir)}
        rerr = None
    except Exception as e:                                    # noqa: BLE001 — report, never mask
        routes, rerr = {}, e
    kdir = os.path.join(out_dir, "_keyframes")
    L.append("| beat | type | route | page | narration |")
    L.append("|---|---|---|---|---|")
    no_strip = []
    for pos, s in enumerate(slides, start=1):
        num = s.get("index", pos)
        r, _w, rel = routes.get(num, ("-", "", None))
        if not os.path.exists(os.path.join(kdir, "scene_%02d.png" % num)):
            no_strip.append(str(num))
        L.append("| %s | %s | %s | %s | %s |" % (num, s.get("type", "slide"), str(r).upper(), rel or "-",
                                               str(s.get("narration", ""))[:60].replace("|", "/")))
    if no_strip:
        L.append("")
        L.append("Beats with no filmstrip (not an HTML page, or keyframe_qa could not shoot it): %s — judge them "
                 "from `%s/`." % (", ".join(no_strip), FRAMES))
    L.append("")
    L.append("## 3 · What only you can judge")
    L.append("")
    L.append("The H-dimensions in agents/design-critic.md, one ledger row each (`python3 scripts/critic_ledger.py "
             "<out_dir> --emit-template`). The half no script can do:")
    L.append("")
    L.append("- **FAITHFULNESS (H1, hard gate)** — every number, name, quote and photograph on a page, and every "
             "factual claim the voice makes, traced to its source (section 4: where each beat's facts come from).")
    L.append("- **MEANING (H2)** — hide the caption: does the page still carry THIS idea, and only this one?")
    L.append("- **FORM FIT + VARIETY (H3)**, **FRAME-CRAFT (H4)**, **REGISTER/STYLE/COLOUR (H5)**, **MOTION (H6)** "
             "— judged on the strips.")
    L.append("- **A/V + BURNED CAPTIONS (H7)** — on the delivered frames; check_av's verdict is above.")
    L.append("- **ROUTES (H8)** and **BUILT THINGS (H9)** — below.")
    L.append("")
    L.append("## 4 · Facts computed for you")
    L.append("")
    L.extend(_sources_lines(out_dir, len(slides)))
    L.append("")
    import critic_ledger as _cl
    kept = _v.design_first_keep(meta, slides, "html", out_dir)[0]
    credited = [(n, r, w, rel) for n, (r, w, rel) in routes.items() if r in ("built", "bespoke") and n not in kept]
    keep = _cl.kept_line(out_dir)
    if keep:
        L.append("**%s.** Judge those pages as they are, and say so; every other page is held to design-first." % keep)
        L.append("")
    if rerr is not None:
        L.append("**Routes to confirm (H8)** — could not be computed (%s); run scripts/validate.py" % rerr)
    elif credited:
        L.append("**Routes to confirm (H8)** — validate.py credits these pages; for each, record a ledger `routes` "
                 "row `{beat, route, visible: true|false, evidence}` saying whether the route is VISIBLE in the "
                 "rendered frame. A route you cannot see fails H8.")
        by_num = {x.get("index", i): x for i, x in enumerate(slides, 1)}
        for num, route, why, rel in credited:
            fit = by_num.get(num, {}).get("shot_fit")
            fit = fit if isinstance(fit, dict) else {}
            L.append("- beat %s · %s (%s) · `%s` · ideal: %s" % (num, route.upper(), why, rel or "-",
                                                                fit.get("ideal") or "-"))
    else:
        L.append("**Routes to confirm (H8)** — validate.py credits no page as BUILT or BESPOKE: every page is a "
                 "stock archetype or exempt. That is itself the design-first floor's finding (section 1).")
    L.append("")
    L.extend(_waiver_lines(out_dir))
    bl = [e for e in meta.get("build_list") or [] if isinstance(e, dict) and e.get("kind") == "component"]
    L.append("")
    if bl:
        L.append("**Built things** — judge each on H9, against its own `means` and `accept`:")
        for e in bl:
            still = os.path.join("workshop", "_stills", "%s.png" % e.get("id"))
            L.append("- `%s` (component, beats %s%s) — means: %s · accept: %s%s"
                     % (e.get("id"), e.get("beats"), ", promoted" if e.get("promoted") else "", e.get("means"),
                        e.get("accept"),
                        " · settled frame: `%s`" % still if os.path.exists(os.path.join(out_dir, still)) else ""))
    else:
        L.append("**Built things** — this film built no component (no `kind: \"component\"` entry in "
                 "meta.build_list): H9 is `na`, and say so.")
    return "\n".join(L) + "\n"


def _build_no_pages(out_dir, board):
    """A board with no authored page: no design to judge and no keyframe to pin, so no ledger — critic-av alone."""
    meta = board.get("meta") if isinstance(board.get("meta"), dict) else {}
    L = ["# Critic brief — %s" % os.path.basename(os.path.abspath(out_dir)), "",
         "> **No authored page on this film** (`renderer` = %r, no `type:\"html\"` beat) — the 原样配音 tier or a "
         "board of programmatic scenes. There is no design to judge and no keyframe to pin, so there is NO review "
         "ledger here (`critic_ledger.py` says it does not apply). The review at the chosen depth is "
         "`agents/critic-av.md` on `out.mp4`." % meta.get("renderer"), ""]
    for label, script in (("A/V", "check_av.py"), ("validate", "validate.py")):
        L += ["**%s**" % label, "```", _run(script, out_dir), "```"]
    return "\n".join(L) + "\n"


def _failure_excerpt(out, n=6):
    """The lines of a failed gate's output that say WHY: its ERROR / FAIL lines (first n), then its last line, which
    every gate here spends on its verdict. The plain tail was validate.py's coverage table — eight lines on which
    branches were taken, and not one of the ERRORs that failed the film."""
    lines = [x for x in str(out).strip().splitlines() if x.strip()]
    why = [x for x in lines if re.search(r"\bERROR\b|\bFAIL(ED)?\b", x)]
    if not why:
        return lines[-8:]
    picked = why[:n]
    if lines and lines[-1] not in picked:
        picked.append(lines[-1])
    return picked


def _gates_only(out_dir, tier, ran, sheet_ok, made):
    """`--gates`: run this film's delivery gates, record their exit codes against the render id WITHOUT counting a
    review round (the brief that follows on the same render does), print one line per gate and the tail of every
    blocking failure. Exit 1 on a blocking failure; 2 when nothing could be recorded (no contact sheet), since
    `--final` would then refuse the film for want of a record; 0 otherwise."""
    import critic_ledger as _cl
    rows = _gate_rows(out_dir) if tier else [("A/V", "check_av.py", (), 240, True),
                                            ("validate", "validate.py", (), 240, True)]
    codes, bad = {}, []
    for label, script, args, timeout, blocking in rows:
        out = ran[script] if (script in ran and not args) else _gate_run(script, out_dir, args, timeout=timeout)
        _note(codes, script, args, out)
        code = getattr(out, "code", None)
        name = _cl.gate_name(script, args)
        verdict = "ok" if code == 0 else ("advisory (exit %s)" % code if not blocking else "FAIL (exit %s)" % code)
        print("[critic_brief] %-26s %s" % (name, verdict))
        if blocking and code != 0:
            bad.append(name)
            for line in _failure_excerpt(out):
                print("    | " + line[:220])
    if tier is None:
        print("[critic_brief] no authored page — nothing to record (this tier has no review ledger)")
        return 1 if bad else 0
    if not sheet_ok:
        print("[critic_brief] gate results NOT recorded: the contact sheet was not built (%s), so there is no render "
              "id to record them against — fix the keyframes and re-run" % made)
        return 2
    try:
        rid = _cl.record_render(out_dir, gates=codes, review_round=False)
    except Exception as e:                                    # noqa: BLE001 — report, never mask
        print("[critic_brief] gate results NOT recorded (%s)" % e)
        return 2
    print("[critic_brief] %s  %d gate(s) recorded for render %s; %d blocking failure(s)%s"
          % ("FAIL" if bad else "OK", len(codes), (rid or "?")[:12], len(bad),
             (": " + ", ".join(bad)) if bad else ""))
    return 1 if bad else 0


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir = os.path.abspath(argv[0])
    gates_only = "--gates" in argv[1:]
    import critic_ledger as _cl
    tier = _cl.film_tier(out_dir)
    ran = {}
    if tier == "html":
        # THE FILMSTRIPS FIRST: when keyframe_qa re-shoots the pages, the sheet built next shows them as they are now
        # — a sheet built BEFORE it would be older than its keyframes, which critic_ledger refuses
        ran["keyframe_qa.py"], fresh = keyframe_qa(out_dir)
        print("[critic_brief] keyframe_qa %s" % ("re-run: its inputs changed (or no strips / no record)" if fresh else
                                                 "NOT re-run: none of its inputs changed since its last run"))
        try:
            if not gates_only:                                # --gates: the frames are the critic's evidence
                print("[critic_brief] %d delivered frame(s) -> %s/" % (len(html_frames(out_dir)), FRAMES))
        except Exception as e:                                # noqa: BLE001 — report, never mask
            # NONE rather than some: a partial set would let the brief say "N frames" and the critic cite them
            # as the delivered film, while the beats after the failure were never pulled
            _clear_frames(out_dir)
            print("[critic_brief] delivered frames NOT pulled (%s) — none are left in %s/" % (e, FRAMES))
    codes, sheet_ok = {}, False
    if tier is None:
        made = "not built — this film has no authored page (no keyframes, no ledger)"
    else:
        try:
            import contact_sheet
            sheet, n, size = contact_sheet.build(out_dir)
            made = "%s (%dx%d, %d beats)" % (os.path.basename(sheet), size[0], size[1], n)
            sheet_ok = True
        except (Exception, SystemExit) as e:                  # noqa: BLE001 — contact_sheet exits on no keyframes
            # AN OLD SHEET IS NOT THIS FILM. Left in place it would anchor the render id and every pin to a picture
            # the current keyframes no longer show; removed, critic_ledger says plainly that there is no sheet.
            old = os.path.join(out_dir, _cl.CONTACT_SHEET)
            if os.path.exists(old):
                os.remove(old)
            made = "NOT BUILT (%s) — any older sheet was removed" % e
    global _CACHE
    if sheet_ok:
        rid, inputs = _cl.render_id(out_dir), gate_inputs(out_dir)
        _CACHE = {"render": rid, "inputs": inputs, "gates": {},
                  "hit": {k: g for k, g in _load_gate_runs(out_dir, rid, inputs).items()
                          if isinstance(g, dict) and g.get("exit") == 0}}     # a recorded failure is re-run
        if _CACHE["hit"]:
            print("[critic_brief] %d gate result(s) recorded on this render with unchanged inputs — reused, not re-run"
                  % len(_CACHE["hit"]))
    try:
        if gates_only:
            return _gates_only(out_dir, tier, ran, sheet_ok, made)
        text = build(out_dir, ran, codes)
    finally:
        _save_gate_runs(out_dir)
        _CACHE = None
    if sheet_ok:
        try:
            _cl.record_render(out_dir, gates=codes)   # the render, and the exit code of every gate run on it
        except Exception as e:                  # noqa: BLE001 — report, never mask
            print("[critic_brief] render history NOT recorded (%s)" % e)
    elif tier is not None:
        print("[critic_brief] render NOT recorded: the contact sheet was not built, so there is no render id to "
              "record — fix the keyframes and re-run this")
    path = os.path.join(out_dir, "_critic_brief.md")
    open(path, "w", encoding="utf-8").write(text)
    print("[critic_brief] %s  ·  contact sheet: %s" % (path, made))
    print("[critic_brief] %d lines; hand the critic this file and the contact sheet." % len(text.split("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
