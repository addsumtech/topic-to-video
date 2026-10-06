"""The DOCUMENTARY image tier — fetch REAL, license-clean images from Wikimedia Commons.

Distinct from `imagegen.py` (AI broll: generic, no facts, atmosphere only): these are REAL
photographs / maps / diagrams that depict the ACTUAL named subject, with license + attribution
captured, so they can be used as FAITHFUL evidence (a real rail map, a real crowded station, a real
cityscape). The design-director picks this treatment per beat for CONCRETE topics where seeing the
real thing lands the point harder than abstract atmosphere.

Source: Wikimedia Commons (huge, real, CC / Public-Domain, attributable, no API key). We accept only
free/attributable licenses and record the attribution alongside each file, so the deck stays faithful
AND license-clean. Optional `duotone()` maps an image to the deck's ink→paper palette so a real photo
blends with a styled deck ("treated to match").
"""
import os, re, sys, json, time, socket, hashlib, http.client, email.utils
import urllib.error, urllib.request, urllib.parse

_API = "https://commons.wikimedia.org/w/api.php"
# a descriptive UA is required by the Wikimedia API etiquette
_UA = "topic-to-video-skill/1.0 (github.com/addsumtech/topic-to-video; documentary image tier)"
# licenses we accept: public-domain or FREE/attributable Creative-Commons. Reject non-free / fair-use
# AND the non-free CC variants: NonCommercial (-nc) and NoDerivatives (-nd) — a deck reuses + often
# DUOTONE-treats (derives) the image commercially-ish, so BY-NC / BY-ND are not safe. _BAD is checked
# FIRST (wins), so "cc by-nc-sa 4.0" matches "-nc" and is rejected even though it contains "cc by".
_OK_LICENSE = ("public domain", "pdm", "cc0", "cc by", "cc-by", "no restrictions", "attribution")
# "-nc"/"-nd" are safe hyphenated substrings — they occur only in the NC/ND CC variants, never in a free
# short-name (CC0 / CC BY / CC BY-SA / Public domain). A leading-space form would risk matching words.
_BAD_LICENSE = ("non-free", "fair use", "fair-use", "copyright", "all rights",
                "noncommercial", "non-commercial", "-nc", "noderiv", "-nd")


# A FAILED REQUEST IS NOT AN EMPTY RESULT. Commons rate-limits a burst of searches with HTTP 429, and
# `fetch()` used to swallow that (and every 5xx, timeout and dropped connection) and return None, which its
# callers read as "nothing license-clean exists" — so a documentary beat was degraded to atmosphere because
# the network was busy for a few seconds. A transient failure is now retried with backoff, honouring the
# server's Retry-After; one that persists raises FetchError, which says what failed and that it is not a
# search result. None keeps exactly one meaning: Commons answered and nothing usable was in the answer.
_RETRIES = 3                  # after the first try — four attempts in all
_BACKOFF_S = 1.5              # the first wait; it doubles on each retry (1.5, 3, 6 seconds)
_RETRY_AFTER_CAP_S = 30.0     # a server's Retry-After is honoured up to this many seconds per wait
_TRANSIENT_HTTP = (429, 500, 502, 503, 504)
_sleep = time.sleep           # a module attribute so a test can record the waits instead of sleeping them


class FetchError(RuntimeError):
    """A Commons request that failed — rate-limited, a server error, the network — rather than answered.

    `kind` is 'rate-limit', 'server', 'network' or 'error'. It is never a finding about the images that
    exist: the message says so, and says to run it again."""

    def __init__(self, message, kind="error"):
        super().__init__(message)
        self.kind = kind


def _transient(err):
    """True for a failure worth waiting out: HTTP 429/5xx, a timeout, a dropped or refused connection."""
    if isinstance(err, urllib.error.HTTPError):          # an HTTPError is also a URLError — decide it first
        return err.code in _TRANSIENT_HTTP
    return isinstance(err, (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError,
                            http.client.IncompleteRead, http.client.RemoteDisconnected))


def _kind(err):
    if isinstance(err, urllib.error.HTTPError):
        return "rate-limit" if err.code == 429 else "server" if err.code >= 500 else "error"
    return "network" if _transient(err) else "error"


def _describe(err):
    if isinstance(err, urllib.error.HTTPError):
        return "HTTP %d %s" % (err.code, err.reason or "")
    return "%s: %s" % (type(err).__name__, getattr(err, "reason", None) or err)


def _wait_for(err, attempt):
    """Seconds to wait before retry `attempt` (0-based): the server's Retry-After when it sent one — as
    delta-seconds or an HTTP date — capped at _RETRY_AFTER_CAP_S, else exponential backoff."""
    after = None
    headers = getattr(err, "headers", None)
    raw = headers.get("Retry-After") if headers is not None else None
    if raw:
        raw = str(raw).strip()
        if raw.isdigit():
            after = float(raw)
        else:
            try:
                when = email.utils.parsedate_to_datetime(raw)
                after = when.timestamp() - time.time()
            except (TypeError, ValueError, IndexError, OverflowError):
                after = None
    if after is not None:
        return max(0.0, min(_RETRY_AFTER_CAP_S, after))
    return _BACKOFF_S * (2 ** attempt)


def _failure(what, err, tries=1):
    kind = _kind(err)
    reason = {"rate-limit": "Wikimedia is rate-limiting these requests",
              "server": "the Wikimedia server answered with an error",
              "network": "the network request did not complete",
              "error": "the request was refused or its answer could not be read"}[kind]
    return FetchError("%s failed after %d attempt%s: %s — %s. This is a failed request, NOT a finding that "
                      "no license-clean image exists; wait a minute and run it again."
                      % (what, tries, "" if tries == 1 else "s", _describe(err), reason), kind)


def _get(url, timeout, what):
    """GET `url` and return its bytes, retrying a transient failure (see the note above). A transient
    failure that outlasts the retries raises FetchError; any other error propagates as it is, so a caller can
    tell "this one file is gone" (a 404) from "the service is unreachable"."""
    last = None
    for attempt in range(_RETRIES + 1):
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                       # noqa: BLE001 — sorted into transient or not just below
            if not _transient(e):
                raise
            last = e
            if attempt < _RETRIES:
                _sleep(_wait_for(e, attempt))
    raise _failure(what, last, _RETRIES + 1)


def _strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _license_ok(lic):
    l = (lic or "").lower()
    if any(b in l for b in _BAD_LICENSE):
        return False
    return any(h in l for h in _OK_LICENSE)


def _http_json(params, timeout=30, api=None):
    url = (api or _API) + "?" + urllib.parse.urlencode(params)
    return json.loads(_get(url, timeout, "the Commons API request"))


def resolve_concept(term, timeout=12):
    """The Wikidata entity a term names — {qid, label, description} — or None.

    WHY. A plain Commons text search matches the FILE PAGE's words, so an abstract term lands on whatever
    document happens to use it. Measured: `imagefetch.py "trust"` returned a 1911 political cartoon,
    '"GOOD TRUST" "BAD TRUST" in Tariff Alley', from The Masses — licence-clean, high resolution, and about
    a different sense of the word.

    ADVISORY ONLY — DO NOT AUTO-APPLY. Resolution is unreliable and was measured to be: the top entity for
    "trust" is Q1641993, a FRENCH ROCK BAND, so wiring this into fetch() would have replaced one wrong
    picture with a worse one; and multi-word phrases ("bicycle workshop", "office worker computer") resolve
    to nothing at all. Even with a hand-verified QID the depicts filter is not clearly better: on
    "magnetic resonance imaging" (Q161238) the plain text search returned an angiogram and an MRI slice while
    the filtered search returned a Bruker scanner and two menstrual-cup studies. So this returns the
    candidate WITH its description for a caller to JUDGE, and `search(depicts=...)` takes a QID a caller has
    already decided on. Automatic relevance for an abstract term is not solved here, and pretending it is
    would put a confidently wrong photograph on a frame.
    """
    try:
        d = _http_json({"action": "wbsearchentities", "format": "json", "language": "en",
                        "uselang": "en", "type": "item", "limit": 1, "search": term},
                       api="https://www.wikidata.org/w/api.php", timeout=timeout)
    except Exception:                                            # noqa: BLE001 — offline is not a failure here
        return None
    hits = d.get("search") or []
    if not hits:
        return None
    h = hits[0]
    return {"qid": h.get("id"), "label": h.get("label"), "description": h.get("description")}


def search(query, limit=10, width=1600, depicts=None):
    """Search Commons files (namespace 6) for `query`; return candidate dicts with a renderable URL
    (SVG is auto-rendered to a PNG thumb by Commons), mime, license and attribution.

    `depicts` is a Wikidata QID. When given, the search is restricted to files that DECLARE they depict it
    (`haswbstatement:P180=<qid>`), which is a statement about the picture rather than about the words on its
    file page — the difference between a photograph of the subject and a document that mentions it.
    """
    term = ("haswbstatement:P180=%s " % depicts + query) if depicts else query
    d = _http_json({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": term, "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size", "iiurlwidth": width,
    })
    out = []
    for p in ((d.get("query") or {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii:
            continue
        mime = ii.get("mime", "")
        # accept raster + svg (Commons gives a rendered PNG thumburl for svg); skip pdf/tiff/video
        if not (mime.startswith("image/") and ("jpeg" in mime or "png" in mime or "svg" in mime)):
            continue
        em = ii.get("extmetadata") or {}
        out.append({
            "title": p.get("title"),
            "url": ii.get("thumburl") or ii.get("url"),
            "mime": mime,
            "license": _strip_html((em.get("LicenseShortName") or {}).get("value", "")),
            "artist": _strip_html((em.get("Artist") or {}).get("value", "")),
            "credit": _strip_html((em.get("Credit") or {}).get("value", "")),
            "source": ii.get("descriptionurl"),
            "width": ii.get("thumbwidth") or ii.get("width"),
            "height": ii.get("thumbheight") or ii.get("height"),
        })
    return out


def _download(url, out_path, timeout=60):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    data = _get(url, timeout, "downloading %s" % url)
    if len(data) < 1024:
        raise ValueError("download too small")
    with open(out_path, "wb") as f:
        f.write(data)


def fetch(query, out_path, width=1600, prefer=None, min_width=800, require_license=True):
    """Search + download the best license-clean image for `query` → out_path, and write a sidecar
    `out_path + '.json'` with {title, license, artist, source, query} (the ATTRIBUTION — a documentary
    image must carry it). `prefer` biases toward candidates whose title contains that substring
    (e.g. 'map'). Returns the attribution dict, or None when Commons ANSWERED and nothing in the answer was
    license-clean, wide enough and downloadable. Raises FetchError when Commons could not be asked — a rate
    limit, a server error, the network — which is never the same thing as "nothing exists".
    Faithfulness: the caller must ensure the QUERY genuinely names the beat's subject — this returns a
    real image OF that subject, so a wrong/over-specific query is a faithfulness risk, not a crash."""
    try:
        cands = search(query, limit=12, width=width)
    except FetchError:
        raise
    except Exception as e:                           # noqa: BLE001 — a refusal or an unreadable answer
        raise _failure("the Commons search for %r" % query, e) from e
    if require_license:
        cands = [c for c in cands if _license_ok(c["license"])]
    cands = [c for c in cands if (c.get("width") or 0) >= min_width]
    if prefer:
        cands.sort(key=lambda c: 0 if prefer.lower() in (c["title"] or "").lower() else 1)
    for c in cands:
        if not c.get("url"):
            continue
        try:
            _download(c["url"], out_path)
        except FetchError:
            raise          # the service, not this file — every other candidate would wait out the same failure
        except Exception:  # noqa: BLE001 — this one file is unusable (gone, too small): try the next candidate
            continue
        meta = {"title": c["title"], "license": c["license"], "artist": c["artist"],
                "credit": c["credit"], "source": c["source"], "query": query}
        with open(out_path + ".json", "w") as f:
            json.dump(meta, f, indent=2)
        return meta
    return None


def attribution_line(meta):
    """A compact on-screen/credits attribution string from a fetch() meta dict (or its .json path)."""
    if isinstance(meta, str):
        meta = json.load(open(meta))
    who = meta.get("artist") or meta.get("credit") or "Wikimedia Commons"
    lic = meta.get("license") or ""
    who = re.sub(r"\s+", " ", who)[:80]
    return f"{who} · {lic} · Wikimedia Commons".strip(" ·")


def duotone(in_path, out_path, shadow=(22, 20, 18), highlight=(245, 242, 234), mid=None):
    """Map an image to a two-tone ramp (shadows→`shadow`, highlights→`highlight`) so a real photo/map
    blends with a styled deck — the 'treated to match' look. Defaults map to a dark-ink→warm-paper
    ramp (cartographic/editorial). Pass a `mid` accent tone for a tri-tone warm map. Needs PIL."""
    from PIL import Image
    g = Image.open(in_path).convert("L")

    def ramp(ch):
        if mid is None:
            return [round(shadow[ch] + (highlight[ch] - shadow[ch]) * (i / 255)) for i in range(256)]
        # shadow -> mid (0..0.5) -> highlight (0.5..1) for a warmer, less flat map
        out = []
        for i in range(256):
            t = i / 255
            if t < 0.5:
                v = shadow[ch] + (mid[ch] - shadow[ch]) * (t / 0.5)
            else:
                v = mid[ch] + (highlight[ch] - mid[ch]) * ((t - 0.5) / 0.5)
            out.append(round(v))
        return out

    img = Image.merge("RGB", [g.point(ramp(ch)) for ch in range(3)])
    img.save(out_path)
    return out_path


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Fetch a real license-clean Commons image (documentary tier).")
    ap.add_argument("query")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--prefer", default=None)
    ap.add_argument("--duotone", nargs=2, metavar=("SHADOW", "HIGHLIGHT"), default=None,
                    help="hex shadow + highlight, e.g. --duotone '#161412' '#f5f2ea'")
    a = ap.parse_args()
    try:
        meta = fetch(a.query, a.out, width=a.width, prefer=a.prefer)
    except FetchError as e:
        # exit 2, not 1: the search never ran to an answer, so nothing may be concluded about the subject
        print(f"[imagefetch] FAILED, no answer from Commons ({e.kind}) for: {a.query}\n             {e}",
              file=sys.stderr)
        raise SystemExit(2)
    if not meta:
        print(f"[imagefetch] no license-clean image found for: {a.query}")
        raise SystemExit(1)
    if a.duotone:
        duotone(a.out, a.out, shadow=_hex_rgb(a.duotone[0]), highlight=_hex_rgb(a.duotone[1]))
    print(f"[imagefetch] {a.out}  <-  {meta['title']}  [{meta['license']}]")
    print(f"             {attribution_line(meta)}")


if __name__ == "__main__":
    main()
