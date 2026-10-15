#!/usr/bin/env python3
"""The rendered review's per-dimension VERDICT LEDGER, on both tiers — the backstop that makes "silence is not consent" real.

    python3 scripts/critic_ledger.py <out_dir> --emit-template   # skeleton with every dimension listed
    python3 scripts/critic_ledger.py <out_dir>                   # validate a filled ledger
    python3 scripts/critic_ledger.py <out_dir> --final           # ...as the DELIVERY gate
    python3 scripts/critic_ledger.py <out_dir> --render-id       # the current render id, alone on stdout
    python3 scripts/critic_ledger.py <out_dir> --preselect       # the review depth to pre-select, and why

ONE GATE, TWO CRITICS. A remotion film is reviewed by agents/shot-critic.md (the S-dimensions); an HTML-tier film
(not remotion, at least one `type:"html"` page) by agents/design-critic.md's delivery section (the H-dimensions),
with critic-av's lens carried in `fast` and running beside it otherwise. Everything below — rows, evidence, the
render pin, the depth, the rounds, the user's acceptances, the routes — is the same method on both; only the list of
dimensions and which of them is never accepted change, and both are PARSED from the critic's own file. The 原样配音
tier (every beat a supplied slide) and a programmatic-only board have no authored page to judge and no keyframes to
pin, so this gate says it does not apply to them (exit 2) rather than passing them.

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
* A ledger written WITHOUT the artifact. `render_sha256` must match the film's RENDER ID — the contact sheet,
  out.mp4 and out.srt hashed together (render_id) — so a ledger cannot be authored from memory of an earlier
  render, or from a description of one, and a re-voiced or re-captioned film is a different render.

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
* It EXPIRES WITH THE RENDER. The waiver pins the render id (picture, sound and captions), so it covers the film
  the user actually watched. Re-render — change one beat, one colour, one line of narration — and the id moves and
  the waiver no longer applies. This is the property that matters: "the user said fine once" must not become
  a standing licence over everything changed afterwards.
* It waives THIS review only. `check_av`, `validate.py` and the tier's own gates (`keyframe_qa` on HTML;
  `keyframe_qa_remotion`, `text_safe_qa`, `cjk_type_qa`, `film_energy_qa`, `shake_qa` on remotion) are untouched
  and still gate delivery. A waiver is a judgement about taste, never about whether the file plays.

AND A REVIEW DEPTH THE USER CHOSE. After the first clean render the user picks how hard to review it —
`meta.review = {tier, user_answer, preselected}` with tier fast | standard | thorough | none (SKILL.md "the
review-depth question"). `--final` refuses a film with no `meta.review`: a depth nobody asked about is not a
depth. The PRE-SELECTED option is computed, not chosen — preselect() returns `fast`, always — and `--final` holds
`meta.review.preselected` to it; the user may pick any tier. A reviewing tier may be the pre-selected option applied
without a reply (auto mode); `none` may not. The
tier scales the WEIGHT of the loop, never the floors: every row, every cited file, an independent reviewer and
the render pin are required on every tier that reviews. What the tier changes is the ROUND CAP — fast 1,
standard 2, thorough unbounded — and the ROUND is the render's place in `_contact_sheet_history.json`
(critic_brief.py records each briefed render), never a number the ledger writes about itself.
* A PASS covers the render it saw: it must be pinned to the CURRENT render.
* Once a capped tier has spent its rounds, a REVISE ledger may close the loop — pinned to the render it reviewed
  — only when every failed row is resolved: its fix `applied` in a later render, or ACCEPTED AS-IS by the user
  (`meta.review.accepted`, per finding, in their words, pinned to that render). The model never declines a
  finding; a faithfulness or sourcing finding (S3 / H1) is never accepted by anyone — it is fixed. The film ships
  marked "reviewed at <tier>, not a PASS", never as a PASS.
`none` is the same decision as `review_waiver` and is held to the same rules: the user's own answer, pinned to
the render they watched, never pre-selected and never inferred.

AND THE ROUTES. Every beat validate.py credits — ADAPTED or BUILT on remotion, BUILT or BESPOKE on HTML — carries a
route row in the ledger (`routes: [{beat, route, visible, evidence}]`): the critic confirms the route is VISIBLE in
the rendered frame, and a route it cannot see fails the dimension that declares the route rows (S14 / H8). A
self-described or source-measured route is a claim; this is where it is checked. (Not on a LEGACY film the user
chose to keep as designed — meta.design_first, validate.design_first_legacy: design-first is not applied to it.)

AND THE WAIVERS. A machine gate's finding the board waived (each non-empty `meta.*_waiver` but `review_waiver`) does
not raise the review depth — standard adds critic-av and a round, and neither re-judges the waived finding. Instead
each gets a `waivers` row (`{key, holds, evidence}`): the critic says whether the waiver's stated reason is TRUE of the
rendered film, and `holds: false` must come with a FAIL on the dimension the critic's file names as that finding's
owner (energy_waiver: S12 / H6). Required on every reviewing tier, on a legacy film too; not under `none`.

The dimension lists are PARSED from the critics' files. Restating them here is how this repo's caption band
became four disagreeing copies; a new dimension must be required by this gate the moment it is written down.
"""
import hashlib
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CRITIC = os.path.join(_ROOT, "agents", "shot-critic.md")
# The HTML tier's delivery review: design-critic's H-dimensions, in the same three-part form (rule / precedent /
# self-check) and read by the same parser — the rendered review is one method on both tiers, not two gates.
_DESIGN_CRITIC = os.path.join(_ROOT, "agents", "design-critic.md")
# The SECOND body of case law: rules for whoever edits the library, in the same form and parsed by
# the same two functions. It is listed here so the precedent-resolution test walks it too — a rule
# whose precedent nobody resolves is a rule that can cite an invented incident. The H-series is walked for the
# same reason: a delivery dimension on the HTML tier may not cite an incident nobody can resolve either.
_CASE_LAW = os.path.join(_ROOT, "references", "engineering-case-law.md")
CASE_LAW_FILES = ((_CRITIC, "S"), (_DESIGN_CRITIC, "H"), (_CASE_LAW, "E"))
# tier -> (the critic's file, its dimension series, the critic's name as a reader dispatches it)
SERIES = {"remotion": (_CRITIC, "S", "agents/shot-critic.md"),
          "html": (_DESIGN_CRITIC, "H", "agents/design-critic.md")}
_REMOTION = ("remotion", "remotion-bespoke")

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
            "no `**%sn · ...**` dimension headings found in %s — this gate requires one row per dimension and "
            "reads the list from there; if the heading format changed, update scripts/critic_ledger.py in the "
            "same change." % (prefix, path or _CRITIC))
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


def _board(out_dir):
    """(meta, slides) of the film's storyboard.json, or (None, None) when there is none or it cannot be read."""
    try:
        b = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    except Exception:                                         # noqa: BLE001 — a broken board is validate.py's
        return None, None
    if not isinstance(b, dict):
        return None, None
    meta = b.get("meta") if isinstance(b.get("meta"), dict) else {}
    slides = [s for s in b.get("slides") or [] if isinstance(s, dict)] if isinstance(b.get("slides"), list) else []
    return meta, slides


def _validate_module():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import validate as _v
    return _v


def film_tier(out_dir):
    """"remotion" | "html" | None — whose dimensions this film's ledger is held to.

    HTML is validate.is_html_film's definition (the one the design-first floor uses), so the two gates cannot
    disagree about which films are HTML films. None — the 原样配音 tier, every beat a supplied slide, or a board of
    programmatic scenes only — has no authored page and no keyframe to pin, and this gate does not apply. A missing
    or unreadable board reads as remotion: the S-series is what this gate required before it knew about tiers, and a
    board that cannot be read is no evidence that it is anything else."""
    meta, slides = _board(out_dir)
    if meta is None or str(meta.get("renderer", "")).lower() in _REMOTION:
        return "remotion"
    return "html" if _validate_module().is_html_film(meta, slides) else None


def film_dimensions(out_dir):
    """[(id, title)] for this film's tier — [] when the gate does not apply (film_tier None)."""
    tier = film_tier(out_dir)
    return dimensions(*SERIES[tier][:2]) if tier else []


def critic_of(out_dir):
    tier = film_tier(out_dir)
    return SERIES[tier][2] if tier else "agents/critic-av.md"


def routes_dimension(path=None, prefix="S"):
    """The dimension the ledger's route rows bind to, READ from the critic's file: the one whose own body says
    "`visible: false` on any row makes <its id> a FAIL" (S14 on remotion, H8 on HTML). It used to be found by a
    GROWTH title regex, which named one series' heading and would have silently bound nothing on the other."""
    src = open(path or _CRITIC, encoding="utf-8").read()
    for sid, body in re.findall(r"^\*\*(%s\d+)\s*·(.*?)(?=^\*\*%s\d+\s*·|\Z)" % (prefix, prefix), src, re.M | re.S):
        if re.search(r"`visible:\s*false`\s+on any row makes %s a FAIL" % re.escape(sid), body):
            return sid
    return None


def waiver_owners(path=None, prefix="S"):
    """{waiver key: the dimension that owns its finding}, READ from the critic's file: each dimension whose body says
    "a `meta.<key>` row with `holds: false` makes <its id> a FAIL" (energy_waiver: S12 on remotion, H6 on HTML) — the
    same declaration-in-the-doctrine shape as routes_dimension, so a waiver whose owner nobody wrote down is a hole the
    gate names, not a FAIL it silently pins on whichever title happens to match."""
    src = open(path or _CRITIC, encoding="utf-8").read()
    out = {}
    for sid, body in re.findall(r"^\*\*(%s\d+)\s*·(.*?)(?=^\*\*%s\d+\s*·|\Z)" % (prefix, prefix), src, re.M | re.S):
        for key in re.findall(r"`meta\.(\w+_waiver)`\s+row\s+with\s+`holds:\s*false`\s+makes\s+%s\s+a\s+FAIL"
                              % re.escape(sid), body):
            out.setdefault(key, sid)
    return out


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# THE RENDER ID — what every pin in this gate is pinned to: the ledger's, a `none` answer's, a waiver's, each
# accepted finding's, and the render history's. It was the contact sheet's sha256 alone, and the sheet is drawn
# from keyframes, which do not hear the voice: change a narration line or the captions, re-render, and the pin did
# not move — an old PASS, waiver or acceptance went on "covering" a film nobody had watched, while SKILL.md told
# the reader that one changed line of narration moves the sha. The id now hashes what the viewer is handed:
#   _contact_sheet.png   the picture the reviewer read
#   out.mp4              the film as delivered — picture, sound and the burned-in captions
#   out.srt              the caption sidecar delivered beside it
# Both tiers' FULL render writes those two names (render.py, render_remotion.py); the step-8 sample (sample.mp4)
# and the HTML `--preview` (preview.mp4) are not the delivered film and are deliberately NOT covered. Nor is a board
# edit nobody has rendered yet — the pin is about what was rendered, not what was planned. With neither out.mp4 nor
# out.srt on disk the id IS the contact sheet's sha256, so a pictures-only record keeps the value it always had.
RENDER_FILES = ("out.mp4", "out.srt")
LEGACY_PIN = "contact_sheet_sha256"          # the ledger field's old name, still READ (with a WARN) — never written


def render_id(out_dir):
    """The current render's id (see RENDER_FILES), or "" when there is no contact sheet to anchor it."""
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    if not os.path.exists(sheet):
        return ""
    base = sha256_of(sheet)
    parts = [(name, sha256_of(os.path.join(out_dir, name))) for name in RENDER_FILES
             if os.path.isfile(os.path.join(out_dir, name))]
    if not parts:
        return base
    # the NAMES go into the hash too, so an out.srt alone and an out.mp4 alone with equal bytes are not one render
    h = hashlib.sha256(("%s:%s" % (CONTACT_SHEET, base)).encode("ascii"))
    for name, sha in parts:
        h.update(("\n%s:%s" % (name, sha)).encode("ascii"))
    return h.hexdigest()


def _pin_of(led):
    """(pin, read_from_the_old_name) — the ledger's `render_sha256`, or its pre-rename `contact_sheet_sha256`."""
    if not isinstance(led, dict):
        return "", False
    pin = str(led.get("render_sha256") or "").strip().lower()
    if pin:
        return pin, False
    old = str(led.get(LEGACY_PIN) or "").strip().lower()
    return old, bool(old)


def template(out_dir):
    try:
        routes = _design_routes(out_dir)
    except Exception as e:                                    # noqa: BLE001 — the gate itself reports it again
        print("[critic_ledger] the design routes could not be computed (%s: %s) — fill `routes` by hand from "
              "scripts/validate.py" % (type(e).__name__, e))
        routes = []
    return {
        # EMPTY on purpose. Pre-filling "independent" would answer, on the reviewer's behalf, the one
        # question this gate exists to ask — and make the lazy path the untrue one.
        "reviewer": "",
        "_reviewer_help": "independent = a fresh subagent given only <out_dir>; in-context = the film's own "
                          "maker (allowed for an interim pass, REFUSED by --final)",
        "_critic": critic_of(out_dir),
        "render_sha256": render_id(out_dir),
        "verdict": "REVISE",
        "rows": [
            {"id": sid, "verdict": "", "evidence": "", "note": "", "fix": "", "_dimension": title}
            for sid, title in film_dimensions(out_dir)
        ],
        # THE ROUTES validate.py CREDITS — each one the critic confirms (or not) in the rendered frame (S14 / H8)
        "routes": [{"beat": num, "route": route, "visible": None, "evidence": ""} for num, route in routes],
        # THE WAIVED GATE FINDINGS — is each waiver's stated reason true of the rendered film? (holds: false → the
        # dimension that owns it FAILs)
        "waivers": [{"key": key, "holds": None, "evidence": "", "_reason": reason}
                    for key, reason in gate_waivers(out_dir)],
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
    declared = film_dimensions(out_dir)
    if wv is not None:
        return {"declared": len(declared), "judged": 0, "pass": 0, "fail": 0,
                "na": [], "unjudged": [], "missing": [], "waived": not wprobs}
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


REVIEW_KEY = "review"
TIERS = ("fast", "standard", "thorough", "none")
ROUND_CAP = {"fast": 1, "standard": 2, "thorough": None}
HISTORY = "_contact_sheet_history.json"
# words that record a DEFAULT or an inference rather than an answer. They are fine on fast/standard/thorough
# when the tier is the PRE-SELECTED one (auto mode, or no reply) — a reviewing tier applied by default is still a
# review. They are never enough for `none`, which exists only as the user's own word.
_NOT_AN_ANSWER = {"default", "auto", "auto mode", "inferred", "assumed", "no answer", "no reply", "silence",
                  "timeout", "n/a", "na", "unknown", "preselected", "pre-selected"}


def _board_meta(out_dir):
    board = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board):
        return {}
    try:
        return (json.load(open(board, encoding="utf-8")) or {}).get("meta") or {}
    except Exception:                                         # noqa: BLE001 — a broken board is validate.py's
        return {}


def _placeholder(text):
    t = str(text or "").strip()
    return t.startswith("<") and t.endswith(">")


def _non_answer(text):
    """True for an empty answer, the template placeholder, or a record of NO answer ("no reply", "auto mode",
    "default (auto mode)") — matched as a leading phrase, so a note after it does not turn it into an answer."""
    t = str(text or "").strip()
    if not t or _placeholder(t):
        return True
    low = t.lower()
    return any(low == w or re.match(re.escape(w) + r"(?![a-z])", low) for w in _NOT_AN_ANSWER)


def review(out_dir):
    """(review_dict, [problems]) — the depth the user chose at the review question, or (None, []).

    None means nobody recorded a choice. `--final` refuses that ("ask the review question"); an interim run
    behaves as `thorough`. Nothing here ever turns an absent or malformed answer into a lighter tier, least of
    all `none`."""
    r = _board_meta(out_dir).get(REVIEW_KEY)
    if r is None:
        return None, []
    if not isinstance(r, dict):
        return None, ["meta.%s must be an object {tier, user_answer, preselected}" % REVIEW_KEY]
    probs = []
    tier = str(r.get("tier") or "").strip().lower()
    if tier not in TIERS:
        probs.append("meta.%s.tier %r must be one of %s" % (REVIEW_KEY, r.get("tier"), " | ".join(TIERS)))
    ans = str(r.get("user_answer") or "").strip()
    pre = str(r.get("preselected") or "").strip().lower()
    if _placeholder(ans):
        probs.append("meta.%s.user_answer %r is the template's placeholder, not an answer — record what the user said, or "
                     "\"no reply\" when the pre-selected tier was applied without one" % (REVIEW_KEY, ans))
    elif tier == "none" and _non_answer(ans):
        probs.append("meta.%s.user_answer %r is not an answer — `none` exists only as the user's own word (the "
                     "option they picked, or what they said); a default, an inference or silence is not it"
                     % (REVIEW_KEY, ans))
    elif tier in ROUND_CAP and _non_answer(ans) and pre != tier:
        probs.append("meta.%s.user_answer %r records no reply, so the tier must be the one you PRE-SELECTED — "
                     "set meta.%s.preselected to %r, or record the user's actual answer"
                     % (REVIEW_KEY, ans, REVIEW_KEY, tier))
    if pre == "none":
        probs.append("meta.%s.preselected is 'none' — `none` is never pre-selected; it exists only as the "
                     "user's own answer" % REVIEW_KEY)
    elif pre and pre not in TIERS:
        probs.append("meta.%s.preselected %r must be one of %s" % (REVIEW_KEY, pre, " | ".join(TIERS[:3])))
    acc = r.get("accepted")
    if acc is not None and not isinstance(acc, list):
        probs.append("meta.%s.accepted must be a list of {id, user_answer, render_sha256} — one per finding the "
                     "user accepted as-is" % REVIEW_KEY)
    for i, a in enumerate(acc if isinstance(acc, list) else []):
        if not isinstance(a, dict) or not str(a.get("id") or "").strip():
            probs.append("meta.%s.accepted[%d] must be {id, user_answer, render_sha256}" % (REVIEW_KEY, i))
        elif _non_answer(a.get("user_answer")) or len(str(a.get("user_answer")).strip()) < 2:
            probs.append("meta.%s.accepted[%d] (%s) carries no user answer — an accepted finding is the USER's "
                         "decision, recorded in their own words; nobody else may accept one"
                         % (REVIEW_KEY, i, a.get("id")))
    return dict(r, tier=tier), probs


def _waived(v):
    """True when a waiver value actually waives something: a non-empty reason, or an object/list holding one. An
    empty `{}` or `""` waives nothing (film_energy_qa.parse_waiver drops empty reasons the same way)."""
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, dict):
        return any(_waived(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(_waived(x) for x in v)
    return bool(v)


def gate_waivers(out_dir):
    """[(key, reason)] for every machine-gate finding the board WAIVES: each non-empty `meta.<gate>_waiver` (today
    `energy_waiver`, film_energy_qa's; a future gate's waiver counts the day it is written, without editing this),
    except `review_waiver`, which waives the review itself. The review confirms each in a `waivers` ledger row."""
    out = []
    for k, v in sorted(_board_meta(out_dir).items()):
        if not (isinstance(k, str) and k.endswith("_waiver") and k != WAIVER_KEY and _waived(v)):
            continue
        if isinstance(v, dict):
            reason = "; ".join("%s: %s" % (a, str(b).strip()) for a, b in v.items() if _waived(b))
        elif isinstance(v, (list, tuple)):
            reason = "; ".join(str(x).strip() for x in v if _waived(x))
        else:
            reason = str(v).strip()
        out.append((k, reason))
    return out


def preselect(out_dir):
    """(tier, why) — the review depth the review-depth question PRE-SELECTS: `fast`, always.

    It used to be left to the model ("pre-select standard on a concrete trigger"), and then to a rule — standard
    whenever a machine gate's finding was waived. Calibrated on the four acceptance films, that rule made standard
    the de-facto default: every one of them carries `meta.energy_waiver`, because diagram films routinely waive
    film_energy_qa's motion floor. And the bump was untargeted — standard adds critic-av and a second round, and
    neither re-judges the waived finding. So the default stays `fast`, the user may pick any tier, and each waived
    finding is confirmed where it can be: its own `waivers` row in the ledger (_waiver_rows), on every tier."""
    n = len(gate_waivers(out_dir))
    return "fast", ("the default, always; the user may pick any tier" +
                    (" — %d waived machine-gate finding(s) on the board do not raise it: the critic confirms each in "
                     "its own `waivers` ledger row" % n if n else ""))


def _preselect_problems(out_dir, rv):
    """--final: meta.review.preselected must be recorded and must be what preselect() computes NOW."""
    want, why = preselect(out_dir)
    pre = str((rv or {}).get("preselected") or "").strip().lower()
    if not pre:
        return ["meta.%s.preselected is missing — record the tier the question PRE-SELECTED; it is computed, not "
                "chosen: python3 scripts/critic_ledger.py <out_dir> --preselect → `%s` (%s)" % (REVIEW_KEY, want, why)]
    if pre == "none" or pre not in TIERS:
        return []                                  # review() already refuses these
    if pre != want:
        return ["meta.%s.preselected is `%s`, but the review-depth question pre-selects `%s` (%s) — the pre-selection is "
                "computed (--preselect), not chosen. Ask the question again with `%s` pre-selected and record the "
                "answer; the user may still pick any tier" % (REVIEW_KEY, pre, want, why, want)]
    return []


def accepted(out_dir):
    """{(finding id, render sha)} the user accepted as-is (meta.review.accepted)."""
    r = _board_meta(out_dir).get(REVIEW_KEY)
    acc = r.get("accepted") if isinstance(r, dict) else None
    out = {}
    for a in acc if isinstance(acc, list) else []:
        if isinstance(a, dict) and not _non_answer(a.get("user_answer")) and len(str(a.get("user_answer")).strip()) >= 2:
            out[(str(a.get("id") or "").strip(), str(a.get("render_sha256") or "").strip().lower())] = \
                str(a.get("user_answer")).strip()
    return out


def never_accepted(out_dir=None):
    """The dimensions whose FAIL is always fixed, never accepted by anyone: faithfulness and sourcing. Parsed from
    the critic's own titles, like the dimension list itself — from THIS film's series (S3 on remotion, H1 on HTML);
    with no out_dir, the S-series."""
    dims = film_dimensions(out_dir) if out_dir else dimensions()
    return {sid for sid, title in dims if re.search(r"FAITHFUL|SOURC", title, re.I)}


def _history(out_dir):
    """[(sha, tier at the time)] in the order the renders were first briefed. The older file — a sorted list of
    shas — carries no order and no tier, so its renders count for membership but for no round."""
    try:
        h = json.load(open(os.path.join(out_dir, HISTORY), encoding="utf-8"))
    except Exception:                                         # noqa: BLE001 — no history = no earlier render
        return []
    out = []
    for x in h if isinstance(h, list) else []:
        if isinstance(x, dict) and x.get("sha"):
            out.append((str(x["sha"]).lower(), x.get("tier") or None))
        elif isinstance(x, str):
            out.append((x.lower(), None))
    return out


def history_shas(out_dir):
    return {sha for sha, _t in _history(out_dir)}


def record_render(out_dir):
    """Append the current render id (render_id) to the out_dir's render history (critic_brief.py calls this, once
    per review round), with the review tier recorded at the time. The ROUND of a ledger is derived from this
    history (round_of), never from a field the ledger writes about itself."""
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    if not os.path.exists(sheet):
        return None
    sha = render_id(out_dir)
    rv, rprobs = review(out_dir)
    tier = (rv or {}).get("tier") if rv and not rprobs and (rv or {}).get("tier") in ROUND_CAP else None
    hist = [{"sha": s, "tier": t} for s, t in _history(out_dir)]
    # A HISTORY WRITTEN BEFORE THE ID COVERED SOUND holds the contact sheet's sha for this same picture. Under the
    # old rule that WAS this render; appending the id beside it would count one render as two review rounds and
    # spend a capped tier's round on a change of format. It is upgraded in place, keeping its tier.
    old = sha256_of(sheet)
    if old != sha and all(e["sha"] != sha for e in hist):
        for e in hist:
            if e["sha"] == old:
                e["sha"] = sha
                break
    for e in hist:
        if e["sha"] == sha:
            if e["tier"] is None and tier:
                e["tier"] = tier          # first briefed before the depth was chosen; this is its review round
            break
    else:
        hist.append({"sha": sha, "tier": tier})
    json.dump(hist, open(os.path.join(out_dir, HISTORY), "w", encoding="utf-8"), indent=1)
    return sha


def round_of(out_dir, sha):
    """The review round a render was, counted from the render history: its position among the renders briefed
    after the review depth was chosen. None when the render is not in the history or predates that choice."""
    n = 0
    for s, t in _history(out_dir):
        if t:
            n += 1
        if s == str(sha or "").lower():
            return n if t else None
    return None


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
    rv = meta.get(REVIEW_KEY)
    if w is None and isinstance(rv, dict) and str(rv.get("tier") or "").strip().lower() == "none":
        # THE REVIEW QUESTION'S `none` IS A WAIVER, held to the same pin and expiry. Its reason is the user's
        # answer; review() refuses an answer that is really a default, so this only ever sees a real one.
        rprobs = review(out_dir)[1]
        w = {"reason": str(rv.get("user_answer") or ""), "render_sha256": rv.get("render_sha256"),
             "_from": REVIEW_KEY}
        if rprobs:
            return w, rprobs
    if w is None:
        return None, []
    if isinstance(w, str):
        w = {"reason": w}
    if not isinstance(w, dict):
        return None, ["meta.%s must be an object {reason, render_sha256} or a reason string" % WAIVER_KEY]
    # name the field the user's answer actually lives in — `meta.review` (tier none) or the older form
    key = REVIEW_KEY if w.get("_from") == REVIEW_KEY else WAIVER_KEY
    probs = []
    reason = str(w.get("reason") or "").strip()
    if w.get("_from") == REVIEW_KEY:
        pass                     # a picked option ("none") is a complete answer; review() vetted it above
    elif len(reason) < 12:
        probs.append("meta.%s.reason is empty or too short — a waiver is a decision someone made, and the "
                     "record has to say what it was, in the user's own words" % WAIVER_KEY)
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    pinned = str(w.get("render_sha256") or "").strip().lower()
    if not pinned:
        probs.append("meta.%s.render_sha256 is empty — a waiver covers the render the user actually watched, "
                     "so it must be pinned to one (python3 scripts/critic_ledger.py <out_dir> --render-id)" % key)
    elif not os.path.exists(sheet):
        probs.append("%s is missing, so the pinned render cannot be checked — run scripts/critic_brief.py"
                     % CONTACT_SHEET)
    elif pinned != render_id(out_dir):
        now = render_id(out_dir)
        if pinned == sha256_of(sheet):
            probs.append("meta.%s pins the contact sheet ALONE (%s) — the rule before the pin covered sound and "
                         "captions, so it cannot say which narration and captions the user watched. Record the "
                         "render id of the cut the user watched (python3 scripts/critic_ledger.py <out_dir> "
                         "--render-id → %s), asking them again if it is not that cut." % (key, pinned[:12], now[:12]))
        else:
            probs.append("meta.%s was given for a DIFFERENT render (pinned %s, this film is %s). The film has "
                         "been re-rendered since it was waived — its picture, sound or captions changed; a waiver "
                         "is not a standing licence over everything changed afterwards. Show the user this cut "
                         "and ask again, or review it." % (key, pinned[:12], now[:12]))
    return w, probs


def _ledger_pin(out_dir):
    try:
        return _pin_of(json.load(open(os.path.join(out_dir, LEDGER_NAME), encoding="utf-8")))[0]
    except Exception:                                         # noqa: BLE001 — validate() reports the why
        return ""


def capped(out_dir):
    """(tier, cap, round, spent) for the ledger in out_dir. The ROUND is the round of the render the ledger is
    pinned to, derived from the render history (round_of) — never read from the ledger. `spent` is True once a
    capped tier has used its rounds; thorough (and an unrecorded tier) never is."""
    rv, rprobs = review(out_dir)
    tier = (rv or {}).get("tier") if rv and not rprobs else "thorough"
    cap = ROUND_CAP.get(tier)
    rnd = round_of(out_dir, _ledger_pin(out_dir))
    return tier, cap, rnd, bool(cap is not None and rnd is not None and rnd >= cap)


def _stale_sheet(out_dir):
    """True when a keyframe is newer than the contact sheet — the film was re-rendered and critic_brief.py was
    not re-run, so the sheet (and every pin checked against it) still describes the OLD render."""
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    kdir = os.path.join(out_dir, "_keyframes")
    if not (os.path.exists(sheet) and os.path.isdir(kdir)):
        return False
    frames = [os.path.join(kdir, f) for f in os.listdir(kdir) if re.match(r"scene_\d+\.png$", f)]
    return bool(frames) and max(os.path.getmtime(f) for f in frames) > os.path.getmtime(sheet)


# the routes validate.py CREDITS on each tier, which the critic must then see in the rendered frame
CREDITED = {"remotion": ("adapted", "built"), "html": ("built", "bespoke")}


def _design_routes(out_dir):
    """[(beat, route)] for the beats validate.py credits — ADAPTED or BUILT on remotion (design_routes), BUILT or
    BESPOKE on HTML (html_design_routes, measured from the page source) — the routes the critic must see."""
    meta, slides = _board(out_dir)
    tier = film_tier(out_dir)
    if not slides or meta is None or tier is None:
        return []
    _v = _validate_module()
    if _v.design_first_legacy(meta, slides, out_dir, tier)["accepted"]:
        return []        # a LEGACY film the user chose to keep as designed: design-first is not applied, by decision
    if tier == "remotion":
        return [(num, r) for num, r, _w in _v.design_routes(meta, slides, out_dir) if r in CREDITED[tier]]
    return [(num, r) for num, r, _w, _rel in _v.html_design_routes(meta, slides, out_dir) if r in CREDITED[tier]]


def _cites(out_dir, ev):
    """The cited files in an evidence string that do not exist."""
    bad = []
    for tok in re.findall(r"[\w./\\-]+\.(?:png|jpg|jpeg|mp4|json|md|srt)\b", ev):
        cand = tok if os.path.isabs(tok) else os.path.join(out_dir, tok)
        if not os.path.exists(cand) and not os.path.exists(os.path.join(_ROOT, tok)):
            bad.append(tok)
    return bad


def _unresolved(out_dir, by_id, failed, pin, current, tier):
    """Why each failed row of a capped tier's spent last round is NOT resolved. A finding is resolved by the fix
    being APPLIED in a later render (the ledger is pinned to the render it reviewed, which is in the history), or
    by the USER accepting it as-is (meta.review.accepted, their words, pinned to that same render). The model
    never declines a finding, and nobody accepts a faithfulness or sourcing one: those are fixed."""
    out, hard, acc = [], never_accepted(out_dir), accepted(out_dir)
    ask = ("take it to the user: list the open findings and offer ONE MORE ROUND or ACCEPT AS-IS, and record an "
           "acceptance in meta.%s.accepted as {id, user_answer (their words), render_sha256: %s}"
           % (REVIEW_KEY, pin[:12] + "…"))
    for sid in failed:
        r = by_id[sid]
        applied = str(r.get("applied", "")).strip()
        user_ok = (sid, pin) in acc
        if str(r.get("declined", "")).strip():
            out.append("%s records `declined` — at the %s tier the model may not decline a finding. Apply the "
                       "fix, or %s" % (sid, tier, ask))
            continue
        if sid in hard:
            if user_ok or any(k[0] == sid for k in acc):
                out.append("%s is a faithfulness/sourcing finding and was recorded as ACCEPTED — those are never "
                           "accepted, by anyone: fix it, re-render, re-run critic_brief.py" % sid)
            elif current or not applied:
                out.append("%s (faithfulness/sourcing) failed and is not fixed — it is never accepted, by anyone: "
                           "apply the fix, re-render, re-run scripts/critic_brief.py, and record `applied`" % sid)
            continue
        if user_ok:
            continue
        if applied and not current:
            continue
        if applied and current:
            out.append("%s records `applied`, but this ledger is pinned to the CURRENT render — the fix is not in "
                       "the film yet. Re-render and re-run scripts/critic_brief.py, or %s" % (sid, ask))
        else:
            stale = any(k[0] == sid for k in acc)
            out.append("%s failed and is unresolved — the %s tier's rounds are spent. Apply its fix (record "
                       "`applied` and re-render), or %s%s"
                       % (sid, tier, ask, " (an acceptance pinned to another render does not carry over)"
                          if stale else ""))
    return out


def _route_rows(out_dir, led, by_id, warns):
    """Every beat validate.py credits (CREDITED, per tier) needs a route row from the critic — the route seen in the
    rendered frame, not only described on the board or measured in the page source. A route the critic could not
    see makes the routes dimension (routes_dimension: S14 / H8) a FAIL."""
    try:
        routes = _design_routes(out_dir)
    except Exception as e:                                    # noqa: BLE001 — report, never mask
        return ["the design routes could not be computed (%s: %s) — run scripts/validate.py" % (type(e).__name__, e)]
    if not routes:
        return []
    tier = film_tier(out_dir)
    credited = " or ".join(r.upper() for r in CREDITED[tier])
    rd = routes_dimension(*SERIES[tier][:2])
    if rd is None:
        # a route row nothing binds to is a check that cannot fail — say so rather than accept every row
        return ["%s declares no dimension the route rows bind to (\"`visible: false` on any row makes <id> a "
                "FAIL\") — restore that sentence, or update scripts/critic_ledger.py in the same change"
                % SERIES[tier][2]]
    errs = []
    rows = led.get("routes")
    if not isinstance(rows, list):
        return ["`routes` is missing — %d beat(s) are credited as %s (%s); for each, the critic records {beat, "
                "route, visible: true|false, evidence: <keyframe>} saying whether that route is VISIBLE in the "
                "rendered frame (%s). --emit-template lists them."
                % (len(routes), credited, ", ".join("#%s %s" % rb for rb in routes[:8]), rd)]
    seen = {}
    for r in rows:
        if isinstance(r, dict):
            seen[str(r.get("beat"))] = r
    invisible = []
    for num, route in routes:
        r = seen.get(str(num))
        if r is None:
            errs.append("beat #%s is credited as %s and has no route row — %s confirms the route in the frame"
                        % (num, route.upper(), rd))
            continue
        if str(r.get("route", "")).strip().lower() != route:
            errs.append("beat #%s's route row says %r; validate.py credits it as %s — re-read the board"
                        % (num, r.get("route"), route))
        vis = r.get("visible")
        if not isinstance(vis, bool):
            errs.append("beat #%s's route row needs `visible: true|false` — is the %s route visible in the frame?"
                        % (num, route))
        ev = str(r.get("evidence", "")).strip()
        if not ev:
            errs.append("beat #%s's route row cites no evidence — name the keyframe it was judged on" % num)
        for tok in _cites(out_dir, ev):
            errs.append("beat #%s's route row cites %s, which does not exist" % (num, tok))
        if vis is False:
            invisible.append(str(num))
    if invisible and str((by_id.get(rd) or {}).get("verdict", "")).lower() != "fail":
        errs.append("the route rows say beat(s) %s do not show their route in the frame, but %s does not fail — "
                    "a route nobody can see is the %s as-is" % (", ".join(invisible), rd,
                                                              "register" if tier == "remotion" else "stock page"))
    extra = sorted(set(seen) - {str(n) for n, _r in routes})
    if extra:
        warns.append("route rows for beat(s) %s, which validate.py does not credit as %s"
                     % (", ".join(extra), " or ".join(CREDITED[tier])))
    return errs


def _waiver_rows(out_dir, led, by_id, warns):
    """Every machine-gate finding the board waives (gate_waivers) needs a `waivers` row from the critic —
    {key, holds: true|false, evidence} — saying whether the waiver's stated reason is TRUE of the rendered film. A
    waiver does not raise the review depth (preselect); this row is where it is checked. `holds: false` means the
    waived finding stands, so the dimension that owns it (waiver_owners) must FAIL. Required on every reviewing tier
    and on a legacy film (legacy waives design-first, nothing else); a `none` review has no ledger to carry it."""
    waived = gate_waivers(out_dir)
    if not waived:
        return []
    tier = film_tier(out_dir)
    owners = waiver_owners(*SERIES[tier][:2])
    rows = led.get("waivers")
    if not isinstance(rows, list):
        return ["`waivers` is missing — the board waives %d machine-gate finding(s) (%s); for each, the critic records "
                "{key, holds: true|false, evidence: <keyframe>} saying whether the waiver's stated reason is true of "
                "the rendered film. --emit-template lists them."
                % (len(waived), ", ".join("meta." + k for k, _r in waived))]
    seen = {}
    for r in rows:
        if isinstance(r, dict):
            seen[re.sub(r"^meta\.", "", str(r.get("key") or "").strip())] = r
    errs = []
    for key, _reason in waived:
        r = seen.get(key)
        if r is None:
            errs.append("meta.%s waives a machine gate's finding and has no `waivers` row — confirm its reason against "
                        "the rendered film: {key: %r, holds: true|false, evidence}" % (key, key))
            continue
        holds = r.get("holds")
        if not isinstance(holds, bool):
            errs.append("the `waivers` row for meta.%s needs `holds: true|false` — is the waiver's reason true of this "
                        "film?" % key)
        ev = str(r.get("evidence", "")).strip()
        if not ev:
            errs.append("the `waivers` row for meta.%s cites no evidence — name the keyframe or frame it was judged on"
                        % key)
        for tok in _cites(out_dir, ev):
            errs.append("the `waivers` row for meta.%s cites %s, which does not exist" % (key, tok))
        if holds is False:
            owner = owners.get(key)
            if owner is None:
                errs.append("the `waivers` row says meta.%s does not hold, and %s declares no dimension that owns that "
                            "finding (\"a `meta.%s` row with `holds: false` makes <id> a FAIL\") — write the owner "
                            "into the critic's file, or update scripts/critic_ledger.py in the same change"
                            % (key, SERIES[tier][2], key))
            elif str((by_id.get(owner) or {}).get("verdict", "")).lower() != "fail":
                errs.append("the `waivers` row says meta.%s does not hold — the waived finding stands — but %s, which "
                            "owns it, does not fail" % (key, owner))
    extra = sorted(set(seen) - {k for k, _r in waived})
    if extra:
        warns.append("`waivers` rows for %s, which the board does not waive" % ", ".join("meta." + k for k in extra))
    return errs


NOT_APPLICABLE = ("this film has no authored page — the 原样配音 tier (every beat a supplied slide) or a board of "
                  "programmatic scenes only — so there is no design to judge and no keyframe to pin: the rendered "
                  "review ledger covers the remotion and HTML tiers. On this tier the review at the chosen depth is "
                  "agents/critic-av.md on out.mp4, and it is NOT recorded or checked here.")


def validate(out_dir, final=False):
    errs, warns = [], []
    if film_tier(out_dir) is None:
        # Not a pass: a gate that has nothing to check says so as an ERROR, so no caller can read silence as a review
        return [NOT_APPLICABLE], []
    rv, rprobs = review(out_dir)
    if rprobs:
        errs.extend("the recorded review depth is not usable: " + p for p in rprobs)
    # THE PRE-SELECTION IS COMPUTED, not chosen (preselect): checked at delivery, on every answer the question took
    # — `none` included, since it too was asked with a pre-selected option beside it
    pre_errs = _preselect_problems(out_dir, rv) if final and rv is not None and not rprobs else []
    errs.extend(pre_errs)
    wv, wprobs = waiver(out_dir)
    if wv is not None:
        if wprobs:
            return (sorted(set(errs + ["the review waiver is not usable: " + p for p in wprobs])), [])
        if pre_errs:
            return (pre_errs, [])
        return ([], ["REVIEW WAIVED BY THE USER for this render — no critic judged this film. Reason given: "
                     "%r. The deterministic gates still apply and still gate delivery; this waives taste, "
                     "not whether the file plays." % str(wv.get("reason"))[:160]])
    # NO DEPTH RECORDED IS NOT A DEPTH. It used to mean `thorough` in silence, so a run that never asked the
    # question looked exactly like one where the user chose the full loop.
    no_depth = ("no meta.%s recorded — ask the review-depth question (SKILL.md 9d: fast | standard | thorough "
                "| none) and record the answer before delivery" % REVIEW_KEY) if rv is None and final else None
    path = os.path.join(out_dir, LEDGER_NAME)
    if not os.path.exists(path):
        return (errs + ["no %s — the review produced no per-dimension record. Run with --emit-template, fill every "
                 "row, then re-run this gate." % LEDGER_NAME] + ([no_depth] if no_depth else []), [])
    try:
        led = json.load(open(path, encoding="utf-8"))
    except Exception as e:                                    # noqa: BLE001 - report, don't crash the gate
        return (errs + ["%s is not valid JSON: %s" % (LEDGER_NAME, e)] + ([no_depth] if no_depth else []), [])

    # ── the artifact the reviewer actually looked at ────────────────────────────────────────────────────
    sheet = os.path.join(out_dir, CONTACT_SHEET)
    tier, cap, rnd, spent = capped(out_dir)
    overall = str(led.get("verdict", "")).strip().upper()
    got, renamed = _pin_of(led)
    if renamed:
        warns.append("the ledger's `%s` field was renamed `render_sha256` (the pin now covers the picture, the "
                     "sound and the captions) — read as the pin this time; write `render_sha256`" % LEGACY_PIN)
    current = False
    stale = _stale_sheet(out_dir)
    hist = history_shas(out_dir)
    want = render_id(out_dir) if os.path.exists(sheet) and not stale else ""
    # RE-RENDERED AFTER THE LAST BRIEF: the current render was never briefed, so no review round has seen it and
    # every pin compared with it would be compared with a render the history does not know. It used to surface as
    # "a render this film never had" — true of the PIN only by accident, and silent about the fix.
    rerendered = bool(want) and bool(hist) and want not in hist
    if not os.path.exists(sheet):
        errs.append("%s is missing — run scripts/critic_brief.py first; a review with no contact sheet saw "
                    "no film" % CONTACT_SHEET)
    elif stale:
        errs.append("%s is older than the keyframes — the film was re-rendered and the sheet was not rebuilt, so "
                    "every pin checked against it describes the OLD render. Re-run scripts/critic_brief.py "
                    "<out_dir> (it rebuilds the sheet and records the render), then this gate." % CONTACT_SHEET)
    elif rerendered:
        errs.append("the current render (%s) is not in the render history — the film was re-rendered (its picture, "
                    "sound or captions changed) after the last scripts/critic_brief.py, so no review round has seen "
                    "it. Re-run python3 scripts/critic_brief.py <out_dir> (it rebuilds the sheet and records the "
                    "render), then this gate." % want[:12])
    else:
        if not hist:
            warns.append("no render history (%s) — scripts/critic_brief.py records every render it briefs; without "
                         "it no round can be derived and a re-render cannot be told from this one" % HISTORY)
        current = got == want
        if not got:
            errs.append("render_sha256 is empty — a ledger must be pinned to the render it reviewed "
                        "(--emit-template fills it; --render-id prints it)")
        elif current:
            pass
        elif got == sha256_of(sheet):
            errs.append("this ledger pins the contact sheet ALONE (%s) — the rule before the pin covered sound and "
                        "captions, so it cannot say which narration and captions were reviewed. Re-run "
                        "scripts/critic_brief.py and have the review pinned to the render id (%s)"
                        % (got[:12], want[:12]))
        elif got not in hist:
            errs.append("render_sha256 %s does not match the film's render (%s) — this ledger reviews a "
                        "DIFFERENT render than the one in %s, and not one this film ever had"
                        % (got[:12], want[:12], out_dir))
        elif overall == "PASS":
            # A PASS COVERS THE RENDER IT SAW. Anything changed after it was never judged by anyone.
            errs.append("this PASS reviewed an earlier render (%s), not the current one (%s) — the film changed "
                        "after it passed, and a PASS covers only the render it saw. Review the current render."
                        % (got[:12], want[:12]))
        elif not spent:
            errs.append("render_sha256 %s does not match the film's render (%s) — this ledger reviews an earlier "
                        "render, and the %s tier has rounds left (this was round %s of %s): review the current "
                        "render" % (got[:12], want[:12], tier, rnd if rnd else "?", cap if cap else "unbounded"))
        else:
            # A CAPPED TIER'S LAST ROUND reviewed an earlier render and its fixes were applied; the rows must
            # show every finding resolved (checked below), and the film ships marked as not re-reviewed.
            warns.append("this ledger reviews an earlier render (%s) — the %s tier's round cap is spent, so "
                         "its applied fixes ship without a re-review" % (got[:12], tier))
    if "round" in led:
        warns.append("the ledger's own `round` field is ignored — the round is derived from the render history "
                     "(this ledger's render is round %s)" % (rnd if rnd else "unknown"))

    # ── one row per declared dimension, no more, no fewer ───────────────────────────────────────────────
    declared = film_dimensions(out_dir)
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
    if overall not in ("PASS", "REVISE"):
        errs.append("verdict must be PASS or REVISE")
    failed = sorted(s for s, r in by_id.items() if str(r.get("verdict", "")).lower() == "fail")
    if overall == "PASS" and failed:
        errs.append("verdict is PASS while %s failed" % ", ".join(failed))
    unpinned = stale or rerendered                # no pin can be judged against a render nobody briefed
    history_pin = (bool(got) and not current and not unpinned and os.path.exists(sheet) and got in hist)
    if overall == "REVISE" and spent and not unpinned and (final or history_pin):
        errs.extend(_unresolved(out_dir, by_id, failed, got, current, tier))

    # ── the routes validate.py credited: did the critic SEE them in the frame? (S14) ─────────────────────
    errs.extend(_route_rows(out_dir, led, by_id, warns))

    # ── the machine-gate findings the board waived: is each waiver's reason true of the film? ──────────────────
    errs.extend(_waiver_rows(out_dir, led, by_id, warns))

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
    if no_depth:
        errs.append(no_depth)
    return errs, warns


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: critic_ledger.py <out_dir> [--emit-template] [--final] [--render-id] [--preselect]")
        return 2
    out_dir = os.path.abspath(argv[0])
    if not os.path.isdir(out_dir):
        print("[critic_ledger] no such out_dir: %s" % out_dir)
        return 2
    if "--preselect" in argv:
        # the tier ALONE on the first line, the reason on the second — the reason is said in the question. Asked on
        # every tier, the 原样配音 one included: the review-depth question is, even where no ledger follows it
        tier, why = preselect(out_dir)
        print(tier)
        print("[critic_ledger] pre-select `%s` — %s. Record it as meta.%s.preselected; never `none`, never `thorough`."
              % (tier, why, REVIEW_KEY))
        return 0
    if film_tier(out_dir) is None:
        print("[critic_ledger] NOT APPLICABLE — %s" % NOT_APPLICABLE)
        print("[critic_ledger] nothing was checked: exit 2 is not a pass")
        return 2
    if "--render-id" in argv:
        # The id ALONE on stdout, so the maker can record it as meta.review.render_sha256 for a `none` answer
        # without parsing prose; what it covers goes to stderr. A stale or missing sheet prints no id at all: an id
        # of the OLD picture would pin the user's answer to a cut they did not watch.
        if not os.path.exists(os.path.join(out_dir, CONTACT_SHEET)):
            print("[critic_ledger] no %s — run python3 scripts/critic_brief.py %s first" % (CONTACT_SHEET, out_dir),
                  file=sys.stderr)
            return 2
        if _stale_sheet(out_dir):
            print("[critic_ledger] %s is older than the keyframes — re-run python3 scripts/critic_brief.py %s first"
                  % (CONTACT_SHEET, out_dir), file=sys.stderr)
            return 2
        print(render_id(out_dir))
        print("[critic_ledger] render id over: %s" % ", ".join(
            [CONTACT_SHEET] + [f for f in RENDER_FILES if os.path.isfile(os.path.join(out_dir, f))]), file=sys.stderr)
        return 0
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
    _t, _c, _r, _sp = capped(out_dir)
    print("[critic_ledger] %s tier — %s's %s-dimensions" % (film_tier(out_dir), critic_of(out_dir),
                                                            SERIES[film_tier(out_dir)][1]))
    print("[critic_ledger] review depth: %s%s" % (
        _t, "" if review(out_dir)[0] or wv is not None else
        " (no meta.review recorded — an interim run uses the full loop; --final refuses until the review-depth "
        "question is asked)"))
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
                     "The user waived `%s` for this render (%s in "
                     "storyboard.json).\n\n- **Reason given:** %s\n- **Render this covers:** render id "
                     "`%s` (contact sheet + out.mp4 + out.srt)\n\nNo critic judged %s on this film. The "
                     "deterministic gates DID run and did gate delivery.\n\n"
                     "If this film is re-rendered, the waiver expires with it: the pin above stops matching "
                     "and `critic_ledger.py --final` asks again.\n"
                     % (os.path.basename(critic_of(out_dir))[:-3],
                        "`meta.review` = `none`" if wv.get("_from") == REVIEW_KEY else "`meta.review_waiver`",
                        str(wv.get("reason"))[:400], str(wv.get("render_sha256"))[:16],
                        "register fit, meaning, frame-craft, boldness or direction adherence"
                        if film_tier(out_dir) == "remotion" else
                        "faithfulness on screen, meaning, form fit, frame-craft, motion, the burned captions or the "
                        "design routes"))
        print("[critic_ledger] delivered UNREVIEWED — rewrote NOT_DELIVERED.md to say so")
    elif final and not errs and overall == "REVISE" and capped(out_dir)[3]:
        tier, cap, rnd, _sp = capped(out_dir)
        led = json.load(open(os.path.join(out_dir, LEDGER_NAME), encoding="utf-8"))
        rows = [r for r in led.get("rows") or [] if str(r.get("verdict", "")).lower() == "fail"]
        pin = _pin_of(led)[0]
        acc = accepted(out_dir)

        def _how(r):
            sid = str(r.get("id"))
            if (sid, pin) in acc:
                return "ACCEPTED AS-IS by the user: \"%s\"" % acc[(sid, pin)][:200]
            return "fix applied, not re-reviewed: %s" % str(r.get("applied") or "-")[:200]
        with open(nd, "w", encoding="utf-8") as fh:
            fh.write("# Delivered after a `%s` review — not a PASS\n\n"
                     "The user chose the `%s` review depth (%d round%s; round %s was the last). The critic's last "
                     "round said REVISE on render `%s`; each finding was either fixed in a later render (NOT "
                     "re-reviewed) or accepted as-is by the user, as below.\n\n%s\n\n"
                     "The deterministic gates DID run and did gate delivery.\n"
                     % (tier, tier, cap, "" if cap == 1 else "s", rnd if rnd else "?", pin[:16],
                        "\n".join("- **%s** — %s" % (r.get("id"), _how(r)) for r in rows)))
        print("[critic_ledger] delivered after a %s review (round cap spent) — NOT_DELIVERED.md records it"
              % tier)
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
