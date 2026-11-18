#!/usr/bin/env python3
"""stage_contacts_qa — does anything in a film's 3D stage pass through anything else? Read from the stage, over time.

    python3 scripts/stage_contacts_qa.py <film_dir> [--page film.html] [--every 0.0667] [--json]

For a film page built on assets/html/stage3d.js: steps window.seek(t) through the film and asks every visible stage
(`Stage3D.stages`) for `contacts()` — a panel's face or a character's surface INSIDE a character's body (a carried card
sunk into a head, a card swung through a Bot, two Bots merged), or two panels STACKED in one place and orientation
(they flicker through each other). Exact bodies, not bounding boxes. A contact that lasts two samples or more is
reported with both objects' names (`name:` in panel()/inflate(), else the image's file name) and the time span.

WHY. The Grok Bot film (2026-11-18): a relay card sank into a Bot, the approval card swung through the Bot and its
email, three action cards parked in one place; the user saw each, no check did (page_overlap_qa sees only the DOM).
EXEMPT: an object with userData.contactOk = true (a deliberate hug, a card held against a body).
Exit 0 clean, 1 contacts found, 2 usage error, the page failed to load, or no stage3d stage on it.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402
import _filmpage as _fp  # noqa: E402

_USAGE = "usage: stage_contacts_qa.py <film_dir> [--page film.html] [--every 0.0667] [--json]"

_PROBE = r"""
(() => { const S = (window.Stage3D && window.Stage3D.stages) || []; if (!S.length) return null; const out = [];
  const seen = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false; } return true; };
  S.forEach((st, k) => { if (!seen(st.renderer.domElement)) return; for (const c of st.contacts()) out.push(Object.assign({stage: k}, c)); });
  return out; })()
"""


def spans(samples, every):
    """samples: [(t, [contact...])] -> [(kind, a, b, t0, t1, max_share)] for contacts seen in >= 2 consecutive samples."""
    runs, out = {}, []
    for t, cs in samples:
        now = {(c["kind"], c["a"], c["b"]): c.get("share", 0) for c in cs}
        for k, sh in now.items():
            r = runs.get(k)
            if r and t - r[1] <= every * 1.5:
                r[1], r[2], r[3] = t, max(r[2], sh), r[3] + 1
            else:
                if r and r[3] >= 2:
                    out.append((k[0], k[1], k[2], r[0], r[1] + every, r[2]))
                runs[k] = [t, t, sh, 1]
    for k, r in runs.items():
        if r[3] >= 2:
            out.append((k[0], k[1], k[2], r[0], r[1] + every, r[2]))
    return sorted(out, key=lambda x: x[3])


def main(argv):
    _c.refuse_unknown(argv, valued=("page", "every"), switches=("json",), usage=_USAGE)
    vals = {k: _c.argflag(argv, k, None) for k in ("page", "every")}
    args = [a for a in argv if not a.startswith("--") and a not in vals.values()]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(_USAGE, file=sys.stderr)
        return 2
    d = os.path.abspath(args[0])
    page = vals["page"] or "film.html"
    if not os.path.isfile(os.path.join(d, page)):
        print("stage_contacts_qa: no page at %s" % os.path.join(d, page), file=sys.stderr)
        return 2
    every = float(vals["every"] or 1 / 15)
    n = _fp.film_frames_count(d, 30)
    if not n:
        print("stage_contacts_qa: no _plan.json \"frames\" or timeline.json \"duration\"", file=sys.stderr)
        return 2
    port, srv = _fp.serve(d)
    samples = []
    try:
        p = _fp.FilmPage(port, page)
        try:
            t, k = 0.0, 0
            while t < n / 30.0:
                p.seek(t)
                cs = p.ev(_PROBE)
                if cs is None:
                    print("stage_contacts_qa: no stage3d stage on this page (Stage3D.stages is empty)", file=sys.stderr)
                    return 2
                samples.append((round(t, 4), cs))
                k += 1
                t = k * every
        finally:
            p.close()
    except _fp.PageError as e:
        print("stage_contacts_qa: %s" % e, file=sys.stderr)
        return 2
    finally:
        srv.shutdown()
    found = spans(samples, every)
    if "--json" in argv:
        print(json.dumps({"contacts": [{"kind": k, "a": a, "b": b, "start": round(s, 2), "end": round(e, 2), "share": sh}
                                       for k, a, b, s, e, sh in found]}))
    else:
        for k, a, b, s, e, sh in found:
            what = "into" if k == "penetrates" else "stacked on"
            print("%-10s %6.2f-%6.2fs  %r %s %r  (%.0f%% of its points)" % (k.upper(), s, e, a, what, b, sh * 100))
        print("[stage_contacts_qa] %s  %d contact(s) over %.0f s sampled every %.3f s"
              % ("OK" if not found else "RED", len(found), n / 30.0, every))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
