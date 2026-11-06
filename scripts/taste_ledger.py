#!/usr/bin/env python3
"""What the user taught the skill about taste, kept so the next film does not need teaching again.

    python3 scripts/taste_ledger.py add --said "<the user's words>" --rule "<the rule>" --stage design [--film F]
    python3 scripts/taste_ledger.py list
    python3 scripts/taste_ledger.py retire <id> --gate "<the gate that now enforces it>"
    python3 scripts/taste_ledger.py brief --stage design|plan|build|render
    python3 scripts/taste_ledger.py check <out_dir>

WHY. Every design correction so far came from the user, not from the skill: header titles on a video ("视频不是
PPT"), one landscape behind a satellite ("卫星的背景怎么可能是山水"), a red timetable palette for satellites, the
native-3D tier ("很烂"). Each became a one-off rule in whichever file the incident touched, and nothing carried the
next mistake of the same KIND. The ledger is that memory: the user's own words, the rule they imply, and the stage
where a director applies it.

SELF-LIMITING (slide-maker's design, 2026-09-08). An entry is RETIRED once a deterministic gate enforces it, so the
ledger only ever holds taste that is taught but not yet gated — the part a director has to carry by reading it.

PRIVATE. The file quotes the user, so it lives at ~/.topic-to-video/taste-ledger.json (TTV_TASTE_LEDGER overrides),
never in this repo, which is public. references/taste-ledger.example.json shows the shape.
"""
import argparse
import json
import os
import re
import sys
import time

STAGES = ("plan", "design", "build", "render")
STATUSES = ("active", "retired")


class LedgerError(Exception):
    """The ledger file exists and cannot be read. Never treated as an empty ledger: an empty one would pass every
    check and the next add would overwrite what the user taught."""


def ledger_path():
    return os.environ.get("TTV_TASTE_LEDGER") or os.path.join(os.path.expanduser("~"), ".topic-to-video",
                                                               "taste-ledger.json")


def load(path=None):
    path = path or ledger_path()
    if not os.path.exists(path):
        return {"version": 1, "entries": []}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise LedgerError("the taste ledger %s cannot be read (%s) — fix or move it; it is not read as empty"
                          % (path, e))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise LedgerError("the taste ledger %s is not {version, entries: [...]}" % path)
    return data


def _save(data, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(s) > 48:                                   # cut on a word: "...its-own-subje" names nothing
        s = s[:49].rsplit("-", 1)[0] if "-" in s[:49] else s[:48]
    return s.rstrip("-") or "rule"


def add(said, rule, stage, film=None, gate=None, path=None):
    """Record one thing the user taught. `said` is their words verbatim; `rule` what a director applies."""
    if stage not in STAGES:
        raise ValueError("stage must be one of %s, got %r" % (", ".join(STAGES), stage))
    if not str(said or "").strip() or not str(rule or "").strip():
        raise ValueError("a taught rule needs the user's words (said) and the rule itself")
    path = path or ledger_path()
    data = load(path)
    taken = {e.get("id") for e in data["entries"]}
    base = _slug(rule)
    eid, n = base, 2
    while eid in taken:
        eid, n = "%s-%d" % (base, n), n + 1
    entry = {"id": eid, "said": str(said), "rule": str(rule).strip(), "stage": stage, "film": film,
             "date": time.strftime("%Y-%m-%d"), "status": "retired" if gate else "active", "gate": gate}
    data["entries"].append(entry)
    _save(data, path)
    return entry


def retire(eid, gate, path=None):
    """The rule is now enforced by `gate`; it leaves the briefs."""
    if not str(gate or "").strip():
        raise ValueError("retiring a rule names the gate that enforces it")
    path = path or ledger_path()
    data = load(path)
    for e in data["entries"]:
        if e.get("id") == eid:
            e["status"], e["gate"] = "retired", str(gate)
            _save(data, path)
            return e
    raise KeyError("no taste rule %r in %s" % (eid, path))


def active(path=None, stage=None):
    return [e for e in load(path)["entries"]
            if e.get("status") == "active" and (stage is None or e.get("stage") == stage)]


def brief(stage, path=None):
    """The active rules a director at `stage` applies, one line each."""
    if stage not in STAGES:
        raise ValueError("stage must be one of %s, got %r" % (", ".join(STAGES), stage))
    return [e["rule"] for e in active(path, stage)]


# Where an answer's artifact may sit: the film's own sheets, proofs and frames — never the segment cache or audio.
_PIN_SKIP_DIRS = {".remotion_segments", "audio", "node_modules", ".assets", "frames"}
WAIVER_NAME = "taste_ledger"                         # meta.delivery_waivers key, as deliver.py and --final read it


def _board_meta(out_dir):
    try:
        with open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("meta") or {}
    except (OSError, ValueError):
        return {}


def _film_shas(out_dir, depth=2):
    import hashlib
    out = set()
    base = os.path.abspath(out_dir)
    for root, dirs, files in os.walk(base):
        rel = os.path.relpath(root, base)
        dirs[:] = [d for d in dirs if d not in _PIN_SKIP_DIRS and (rel == "." or rel.count(os.sep) < depth - 1)]
        for f in files:
            if f == "storyboard.json":
                continue
            h = hashlib.sha256()
            with open(os.path.join(root, f), "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            out.add(h.hexdigest())
    return out


def waived(out_dir):
    """The user's reason when they waived the taste check by name (meta.delivery_waivers), else None."""
    v = (_board_meta(out_dir).get("delivery_waivers") or {}).get(WAIVER_NAME)
    return v.strip() if isinstance(v, str) and v.strip() else None


def check(out_dir, path=None):
    """One problem per ACTIVE rule this film has not answered. An answer is `meta.taste_review[<id>] = {answer,
    sha256}`, the sha256 of a file of THIS film the rule was judged on (the sketch sheet, a proof frame) — the same
    pin the review ledger requires, so an answer cannot be written without looking at something."""
    rules = active(path)
    if not rules:
        return []
    answers = _board_meta(out_dir).get("taste_review") or {}
    shas = None
    probs = []
    for e in rules:
        a = answers.get(e["id"]) if isinstance(answers, dict) else None
        if not isinstance(a, dict) or not str(a.get("answer") or "").strip():
            probs.append("taste rule %s is unanswered for this film — %s (the user said: %s). Judge it on the "
                         "picture and record meta.taste_review[%r] = {answer, sha256 of the file you judged}"
                         % (e["id"], e["rule"], e["said"], e["id"]))
            continue
        if shas is None:
            shas = _film_shas(out_dir)
        if str(a.get("sha256") or "").strip().lower() not in shas:
            probs.append("taste rule %s's answer pins sha256 %s, and no file of this film has it — pin the sheet or "
                         "frame it was judged on" % (e["id"], str(a.get("sha256") or "")[:12] or "(empty)"))
    return probs


def main(argv):
    ap = argparse.ArgumentParser(description="The user's taught taste rules")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--said", required=True)
    a.add_argument("--rule", required=True)
    a.add_argument("--stage", required=True, choices=STAGES)
    a.add_argument("--film")
    a.add_argument("--gate")
    sub.add_parser("list")
    r = sub.add_parser("retire")
    r.add_argument("id")
    r.add_argument("--gate", required=True)
    b = sub.add_parser("brief")
    b.add_argument("--stage", required=True, choices=STAGES)
    c = sub.add_parser("check")
    c.add_argument("out_dir")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "add":
            e = add(args.said, args.rule, args.stage, film=args.film, gate=args.gate)
            print("[taste] added %s (%s)" % (e["id"], e["status"]))
        elif args.cmd == "list":
            for e in load()["entries"]:
                print("%-8s %-7s %-40s %s%s" % (e.get("status"), e.get("stage"), e.get("id"), e.get("rule"),
                                                "  [gate: %s]" % e["gate"] if e.get("gate") else ""))
        elif args.cmd == "retire":
            e = retire(args.id, args.gate)
            print("[taste] retired %s — enforced by %s" % (e["id"], e["gate"]))
        elif args.cmd == "brief":
            lines = brief(args.stage)
            print("[taste] %d taught rule(s) for the %s stage — apply every one:" % (len(lines), args.stage))
            for line in lines:
                print("  - " + line)
        elif args.cmd == "check":
            why = waived(args.out_dir)
            probs = [] if why else check(args.out_dir)
            for p in probs:
                print("[taste] " + p)
            print("[taste] %s" % ("waived by the user: " + why if why else
                                  "%d unanswered taught rule(s)" % len(probs) if probs else "every taught rule answered"))
            return 1 if probs else 0
    except (LedgerError, KeyError, ValueError) as e:
        print("[taste] " + str(e).strip("'\""), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
