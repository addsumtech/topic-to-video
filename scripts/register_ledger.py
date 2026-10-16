"""Cross-deck REGISTER MEMORY — the fix for silent aesthetic convergence across videos.

A single-shot pipeline forgets what the last video looked like, so consecutive decks drift toward the
same register (the amber-terminal repeat). This ledger records each delivered deck's expressive
identity in `~/.slides-to-video/recent.json` (override dir via SLIDES_TO_VIDEO_HOME), and the contest
step reads it to (a) tell Phase A the recent registers so candidates don't clone them BY DEFAULT, and
(b) surface an explicit **distinct vs house** choice to the USER at the pick (per the design decision:
memory surfaces a choice — it never auto-penalizes a style that fits the topic).

CLI:  record <out_dir>   — append this deck's register (reads design_plan.json + storyboard.json + theme.css)
      show [--json] [-n N] — newest-first recent entries
API:  record(out_dir), recent(n=5)
"""
import argparse
import json
import os
import re
import time

_KEEP = 12


def _home():
    return os.environ.get("SLIDES_TO_VIDEO_HOME") or os.path.expanduser("~/.slides-to-video")


def _path():
    return os.path.join(_home(), "recent.json")


def _load():
    try:
        data = json.load(open(_path(), encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _remotion_entry(out_dir, meta):
    """A REMOTION film's register — its chosen DIRECTION. The tier has no design_plan.json, so `record` returned None
    for every remotion film and the next contest could never see what the last one looked like (on the GPS test
    film: "nothing to record"). The direction, its DNA's ground and accent, and the contest's own pitch and ideal
    are the same facts the html entry carries."""
    key = meta.get("shot_template")
    if not key:
        return None
    dna = meta.get("design_dna") if isinstance(meta.get("design_dna"), dict) else {}
    tc = meta.get("shot_template_contest") if isinstance(meta.get("shot_template_contest"), dict) else {}
    d = (tc.get("directions") or {}).get(key) if isinstance(tc.get("directions"), dict) else None
    bg, accent, mode = str(dna.get("bg") or ""), str(dna.get("accent") or "").lower(), ""
    if re.match(r"^#[0-9a-fA-F]{6}$", bg):
        mode = "dark" if int(bg[1:3], 16) * 3 + int(bg[3:5], 16) * 6 + int(bg[5:7], 16) < 1200 else "light"
    return {
        "when": time.strftime("%Y-%m-%d"),
        "deck": os.path.basename(os.path.abspath(out_dir)),
        "register": str(key)[:80],
        "motion": "",
        "style": "remotion",
        "angle": str((d or {}).get("ideal") or "")[:120],
        "mode": mode,
        "accent": accent if re.match(r"^#[0-9a-f]{6}$", accent) else "",
        "language": str(meta.get("language") or ""),
        "brand": os.path.basename(str(((meta.get("brand") or {}).get("logo")) or ""))
                 if isinstance(meta.get("brand"), dict) else "",
    }


def _store(entry):
    entries = [e for e in _load() if e.get("deck") != entry["deck"]]   # re-delivering a deck updates it
    entries.insert(0, entry)
    os.makedirs(_home(), exist_ok=True)
    json.dump(entries[:_KEEP], open(_path(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return entry


def record(out_dir):
    """Append this deck's register identity; returns the entry (or None when there's nothing to record — an html
    deck without a design_plan.json, or a remotion film with no chosen direction)."""
    try:
        meta = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {}
    except (OSError, ValueError, AttributeError):
        meta = {}
    if str(meta.get("renderer") or "") in ("remotion", "remotion-bespoke"):
        e = _remotion_entry(out_dir, meta)
        return _store(e) if e else None
    try:
        plan = json.load(open(os.path.join(out_dir, "design_plan.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(plan, dict):
        return None
    reg = plan.get("design_register") or {}
    if not (isinstance(reg, dict) and reg.get("name")):
        return None
    meta = {}
    try:
        meta = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8")).get("meta") or {}
    except (OSError, ValueError):
        pass
    mode = accent = ""
    try:
        css = open(os.path.join(out_dir, "theme.css"), encoding="utf-8").read()
        m = re.search(r"--bg:\s*(#[0-9a-fA-F]{6})", css)
        if m:
            bg = m.group(1)
            mode = "dark" if int(bg[1:3], 16) * 3 + int(bg[3:5], 16) * 6 + int(bg[5:7], 16) < 1200 else "light"
        m = re.search(r"--accent:\s*(#[0-9a-fA-F]{6})", css)
        if m:
            accent = m.group(1).lower()
    except OSError:
        pass
    contest = plan.get("register_contest") or {}
    entry = {
        "when": time.strftime("%Y-%m-%d"),
        "deck": os.path.basename(os.path.abspath(out_dir)),
        "register": str(reg.get("name") or "")[:80],
        "motion": str(reg.get("motion_personality") or "").split("—")[0].split(":")[0].strip()[:40],
        "style": str(plan.get("visual_style") or "")[:40],
        "angle": next((str(c.get("angle") or "") for c in (contest.get("candidates") or [])
                       if isinstance(c, dict) and str(c.get("key")) == str(contest.get("winner"))), ""),
        "mode": mode,
        "accent": accent,
        "language": str(meta.get("language") or ""),
        # a branded HOUSE series shares its accent by mandate — the marker lets the contest dispatch
        # read same-brand recents as continuity, not convergence to avoid
        "brand": os.path.basename(str(((meta.get("brand") or {}).get("logo")) or ""))
                 if isinstance(meta.get("brand"), dict) else "",
    }
    return _store(entry)


def recent(n=5):
    return _load()[:max(0, int(n))]


def main():
    ap = argparse.ArgumentParser(description="cross-deck register memory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("out_dir")
    s = sub.add_parser("show"); s.add_argument("-n", type=int, default=5); s.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.cmd == "record":
        e = record(a.out_dir)
        print(json.dumps(e, ensure_ascii=False) if e else "[ledger] nothing to record (no committed design_register, "
              "and no remotion direction in meta.shot_template)")
    else:
        es = recent(a.n)
        if a.json:
            print(json.dumps(es, ensure_ascii=False))
        elif not es:
            print("[ledger] empty — no recent decks recorded")
        else:
            for e in es:
                print(f"  {e.get('when','')}  {e.get('deck','')}: 「{e.get('register','')}」 "
                      f"style={e.get('style','')} mode={e.get('mode','')} accent={e.get('accent','')} "
                      f"motion={e.get('motion','')}")


if __name__ == "__main__":
    main()
