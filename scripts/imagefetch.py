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
    import html as _html
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def _artist(s):
    """The author's name off a Commons Artist field. The field often carries a template box after the name (a
    "valid SVG" badge, an "own work" table): its text is not the author, and attribution_line printed it on screen
    ("Fred the Oyster iThe source code of this SVG is valid..."). The name comes before the first block element."""
    return _strip_html(re.split(r"(?i)<(?:div|table)\b", s or "", maxsplit=1)[0])


def _em(em, key, every=False):
    """One extmetadata field as text. Asked with multilang, a translated field arrives as {lang: text} (plus a
    `_type` marker): `every` joins all languages (for matching); otherwise English, else the first one."""
    v = (em.get(key) or {}).get("value", "")
    if isinstance(v, dict):
        langs = {k: t for k, t in v.items() if not k.startswith("_") and isinstance(t, str)}
        if every:
            return " | ".join(langs.values())
        return langs.get("en") or next(iter(langs.values()), "")
    return v if isinstance(v, str) else str(v)


def _real_size(ii, mime, axis):
    """The pixels a candidate can really deliver on `axis`: its thumb's, capped by the original's on a raster, and by
    the width the thumb URL itself names. Commons answers thumbwidth = the REQUESTED width while the URL it hands
    back can be a smaller standard size: a 1255 px tiff asked for at 1600 came back as `lossy-page1-960px-...jpg`
    with thumbwidth 1600. The URL is the file that will be downloaded."""
    thumb, orig = ii.get("thumb" + axis), ii.get(axis)
    m = re.search(r"/(?:lossy-|lossless-)?(?:page\d+-)?(\d+)px-[^/]*$", (ii.get("thumburl") or "").split("?")[0])
    if m and thumb:
        url_w, tw = int(m.group(1)), ii.get("thumbwidth") or 0
        if tw and url_w < tw:
            thumb = round(thumb * url_w / tw)        # both axes shrink by the URL's own ratio
    if "svg" in (mime or "") or not orig:
        return thumb or orig
    return min(thumb, orig) if thumb else orig


# ── relevance: does the file's own record name the subject? ────────────────────────────────────────────────
# A Commons text search matches the WHOLE file page, so a candidate can rank for a query while depicting something
# else. Measured (2026-10-30 validation): "lever escapement" returned 'Britannica Pianoforte Erard Double Escapement
# Action' — a piano — whose title says "escapement" and whose description prose says "...pressing the hinged lever
# upwards". Two defects stacked: search() walked the answer in PAGE-ID order (the API's `pages` is a dict keyed by
# id; the rank is the separate `index`), so the oldest upload went first and Commons' own 8th-ranked hit became
# ours 1st; and nothing asked whether the picture's record names the subject at all.
#
# The rule. Every KEY TERM of the query must be ATTESTED by the file's record. The title, object name and categories
# are statements about the picture, and a term found there is attested. The description is prose that mentions
# other things ("a hinged lever"), so it attests only when it contains the WHOLE required phrase, in order — then it
# names the subject. A candidate missing a term is rejected and the rejection says which term and where it looked.
# Words that name a FORMAT rather than a subject ("diagram", "photo", "close-up", "map") are not required — the subject
# is — but a candidate whose record carries them ranks first, since the author asked for that kind of picture.
# This judges words, not pixels: an ambiguous term ("jaguar") passes for every sense it has, so name the sense in the
# query ("jaguar cat") — and when nothing attests every term, fetch() returns None and says so rather than handing
# back the nearest wrong picture.
_STOPWORDS = frozenset(
    "a an the of in on at for with and or to from by as is its his her their this that these those "
    "de la le les des du un une et en der die das den dem und von vom zu im am ein eine el los las y del "
    "il lo gli di da e".split())
_FORMAT_WORDS = frozenset(
    "diagram diagrams photo photos photograph photographs photography picture pictures image images "
    "illustration illustrations drawing drawings sketch close closeup up detail details view views schematic "
    "scheme svg png jpg jpeg macro shot map maps chart charts infographic".split())
_CJK = r"぀-ヿ㐀-䶿一-鿿가-힯豈-﫿"
_TOKEN = re.compile(r"[%s]+|[^\W_]+" % _CJK)


def _fold(s):
    """Lowercase, strip accents (Glashütte ~ glashutte), unescape HTML — the form every comparison is made in."""
    import unicodedata
    s = unicodedata.normalize("NFKD", _strip_html(s or "").casefold())     # casefold: ß -> ss
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _is_cjk(tok):
    return bool(re.match(r"[%s]" % _CJK, tok))


def key_terms(query):
    """(required, format) terms of `query`. Raises ValueError when nothing in it names a subject — a query of only
    stopwords and format words cannot be checked for relevance, and fetching for it would return anything."""
    req, fmt = [], []
    for t in _TOKEN.findall(_fold(query)):
        if t in _STOPWORDS or (len(t) == 1 and not _is_cjk(t)):
            continue                                  # a lone letter ("E" of E-Type) cannot be attested
        (fmt if t in _FORMAT_WORDS else req).append(t)
    if not req:
        raise ValueError("query %r names no subject (only stopwords / format words %r): relevance cannot be "
                         "checked, so nothing would be refused" % (query, fmt))
    return req, fmt


def _same_word(term, word):
    """A term matches a word when they are equal; when the longer is the shorter plus a plural (fox~foxes,
    bee~bees); or when one is the other plus a short inflection on a stem of at least 4 letters (escapement~
    escapements, rail~railway, spiral~spirale). A CJK term is a run of glyphs and matches where that run occurs
    inside the word (CJK is not space-delimited)."""
    if _is_cjk(term):
        return term in word
    if term == word:
        return True
    short, long_ = (term, word) if len(term) <= len(word) else (word, term)
    if len(short) >= 3 and long_ in (short + "s", short + "es"):
        return True
    return len(short) >= 4 and long_.startswith(short) and len(long_) - len(short) <= 3


def _attested(term, text):
    """True when a word of `text` — or two adjacent words written as one (hair spring ~ hairspring) — is `term`."""
    words = _TOKEN.findall(text)
    if any(_same_word(term, w) for w in words):
        return True
    return not _is_cjk(term) and any(_same_word(term, a + b) for a, b in zip(words, words[1:]))


def _phrase_in(terms, text):
    """True when `text` contains `terms` as consecutive words, each matched by _same_word."""
    words = _TOKEN.findall(text)
    n = len(terms)
    return any(all(_same_word(terms[j], words[i + j]) for j in range(n)) for i in range(len(words) - n + 1))


def _record_fields(cand):
    title = _fold(re.sub(r"(?i)^file:|\.[a-z0-9]{2,4}$", "", cand.get("title") or ""))
    return (("title", title), ("object name", _fold(cand.get("object_name"))),
            ("categories", _fold((cand.get("categories") or "").replace("|", " | "))))


def relevance(cand, required, fmt=()):
    """Judge one candidate. Returns {ok, tier, where: {term: field}, missing: [term], format_hits, why}.

    tier 0: every term attested by the RECORD (title, object name, categories — statements about the picture);
    tier 1: attested only because the description contains the whole phrase. Within a tier the order is Commons'
    own rank, which weighs far more than this does; the tier only says how direct the evidence is.
    `format_hits` counts the query's format words ("diagram", "map") the record or description carries.
    `why` is one line a reader can act on."""
    fields = _record_fields(cand)
    desc = _fold(cand.get("description"))
    where, missing = {}, []
    for t in required:
        hit = next((name for name, text in fields if _attested(t, text)), None)
        if hit:
            where[t] = hit
        else:
            missing.append(t)
    everything = " ".join(text for _n, text in fields) + " " + desc
    fh = sum(1 for f in fmt if _attested(f, everything))
    if not missing:
        return {"ok": True, "tier": 0, "where": where, "missing": [], "format_hits": fh,
                "why": "its %s name%s %s" % (", ".join(sorted(set(where.values()))),
                                              "s" if len(set(where.values())) == 1 else "", " + ".join(required))}
    if desc and _phrase_in(required, desc):
        where.update({t: "description" for t in missing})
        return {"ok": True, "tier": 1, "where": where, "missing": [], "format_hits": fh,
                "why": "its description names %r" % " ".join(required)}
    loose = [t for t in missing if desc and _attested(t, desc)]
    why = "%s not in its title, object name or categories" % ", ".join(repr(t) for t in missing)
    if loose:
        why += " (%s only in its description prose, not as the phrase %r)" % (
            ", ".join(repr(t) for t in loose), " ".join(required))
    return {"ok": False, "tier": None, "where": where, "missing": missing, "format_hits": fh, "why": why}


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
        # every language of the description, so a German or Chinese query can be attested by its own words
        "iiextmetadatamultilang": 1,
    })
    out = []
    # `pages` is a dict keyed by PAGE ID — the order of upload, not of relevance. The search rank is `index`.
    # Walking .values() put Commons' 8th hit for "lever escapement" (a piano action) first.
    pages = ((d.get("query") or {}).get("pages") or {}).values()
    for p in sorted(pages, key=lambda p: p.get("index", 1 << 30)):
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii:
            continue
        mime = ii.get("mime", "")
        # raster + svg + tiff: Commons serves a rendered PNG thumb for an svg and a JPEG thumb for a tiff (archival
        # scans and many diagrams are tiff — the best "Unruh Spirale" hit was one). Skip pdf/djvu/video.
        if not (mime.startswith("image/") and any(k in mime for k in ("jpeg", "png", "svg", "tiff"))):
            continue
        if "tiff" in mime and not ii.get("thumburl"):
            continue                                   # no rendered thumb: the original tiff is not a web image
        em = ii.get("extmetadata") or {}
        out.append({
            "title": p.get("title"),
            "url": ii.get("thumburl") or ii.get("url"),
            "mime": mime,
            "license": _strip_html(_em(em, "LicenseShortName")),
            "artist": _artist(_em(em, "Artist")),
            "credit": _strip_html(_em(em, "Credit")),
            "object_name": _strip_html(_em(em, "ObjectName", every=True)),
            "description": _strip_html(_em(em, "ImageDescription", every=True)),
            "categories": _strip_html(_em(em, "Categories")),
            "rank": p.get("index"),
            "source": ii.get("descriptionurl"),
            # a raster's thumb is never larger than its original: Commons reports thumbwidth = the REQUESTED
            # width even so (a 417 px file came back as 2400 and passed min_width=800). A vector renders at any size.
            "width": _real_size(ii, mime, "width"),
            "height": _real_size(ii, mime, "height"),
        })
    return out


def _download(url, out_path, timeout=60):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    data = _get(url, timeout, "downloading %s" % url)
    if len(data) < 1024:
        raise ValueError("download too small")
    with open(out_path, "wb") as f:
        f.write(data)


def _pixel_width(path):
    """The downloaded file's own width, or None when PIL cannot read it. The API's numbers are a claim about the
    file; this is the file."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size[0]
    except Exception:                                   # noqa: BLE001 — unreadable is reported by the caller
        return None


def fetch(query, out_path, width=1600, prefer=None, min_width=800, require_license=True, require=None,
          why=None):
    """Search + download the best license-clean image OF `query`'s subject → out_path, and write a sidecar
    `out_path + '.json'` with {title, license, artist, source, query, relevance} (the ATTRIBUTION — a documentary
    image must carry it — and which field named each term).

    Relevance (see the note above `key_terms`): a candidate is taken only when its own record attests every key
    term of the query — or of `require`, a list of terms that must be attested when the query carries qualifiers
    the record need not repeat. Among relevant candidates the order is `prefer` (a title substring, e.g. 'map'),
    then how strongly the record names the subject, then Commons' own rank.

    Returns the attribution dict, or None when Commons ANSWERED and nothing in the answer was relevant,
    license-clean, wide enough and downloadable. Then each refused candidate and the reason is printed to stderr
    and appended to `why` (a list) when one is passed — a refusal says which term was missing where, so the next
    query can be better than a guess. Raises FetchError when Commons could not be asked (a rate limit, a server
    error, the network), which is never the same thing as "nothing exists"."""
    q_req, fmt = key_terms(query)
    req = [t for t in _TOKEN.findall(_fold(" ".join(require))) if t not in _STOPWORDS] if require else q_req
    if not req:
        raise ValueError("require=%r names no term" % (require,))
    try:
        cands = search(query, limit=12, width=width)
    except FetchError:
        raise
    except Exception as e:                           # noqa: BLE001 — a refusal or an unreadable answer
        raise _failure("the Commons search for %r" % query, e) from e
    refused, keep, near = [], [], []
    for c in cands:
        if require_license and not _license_ok(c["license"]):
            refused.append((c, "licence %r is not free/attributable" % c["license"]))
            continue
        if (c.get("width") or 0) < min_width:
            refused.append((c, "%s px wide at most, under min_width %d" % (c.get("width"), min_width)))
            continue
        r = relevance(c, req, fmt)
        if not r["ok"]:
            refused.append((c, "off-subject: " + r["why"]))
            near.append((len(r["missing"]), c.get("rank") or 0, r))
            continue
        keep.append((c, r))
    pref = (prefer or "").lower()
    keep.sort(key=lambda cr: (0 if pref and pref in (cr[0]["title"] or "").lower() else 1, cr[1]["tier"],
                              -cr[1]["format_hits"],
                              cr[0].get("rank") if cr[0].get("rank") is not None else 1 << 30))
    for c, r in keep:
        if not c.get("url"):
            continue
        try:
            _download(c["url"], out_path)
        except FetchError:
            raise          # the service, not this file — every other candidate would wait out the same failure
        except Exception as e:  # noqa: BLE001 — this one file is unusable (gone, too small): try the next one
            refused.append((c, "download failed: %s" % e))
            continue
        px = _pixel_width(out_path)
        if px is None:
            # not a picture PIL can open (an error page, a truncated file): never hand it on as an image
            refused.append((c, "the downloaded file is not a readable image"))
            os.remove(out_path)
            continue
        if px < min_width:
            # the API overstated it (Commons once reported a requested width for a smaller original)
            refused.append((c, "the downloaded file is %d px wide, under min_width %d" % (px, min_width)))
            os.remove(out_path)
            continue
        meta = {"title": c["title"], "license": c["license"], "artist": c["artist"],
                "credit": c["credit"], "source": c["source"], "query": query,
                "relevance": {"terms": req, "where": r["where"], "tier": r["tier"]},
                "pixel_width": px}
        with open(out_path + ".json", "w") as f:
            json.dump(meta, f, indent=2)
        return meta
    lines = ["%s — %s" % (c.get("title"), reason) for c, reason in refused]
    hints = []
    if near:
        _n, _rk, best = min(near, key=lambda x: (x[0], x[1]))
        named = [t for t in req if t not in best["missing"]]
        if named:
            hints.append("closest records name %s but not %s — if %s only qualif%s the subject, re-run with "
                         "--require %s (require=[...]); if it IS the subject, rephrase the query instead"
                         % (" + ".join(named), " + ".join(best["missing"]), " + ".join(best["missing"]),
                            "ies" if len(best["missing"]) == 1 else "y", " ".join(named)))
    if any(_is_cjk(t) for t in req):
        hints.append("Commons file records are mostly in English (or the subject's Latin/local name); a CJK term is "
                     "attested only where a record carries those glyphs — try the subject's English name")
    lines += ["hint: " + h for h in hints]
    if why is not None:
        why.extend(lines)
    print("[imagefetch] nothing returned for %r (required terms: %s). %d candidate%s refused:%s"
          % (query, " + ".join(req), len(refused), "" if len(refused) == 1 else "s",
             "".join("\n  - " + ln for ln in lines) or " (Commons found no files)"), file=sys.stderr)
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
    ap.add_argument("--prefer", default=None, help="rank candidates whose title contains this first (e.g. map)")
    ap.add_argument("--min-width", type=int, default=800,
                    help="refuse a raster narrower than this at its ORIGINAL resolution (default 800)")
    ap.add_argument("--require", nargs="+", default=None, metavar="TERM",
                    help="the terms the file's record must attest (default: every key term of the query) — "
                         "for a query whose qualifiers a picture's record need not repeat")
    ap.add_argument("--duotone", nargs=2, metavar=("SHADOW", "HIGHLIGHT"), default=None,
                    help="hex shadow + highlight, e.g. --duotone '#161412' '#f5f2ea'")
    a = ap.parse_args()
    try:
        meta = fetch(a.query, a.out, width=a.width, prefer=a.prefer, min_width=a.min_width, require=a.require)
    except FetchError as e:
        # exit 2, not 1: the search never ran to an answer, so nothing may be concluded about the subject
        print(f"[imagefetch] FAILED, no answer from Commons ({e.kind}) for: {a.query}\n             {e}",
              file=sys.stderr)
        raise SystemExit(2)
    if not meta:
        # the refused candidates and why were printed to stderr by fetch()
        print(f"[imagefetch] no relevant, license-clean image found for: {a.query}")
        raise SystemExit(1)
    if a.duotone:
        duotone(a.out, a.out, shadow=_hex_rgb(a.duotone[0]), highlight=_hex_rgb(a.duotone[1]))
    print(f"[imagefetch] {a.out}  <-  {meta['title']}  [{meta['license']}]")
    print(f"             {attribution_line(meta)}")
    print("             relevance: " + ", ".join("%s<-%s" % kv for kv in meta["relevance"]["where"].items()))


if __name__ == "__main__":
    main()
