#!/usr/bin/env python3
"""Capture the SOURCE TEXT behind every claim, so a brief can be checked against what was
actually read rather than trusted.

The hole this closes: when the comprehension brief is built from web research or from a
document that is never persisted, `brief.json` becomes the only record of what the material
said. Nothing downstream can verify it. A content critic reviewing a real deck put it exactly:

    "no raw source documents exist in the workdir, so I audited brief.json as an ARTIFACT …
     but could not independently re-verify its web-sourced figures."

That is the one place in the pipeline where a wrong INPUT yields a fully-green output: the
gates check the brief's internal consistency, the plans inherit it, and 40 beats carry the
error with every check passing. Persisting the extracts turns `source_ref` from a free-text
string nobody reads into a pointer a critic (or a human, months later) can follow.

Each source also carries a **`tier`** — how hard the evidence is:

    primary    the thing itself: official docs, the paper, the repo, the filing, the spec
    secondary  reporting ABOUT it: news, analyst notes, vendor blogs
    community  experience reports: forum posts, tutorials, comments, "I tested it and got X"
    self       material the user handed over directly

Tier is not a quality score — a community post can be right and a vendor page can be stale. It
records WHERE a claim's support comes from, so "this number rests only on tutorials" becomes
visible to a critic instead of living in the researcher's head. Paired with `as_of` (the date a
time-sensitive fact was true, distinct from `fetched`, when the text was pulled), it lets
`brief_qa` flag the two failure modes that actually bite: a figure backed by no primary source,
and a figure with no date on a page that may itself be stale.

Layout — `<out_dir>/sources/`:
    sources/index.json          {sid → {origin, kind, tier, fetched, as_of, title, chars}}
    sources/<sid>.txt           the extract, verbatim, as it was read

`sid` is a short stable slug. An evidence item then carries `source_ref: "<sid>#<anchor>"`,
where `<anchor>` is a literal substring of that extract — so `brief_qa` can confirm the
claim's support EXISTS in the captured text, not merely that a citation was typed.

Usage
  python scripts/sources.py add <out_dir> --sid tencent-overview \\
        --origin https://… --kind web --title "WorkBuddy 简介" --text-file extract.txt
  python scripts/sources.py add <out_dir> --sid paper --origin ./paper.pdf --kind pdf \\
        --title "…" --pages 3-9 --text-file extract.txt
  python scripts/sources.py list <out_dir>
  python scripts/sources.py verify <out_dir> --ref "tencent-overview#交付可验收的结果"

API: `add(out_dir, sid, text, origin, kind, title, extra, fetched, tier, as_of)` ·
     `load(out_dir)` · `resolve(out_dir, ref)` -> (ok, detail) · `meta_of(out_dir, ref)
"""
import argparse, json, os, re, sys

SOURCES_DIR = "sources"
INDEX = "index.json"


def _dir(out_dir):
    return os.path.join(out_dir, SOURCES_DIR)


def _index_path(out_dir):
    return os.path.join(_dir(out_dir), INDEX)


def load(out_dir):
    """→ {sid: meta}; {} when nothing has been captured."""
    try:
        with open(_index_path(out_dir), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def text_of(out_dir, sid):
    try:
        with open(os.path.join(_dir(out_dir), sid + ".txt"), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


TIERS = ("primary", "secondary", "community", "self")


def add(out_dir, sid, text, origin, kind="web", title="", extra=None, fetched=None,
        tier="secondary", as_of=None):
    """Persist one extract verbatim. `fetched`/`as_of` must be supplied by the caller (the
    pipeline knows today's date); they are recorded, never invented here.

    `tier` defaults to "secondary" deliberately: an unlabelled source is NOT assumed to be the
    thing itself. Claiming primary status has to be a decision someone made."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", sid or ""):
        raise ValueError("sid must be a short lowercase slug (a-z 0-9 . _ -)")
    if not (text or "").strip():
        raise ValueError("refusing to record an empty extract — capture what you actually read")
    os.makedirs(_dir(out_dir), exist_ok=True)
    with open(os.path.join(_dir(out_dir), sid + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    idx = load(out_dir)
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS} — it records WHERE the support comes from")
    meta = {"origin": origin, "kind": kind, "tier": tier, "title": title, "chars": len(text)}
    if as_of:
        meta["as_of"] = as_of
    if fetched:
        meta["fetched"] = fetched
    if extra:
        meta.update(extra)
    idx[sid] = meta
    with open(_index_path(out_dir), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return meta


def _norm(s):
    # match on visible characters: whitespace and the CJK/ASCII punctuation that varies between
    # a page's rendering and a hand-typed citation must not decide whether support exists.
    return re.sub(r"[\s，,。.、；;：:！!？?（）()「」『』\"'’“”\-–—]+", "", s or "")


def resolve(out_dir, ref):
    """(ok, detail) for one `source_ref`.

    A ref is `<sid>` or `<sid>#<anchor>`. With an anchor, the anchor must appear in the captured
    extract — that is what makes the citation checkable rather than decorative.
    """
    if not (ref or "").strip():
        return False, "empty source_ref"
    idx = load(out_dir)
    if not idx:
        return True, "no sources/ captured — nothing to check against (advisory)"
    sid, _, anchor = str(ref).partition("#")
    sid = sid.strip()
    if sid not in idx:
        return False, f"unknown source id '{sid}' (sources/index.json has: {', '.join(sorted(idx)[:6])}…)"
    if not anchor.strip():
        return True, f"'{sid}' exists (no anchor given — the claim is not pinned to a passage)"
    body = text_of(out_dir, sid)
    if body is None:
        return False, f"sources/{sid}.txt is missing though the index lists it"
    # NOTE the boundary: a substring match proves the passage EXISTS in what was read; it does not
    # prove the source ASSERTS it. An anchor quoted out of a negated sentence ("并非交付可验收的结果")
    # still matches. That is deliberate — the mechanical gate exists to stop a FABRICATED figure, and
    # judging whether the source actually claims the thing stays with critic-content, which reads the
    # extract. Widening this into semantic judgement would trade a reliable check for an unreliable one.
    if _norm(anchor) in _norm(body):
        return True, f"anchor found in '{sid}'"
    return False, (f"anchor not found in '{sid}' — the captured text does not contain "
                   f"\"{anchor[:40]}\"; quote the source, or fix the claim")


def meta_of(out_dir, ref):
    """The index entry a `source_ref` points at, or None. Accepts `<sid>` or `<sid>#<anchor>`."""
    sid = str(ref or "").partition("#")[0].strip()
    return load(out_dir).get(sid)


# A claim is TIME-SENSITIVE when its truth has a shelf life: a price, a version, a count, a date,
# or an explicit "currently". Those are the ones that go stale silently — the pricing page in one
# real run still said "effective July 1" three weeks after July 1, and only a human noticed.
_TIME_SENSITIVE = re.compile(
    r"(?:[¥$€£]\s*\d|\d+\s*(?:元|美元|块)|/\s*(?:月|年|mo|month|yr|year)|每月|每年"
    r"|\bv?\d+\.\d+(?:\.\d+)?\b|版本|\b20\d\d\b|\d+\s*(?:万|亿|million|billion|k\b)"
    r"|目前|现在|最新|当前|如今|latest|currently|as of|至今|截至)", re.I)


def is_time_sensitive(text):
    return bool(_TIME_SENSITIVE.search(str(text or "")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="capture one extract")
    a.add_argument("out_dir"); a.add_argument("--sid", required=True)
    a.add_argument("--origin", required=True, help="URL or file path the text came from")
    a.add_argument("--kind", default="web", choices=["web", "pdf", "doc", "code", "notes", "transcript", "image"])
    a.add_argument("--title", default=""); a.add_argument("--fetched", default="")
    a.add_argument("--tier", default="secondary", choices=list(TIERS),
                   help="primary = the thing itself · secondary = reporting about it · "
                        "community = experience reports · self = user-supplied")
    a.add_argument("--as-of", dest="as_of", default="",
                   help="date a TIME-SENSITIVE fact was true (a page fetched today can itself be stale)")
    a.add_argument("--pages", default="", help="page range, for a pdf/doc extract")
    src = a.add_mutually_exclusive_group(required=True)
    src.add_argument("--text-file"); src.add_argument("--text")
    l = sub.add_parser("list", help="what has been captured"); l.add_argument("out_dir")
    v = sub.add_parser("verify", help="resolve one source_ref"); v.add_argument("out_dir"); v.add_argument("--ref", required=True)
    args = ap.parse_args()

    if args.cmd == "add":
        text = args.text if args.text else open(args.text_file, encoding="utf-8").read()
        extra = {"pages": args.pages} if args.pages else None
        m = add(args.out_dir, args.sid, text, args.origin, args.kind, args.title, extra,
                args.fetched or None, args.tier, args.as_of or None)
        print(f"[sources] captured '{args.sid}' [{m['tier']}] ({m['chars']} chars) from {args.origin}")
    elif args.cmd == "list":
        idx = load(args.out_dir)
        if not idx:
            print("[sources] nothing captured"); return 0
        for sid, m in sorted(idx.items()):
            print(f"  {sid:<26} {m.get('tier','?'):<10} {m.get('kind',''):<8} "
                  f"{m.get('chars',0):>6} chars  {m.get('as_of','') or m.get('fetched',''):<12} {m.get('origin','')[:48]}")
        tiers = {}
        for m in idx.values():
            tiers[m.get("tier", "?")] = tiers.get(m.get("tier", "?"), 0) + 1
        print("  " + " · ".join(f"{k}: {v}" for k, v in sorted(tiers.items())))
    else:
        ok, detail = resolve(args.out_dir, args.ref)
        print(("  OK   " if ok else "  FAIL ") + detail)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
