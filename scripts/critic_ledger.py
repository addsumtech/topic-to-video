#!/usr/bin/env python3
"""The shot-critic's per-dimension VERDICT LEDGER — the backstop that makes "silence is not consent" real.

    python3 scripts/critic_ledger.py <out_dir> --emit-template   # skeleton with every dimension listed
    python3 scripts/critic_ledger.py <out_dir>                   # validate a filled ledger
    python3 scripts/critic_ledger.py <out_dir> --final           # ...as the DELIVERY gate

WHY THIS FILE EXISTS. The critic's Output asked it to report "each flagged scene". A dimension it never
looked at and a dimension it checked and found clean produced the SAME artifact: nothing. The file even said
"silence is not consent" — as prose, addressed to the one party who cannot be audited by it. Every review
this skill has ever run was therefore unfalsifiable on its unflagged half, which is most of it.

A ledger inverts that. Every dimension must be named with a verdict and the evidence it rests on, so an
unexamined dimension is a MISSING ROW rather than an absence of complaint, and a missing row is a failed run.
This is what turns 13 rules from doctrine into something a later reader can check.

TWO THINGS IT REFUSES, both learned the expensive way:

* A BARE verdict. Every pass/fail must cite evidence that exists — a keyframe path under out_dir, or a line
  of the brief. "S4 pass" with nothing behind it is the same unfalsifiable claim in a machine-readable coat.
* A ledger written WITHOUT the artifact. `contact_sheet_sha256` must match the film's actual contact sheet,
  so a ledger cannot be authored from memory of an earlier render, or from a description of one.

AND, for `--final`, a ledger whose reviewer was the film's own maker. video-shotcraft states the reason
better than I would: the maker has confirmation bias about their own output, so the first review can never be
the one handed to the user. This session supplied the proof — a change was landed, measured at 0.63% ink,
and the number that showed it had NOT worked was written into the code as its motivation. A reviewer holding
no memory of intending it reads that frame as a blank frame, which is what it was.

AND A THIRD STATE, BECAUSE "REVIEWED" AND "NOT REVIEWED" ARE NOT THE ONLY TRUTHS. A user who has watched
the film and judged it finished may waive the critic — `meta.review_waiver` in storyboard.json. That is a
DECISION, recorded where decisions live, and it is not a PASS: the film ships marked UNREVIEWED, and this
gate says so on every run rather than falling silent. Three properties make it safe to have:

* It is the USER's, not the maker's. Nothing in this pipeline may author it on its own behalf; the reason
  string is the user's own words, and an empty one is refused.
* It EXPIRES WITH THE RENDER. The waiver pins the contact sheet's sha256, so it covers the film the user
  actually looked at. Re-render — change one beat, one colour, one line of narration — and the sha moves and
  the waiver no longer applies. This is the property that matters: "the user said fine once" must not become
  a standing licence over everything changed afterwards.
* It waives THIS review only. `check_av`, `keyframe_qa_remotion`, `text_safe_qa`, `cjk_type_qa`,
  `film_energy_qa`, `shake_qa` and `validate.py` are untouched and still gate delivery. A waiver is a
  judgement about taste, never about whether the file plays.

The dimension list is PARSED from agents/shot-critic.md. Restating it here is how this repo's caption band
became four disagreeing copies; a new dimension must be required by this gate the moment it is written down.
"""
import hashlib
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CRITIC = os.path.join(_ROOT, "agents", "shot-critic.md")
# The SECOND body of case law: rules for whoever edits the library, in the same form and parsed by
# the same two functions. It is listed here so the precedent-resolution test walks it too — a rule
# whose precedent nobody resolves is a rule that can cite an invented incident.
_CASE_LAW = os.path.join(_ROOT, "references", "engineering-case-law.md")
CASE_LAW_FILES = ((_CRITIC, "S"), (_CASE_LAW, "E"))

LEDGER_NAME = "_critic_ledger.json"
CONTACT_SHEET = "_contact_sheet.png"
VERDICTS = ("pass", "fail", "na")


def dimensions(path=None, prefix="S"):
    """Every rule the file declares, as [(id, title)] — parsed from that file, never listed here.

    `prefix` selects the numbering series: "S" for the critic's visual dimensions, "E" for the engineering
    case law. Both files carry the same three-part form (rule / precedent / self-check), so both are read
    by the same parser rather than by a second copy of it."""
    src = open(path or _CRITIC, encoding="utf-8").read()
    found = re.findall(r"^\*\*(%s\d+)\s*·\s*([^.*]+)" % prefix, src, re.M)
    if not found:
        raise RuntimeError(
            "no `**Sn · ...**` dimension headings found in %s — this gate requires one row per dimension and "
            "reads the list from there; if the heading format changed, update scripts/critic_ledger.py in the "
            "same change." % (path or _CRITIC))
    seen, out = set(), []
    for sid, title in found:
        if sid in seen:
            continue
        seen.add(sid)
        out.append((sid, title.strip()))
    # Numeric order, not document order — the file currently declares S8 before S7, and a ledger that reads
    # S1..S13 in order is far easier to check for a hole than one that mirrors an editing accident.
    return sorted(out, key=lambda p: int(p[0][1:]))


def precedents(path=None, prefix="S"):
    """{rule id: precedent commit hash} — a rule may instead declare itself DOCTRINE (value None)."""
    src = open(path or _CRITIC, encoding="utf-8").read()
    out = {}
    for sid, body in re.findall(r"^\*\*(%s\d+)\s*·(.*?)(?=^\*\*%s\d+\s*·|\Z)" % (prefix, prefix),
                                src, re.M | re.S):
        m = re.search(r"\*\*Precedent\s*—\s*`([0-9a-f]{7,40})`", body)
        if m:
            out[sid] = m.group(1)
        elif re.search(r"\*\*Precedent\s*—\s*none on record\b", body):
            out[sid] = None
    return out


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def template(out_dir):
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    return {
        # EMPTY on purpose. Pre-filling "independent" would answer, on the reviewer's behalf, the one
        # question this gate exists to ask — and make the lazy path the untrue one.
        "reviewer": "",
        "_reviewer_help": "independent = a fresh subagent given only <out_dir>; in-context = the film's own "
                          "maker (allowed for an interim pass, REFUSED by --final)",
        "contact_sheet_sha256": sha256_of(sheet) if os.path.exists(sheet) else "",
        "verdict": "REVISE",
        "rows": [
            {"id": sid, "verdict": "", "evidence": "", "note": "", "fix": "", "_dimension": title}
            for sid, title in dimensions()
        ],
    }


def coverage(out_dir):
    """How much of the critic's declared universe this ledger actually JUDGED.

    Under a user waiver there is no ledger and nothing was judged — which this reports as zero of N, not as
    a pile of NO ROW findings. "Nobody looked, by the user's decision" is a different fact from "the review
    forgot eleven dimensions", and printing the second for the first would train a reader to scroll past it.

    A missing row is already a refusal. The quieter hole is a ledger that is perfectly well formed and
    judges almost nothing: `na` is a legitimate verdict (a dimension can genuinely not apply) and it
    carries a reason, but thirteen of them still print `0 error(s)` and read exactly like thirteen looked-at
    dimensions. The headline now states the split, so "the review passed" cannot be read off a review that
    declined most of its own subject.
    """
    # A waiver — valid or BROKEN — already explains why there is no ledger, so the per-dimension list is
    # suppressed either way. Printing fourteen NO ROW lines above the one actionable line ("the waiver was
    # given for a different render") is how a reader learns to scroll past this gate's output.
    wv, wprobs = waiver(out_dir)
    if wv is not None:
        return {"declared": len(dimensions()), "judged": 0, "pass": 0, "fail": 0,
                "na": [], "unjudged": [], "missing": [], "waived": not wprobs}
    declared = dimensions()
    # Counters are named rather than indexed by the verdict string: `out[v] += 1` would reach into the
    # LIST fields the moment a new verdict shares their name, and a coverage report that raises is a
    # coverage report nobody keeps.
    out = {"declared": len(declared), "judged": 0, "pass": 0, "fail": 0, "na": [], "missing": [],
           "unjudged": []}
    try:
        led = json.load(open(os.path.join(out_dir, LEDGER_NAME), encoding="utf-8"))
        rows = led.get("rows") or []
        by_id = {str(r.get("id", "")).strip(): r for r in rows if isinstance(r, dict)}
    except Exception:                                        # noqa: BLE001 — validate() reports the why
        by_id = {}
    for sid, title in declared:
        r = by_id.get(sid)
        if r is None:
            out["missing"].append("%s (%s)" % (sid, title))
            continue
        v = str(r.get("verdict", "")).strip().lower()
        if v == "pass":
            out["judged"] += 1
            out["pass"] += 1
        elif v == "fail":
            out["judged"] += 1
            out["fail"] += 1
        elif v == "na":
            out["na"].append("%s (%s): %s" % (sid, title, str(r.get("note", "")).strip() or "no reason given"))
        else:
            out["unjudged"].append("%s (%s): verdict %r is not one of %s"
                                   % (sid, title, r.get("verdict"), "/".join(VERDICTS)))
    return out


WAIVER_KEY = "review_waiver"


def waiver(out_dir):
    """(waiver_dict, [problems]) — the user's decision to ship without a critic pass, or (None, []).

    Read from storyboard.json's `meta`, not from the ledger: the ledger is the REVIEWER's artifact and a
    waiver is not a review. Returns problems rather than raising so the gate can report them like any other
    finding."""
    board = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board):
        return None, []
    try:
        meta = (json.load(open(board, encoding="utf-8")) or {}).get("meta") or {}
    except Exception:                                         # noqa: BLE001 — a broken board is validate.py's
        return None, []
    w = meta.get(WAIVER_KEY)
    if w is None:
        return None, []
    if isinstance(w, str):
        w = {"reason": w}
    if not isinstance(w, dict):
        return None, ["meta.%s must be an object {reason, render_sha256} or a reason string" % WAIVER_KEY]
    probs = []
    reason = str(w.get("reason") or "").strip()
    if len(reason) < 12:
        probs.append("meta.%s.reason is empty or too short — a waiver is a decision someone made, and the "
                     "record has to say what it was, in the user's own words" % WAIVER_KEY)
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    pinned = str(w.get("render_sha256") or "").strip().lower()
    if not pinned:
        probs.append("meta.%s.render_sha256 is empty — a waiver covers the render the user actually watched, "
                     "so it must be pinned to one" % WAIVER_KEY)
    elif not os.path.exists(sheet):
        probs.append("%s is missing, so the pinned render cannot be checked — run scripts/critic_brief.py"
                     % CONTACT_SHEET)
    elif pinned != sha256_of(sheet):
        probs.append("meta.%s was given for a DIFFERENT render (pinned %s, this film is %s). The film has "
                     "been re-rendered since it was waived; a waiver is not a standing licence over "
                     "everything changed afterwards. Show the user this cut and ask again, or review it."
                     % (WAIVER_KEY, pinned[:12], sha256_of(sheet)[:12]))
    return w, probs


def validate(out_dir, final=False):
    errs, warns = [], []
    wv, wprobs = waiver(out_dir)
    if wv is not None:
        if wprobs:
            return (["the review waiver is not usable: " + p for p in wprobs], [])
        return ([], ["REVIEW WAIVED BY THE USER for this render — no critic judged this film. Reason given: "
                     "%r. The deterministic gates still apply and still gate delivery; this waives taste, "
                     "not whether the file plays." % str(wv.get("reason"))[:160]])
    path = os.path.join(out_dir, LEDGER_NAME)
    if not os.path.exists(path):
        return (["no %s — the review produced no per-dimension record. Run with --emit-template, fill every "
                 "row, then re-run this gate." % LEDGER_NAME], [])
    try:
        led = json.load(open(path, encoding="utf-8"))
    except Exception as e:                                    # noqa: BLE001 - report, don't crash the gate
        return (["%s is not valid JSON: %s" % (LEDGER_NAME, e)], [])

    # ── the artifact the reviewer actually looked at ────────────────────────────────────────────────────
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    if not os.path.exists(sheet):
        errs.append("%s is missing — run scripts/critic_brief.py first; a review with no contact sheet saw "
                    "no film" % CONTACT_SHEET)
    else:
        want = sha256_of(sheet)
        got = str(led.get("contact_sheet_sha256", "")).strip().lower()
        if not got:
            errs.append("contact_sheet_sha256 is empty — a ledger must be pinned to the render it reviewed")
        elif got != want:
            errs.append("contact_sheet_sha256 %s does not match the film's contact sheet (%s) — this ledger "
                        "reviews a DIFFERENT render than the one in %s" % (got[:12], want[:12], out_dir))

    # ── one row per declared dimension, no more, no fewer ───────────────────────────────────────────────
    declared = dimensions()
    rows = led.get("rows")
    if not isinstance(rows, list):
        return (errs + ["`rows` must be a list, one entry per dimension"], warns)
    by_id = {}
    for r in rows:
        if not isinstance(r, dict):
            errs.append("every row must be an object")
            continue
        sid = str(r.get("id", "")).strip()
        if sid in by_id:
            errs.append("%s appears twice" % sid)
        by_id[sid] = r
    for sid, title in declared:
        if sid not in by_id:
            errs.append("%s (%s) has no row — an unexamined dimension is a missing row, not a clean one"
                        % (sid, title))
    for sid in by_id:
        if sid not in dict(declared):
            warns.append("%s is not a dimension the critic declares" % sid)

    for sid, title in declared:
        r = by_id.get(sid)
        if r is None:
            continue
        v = str(r.get("verdict", "")).strip().lower()
        if v not in VERDICTS:
            errs.append("%s verdict %r must be one of %s" % (sid, r.get("verdict"), "/".join(VERDICTS)))
            continue
        if v == "na":
            if not str(r.get("note", "")).strip():
                errs.append("%s is N/A with no reason — say why it does not apply" % sid)
            continue
        ev = str(r.get("evidence", "")).strip()
        if not ev:
            errs.append("%s is %s with no evidence — cite the keyframe you read or the brief line you took "
                        "the verdict from" % (sid, v))
        else:
            # A cited FILE must exist. A cited brief line is prose and cannot be checked, so it is allowed
            # through — but a path that looks like a file and is not one is the failure mode worth catching:
            # it reads as specific evidence while pointing at nothing.
            for tok in re.findall(r"[\w./\\-]+\.(?:png|jpg|jpeg|mp4|json|md|srt)\b", ev):
                cand = tok if os.path.isabs(tok) else os.path.join(out_dir, tok)
                if not os.path.exists(cand) and not os.path.exists(os.path.join(_ROOT, tok)):
                    errs.append("%s cites %s, which does not exist" % (sid, tok))
        if v == "fail" and not str(r.get("fix", "")).strip():
            errs.append("%s failed with no FIX — a finding the director cannot act on is not a finding" % sid)

    # ── the film-level verdict must agree with the rows ─────────────────────────────────────────────────
    overall = str(led.get("verdict", "")).strip().upper()
    if overall not in ("PASS", "REVISE"):
        errs.append("verdict must be PASS or REVISE")
    failed = sorted(s for s, r in by_id.items() if str(r.get("verdict", "")).lower() == "fail")
    if overall == "PASS" and failed:
        errs.append("verdict is PASS while %s failed" % ", ".join(failed))

    # ── who reviewed ────────────────────────────────────────────────────────────────────────────────────
    who = str(led.get("reviewer", "")).strip().lower()
    if who not in ("independent", "in-context"):
        errs.append("reviewer must be 'independent' (a fresh subagent given only <out_dir>) or 'in-context'")
    elif final and who != "independent":
        errs.append("the DELIVERY review was run in-context by the film's own maker. The maker has "
                    "confirmation bias about their own output: re-dispatch the critic as a fresh subagent "
                    "whose whole input is <out_dir>, and let it reach its own verdict.")
    elif who == "in-context":
        warns.append("in-context review — fine for an interim pass; delivery needs an independent one")

    return errs, warns


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: critic_ledger.py <out_dir> [--emit-template] [--final]")
        return 2
    out_dir = os.path.abspath(argv[0])
    if not os.path.isdir(out_dir):
        print("[critic_ledger] no such out_dir: %s" % out_dir)
        return 2
    if "--emit-template" in argv:
        path = os.path.join(out_dir, LEDGER_NAME)
        if os.path.exists(path):
            print("[critic_ledger] %s already exists — not overwriting a filled ledger" % LEDGER_NAME)
            return 2
        json.dump(template(out_dir), open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("[critic_ledger] wrote %s — fill every row, then re-run without --emit-template" % path)
        return 0

    final = "--final" in argv
    wv, _wprobs = waiver(out_dir)
    errs, warns = validate(out_dir, final=final)
    cov = coverage(out_dir)
    for w in warns:
        print("[critic_ledger] WARN  %s" % w)
    for e in errs:
        print("[critic_ledger] ERROR %s" % e)
    for n in cov["na"]:
        print("[critic_ledger] NOT JUDGED (n/a) %s" % n)
    for n in cov["unjudged"]:
        print("[critic_ledger] NOT JUDGED %s" % n)
    for n in cov["missing"]:
        print("[critic_ledger] NO ROW %s" % n)
    print("[critic_ledger] %s  judged %d of %d dimension(s) (%d pass / %d fail) · %d n/a · %d no row · "
          "%d error(s), %d warning(s)%s"
          % ("FAIL" if errs else "OK", cov["judged"], cov["declared"], cov["pass"], cov["fail"],
             len(cov["na"]), len(cov["missing"]), len(errs), len(warns),
             "  (delivery gate)" if final else ""))
    # THE OTHER END OF THE SAME STRING. `render_remotion` leaves a NOT_DELIVERED.md in the out_dir carrying
    # the steps that are left, because a printed checklist can be scrolled past and a file in the deliverable
    # cannot. This is the only thing allowed to remove it, and only on a clean DELIVERY review — so the
    # question "was this film ever looked at?" is answerable by `ls` instead of by trusting a summary.
    #
    # AND THE MARKER COMES OFF FOR THE VERDICT, NOT FOR THE FORM. The first version of this removed it on
    # `final and not errs` — and `errs` is everything wrong with the LEDGER, not with the FILM. The very
    # first independent review run through this gate said REVISE with six failed rows, was perfectly well
    # formed, exited 0, and the marker was deleted: `ls` then reported the film as delivered while the
    # review said the opposite. The reviewer caught it and wrote it up as its first finding, which is the
    # only reason it is fixed here. A clean ledger is the gate on the REVIEW; a PASS verdict is the gate on
    # the FILM, and delivery needs both.
    nd = os.path.join(out_dir, "NOT_DELIVERED.md")
    overall = ""
    try:
        overall = str(json.load(open(os.path.join(out_dir, LEDGER_NAME), encoding="utf-8"))
                      .get("verdict", "")).strip().upper()
    except Exception:                                        # noqa: BLE001 — a missing ledger is already an err
        pass
    # A WAIVER IS NOT A PASS, so the marker does not simply come off: it is REWRITTEN to say the film shipped
    # unreviewed and who decided that. `ls` must still answer "was this film ever looked at?" truthfully, and
    # for a waived film the honest answer is no — by the user's choice, for this exact render.
    if final and wv is not None and not errs:
        with open(nd, "w", encoding="utf-8") as fh:
            fh.write("# Delivered WITHOUT a critic review\n\n"
                     "The user waived `shot-critic` for this render (`meta.review_waiver` in "
                     "storyboard.json).\n\n- **Reason given:** %s\n- **Render this covers:** contact sheet "
                     "`%s`\n\nNo critic judged register fit, meaning, frame-craft, boldness or direction "
                     "adherence on this film. The deterministic gates DID run and did gate delivery.\n\n"
                     "If this film is re-rendered, the waiver expires with it: the pin above stops matching "
                     "and `critic_ledger.py --final` asks again.\n"
                     % (str(wv.get("reason"))[:400],
                        str(wv.get("render_sha256"))[:16]))
        print("[critic_ledger] delivered UNREVIEWED — rewrote NOT_DELIVERED.md to say so")
    elif final and os.path.exists(nd):
        if not errs and overall == "PASS":
            os.remove(nd)
            print("[critic_ledger] delivery review PASSED — removed NOT_DELIVERED.md")
        elif not errs:
            print("[critic_ledger] the ledger is well formed and its verdict is %r — the FILM is not "
                  "delivered. NOT_DELIVERED.md stays until a review passes." % (overall or "missing"))
        else:
            print("[critic_ledger] NOT_DELIVERED.md stays: fix the ledger, then the film")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
