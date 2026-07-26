"""The data contract shared by every pipeline stage. No media I/O."""
import json

class StoryboardError(ValueError):
    pass

VALID_STYLES = {"highlight", "arrow", "box"}
VALID_SCENE_TYPES = {"slide", "title", "chart", "timeline", "keypoints", "compare", "html", "cinematic"}
ANIMATED_TYPES = {"title", "chart", "timeline", "keypoints", "compare", "html"}
VALID_CHART_KINDS = {"bars", "line", "counter", "slope", "dumbbell", "dist", "scatter", "small_multiples"}
VALID_IMAGE_SOURCES = {"none", "openai"}
VALID_IMAGE_PROVIDERS = {"auto", "codex", "openai"}
VALID_IMAGE_TAGS = {"motif", "broll", "asserted"}
VALID_FITS = {"contain", "cover"}
VALID_IMAGE_QUALITIES = {"low", "medium", "high"}
VALID_IMAGE_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}   # gpt-image-2 supported sizes
VALID_RENDERERS = {"local", "remotion"}   # local = ffmpeg+Chrome (default); remotion = optional cinematic tier
# Visual-ENERGY dial (render._intensity_amp): the design-director maps a beat's `energy` to this and
# writes it as meta.intensity (deck default) or slide.intensity (per-scene override). "balanced" is the
# no-op default, so the field is OPTIONAL and absent-means-balanced; validated here only when present so
# a typo ("bald") errors loudly instead of silently degrading to balanced.
VALID_INTENSITIES = {"subtle", "balanced", "bold"}

def _valid_intensity(v):
    """A named tier OR a non-negative raw multiplier — mirrors render._intensity_amp's acceptance."""
    if isinstance(v, str) and v.strip().lower() in VALID_INTENSITIES:
        return True
    if isinstance(v, bool):
        return False
    try:
        return float(v) >= 0.0
    except (TypeError, ValueError):
        return False

def new_slide(index, image, narration="", notes=""):
    return {
        "index": index, "image": image, "narration": narration, "notes": notes,
        "type": "slide", "props": None,
        "audio": None, "duration": None,
        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
        "callouts": [], "captions": [],
    }

def new_scene(index, scene_type, props, narration="", notes=""):
    return {
        "index": index, "image": None, "narration": narration, "notes": notes,
        "type": scene_type, "props": props,
        "audio": None, "duration": None,
        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
        "callouts": [], "captions": [],
    }

def new_storyboard(meta_overrides=None):
    # `language` is the language the narration/captions are WRITTEN in (BCP-47-ish:
    # "en", "zh", "ja", "ko", "es", "fr", "de", ...). It drives the caption font and
    # the default TTS voice. "auto" = decide from the slides' language during the
    # interview; the workflow sets a concrete code once confirmed with the user.
    meta = {"aspect": "16:9", "width": 1920, "height": 1080, "fps": 30,
            "language": "auto", "voice": "auto", "captions": True}
    if meta_overrides:
        meta.update(meta_overrides)
    return {"meta": meta, "slides": []}

def load(path):
    with open(path) as f:
        return json.load(f)

def save(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def _in_unit(*vals):
    return all(0.0 <= v <= 1.0 for v in vals)

def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def _validate_props(s):
    t = s["type"]; p = s.get("props")
    if t == "cinematic":
        # the Remotion cinematic tier carries its content in top-level `layers` (+ optional `camera`/
        # `lens`), or inside props — either is fine. It needs depth planes to render.
        layers = s.get("layers") or (p.get("layers") if isinstance(p, dict) else None)
        if not (isinstance(layers, list) and layers):
            raise StoryboardError(f"slide {s.get('index')}: cinematic scene needs a non-empty 'layers' list")
        return
    if not isinstance(p, dict):
        raise StoryboardError(f"slide {s.get('index')}: type '{t}' needs a props dict")
    if t == "title":
        if not (isinstance(p.get("title"), str) and p["title"].strip()):
            raise StoryboardError(f"slide {s.get('index')}: title scene needs non-empty 'title'")
    elif t == "chart":
        if p.get("kind") not in VALID_CHART_KINDS:
            raise StoryboardError(f"slide {s.get('index')}: chart 'kind' must be one of {VALID_CHART_KINDS}")
        data = p.get("data")
        if not isinstance(data, list) or not data:
            raise StoryboardError(f"slide {s.get('index')}: chart needs non-empty 'data' list")
        kind = p.get("kind", "bars")
        for d in data:
            if not isinstance(d, dict):
                raise StoryboardError(f"slide {s.get('index')}: every chart data item must be an object")
            if kind in ("bars", "line", "counter"):
                if not _is_num(d.get("value")):
                    raise StoryboardError(f"slide {s.get('index')}: every {kind} data item needs a numeric 'value'")
            elif kind in ("slope", "dumbbell"):
                vv = d.get("values")
                ok = (isinstance(vv, list) and len(vv) >= 2 and _is_num(vv[0]) and _is_num(vv[1])) \
                    or (_is_num(d.get("v1")) and _is_num(d.get("v2")))
                if not ok:
                    raise StoryboardError(f"slide {s.get('index')}: every {kind} data item needs 'values':[a,b] or 'v1'+'v2'")
            elif kind == "scatter":
                if not (_is_num(d.get("x")) and _is_num(d.get("y"))):
                    raise StoryboardError(f"slide {s.get('index')}: every scatter data item needs numeric 'x' and 'y'")
            elif kind in ("dist", "small_multiples"):
                vv = d.get("values")
                if not (isinstance(vv, list) and vv and all(_is_num(x) for x in vv)):
                    raise StoryboardError(f"slide {s.get('index')}: every {kind} data item needs a non-empty numeric 'values' list")
    elif t == "timeline":
        events = p.get("events")
        if not isinstance(events, list) or not events:
            raise StoryboardError(f"slide {s.get('index')}: timeline needs non-empty 'events' list")
        for e in events:
            # accept BOTH conventions: programmatic date/label AND the HTML .timeline archetype's when/what
            has_when = isinstance(e, dict) and (isinstance(e.get("date"), str) or isinstance(e.get("when"), str))
            has_what = isinstance(e, dict) and (isinstance(e.get("label"), str) or isinstance(e.get("what"), str))
            if not (has_when and has_what):
                raise StoryboardError(f"slide {s.get('index')}: every timeline event needs 'date'/'when' + 'label'/'what' strings")
    elif t == "keypoints":
        pts = p.get("points")
        if not isinstance(pts, list) or not (1 <= len(pts) <= 5):
            raise StoryboardError(f"slide {s.get('index')}: keypoints needs 1-5 'points'")
        for it in pts:
            if not (isinstance(it, dict) and isinstance(it.get("label"), str) and it["label"].strip()):
                raise StoryboardError(f"slide {s.get('index')}: each keypoint needs a non-empty 'label' string")
    elif t == "compare":
        if p.get("kind") not in {"split", "versus"}:
            raise StoryboardError(f"slide {s.get('index')}: compare 'kind' must be 'split' or 'versus'")
        parts = p.get("parts")
        if not isinstance(parts, list) or len(parts) < 2:
            raise StoryboardError(f"slide {s.get('index')}: compare needs a 'parts' list of >=2 items")
        for it in parts:
            if not (isinstance(it, dict) and isinstance(it.get("label"), str) and _is_num(it.get("value"))):
                raise StoryboardError(f"slide {s.get('index')}: each compare part needs a 'label' string + numeric 'value'")
    elif t == "html":
        if not (isinstance(p.get("html"), str) and p["html"].strip()):
            raise StoryboardError(f"slide {s.get('index')}: html scene needs a non-empty 'html' path")
        if "anim_seconds" in p and not (_is_num(p["anim_seconds"]) and p["anim_seconds"] > 0):
            raise StoryboardError(f"slide {s.get('index')}: html 'anim_seconds' must be a positive number")

def validate(data):
    if "meta" not in data or "slides" not in data:
        raise StoryboardError("storyboard needs 'meta' and 'slides'")
    if not data["slides"]:
        raise StoryboardError("storyboard has no slides")
    m = data["meta"]
    if m.get("image_source") not in (None, *VALID_IMAGE_SOURCES):
        raise StoryboardError(f"meta.image_source must be one of {VALID_IMAGE_SOURCES}")
    if "image_quality" in m and m["image_quality"] not in VALID_IMAGE_QUALITIES:
        raise StoryboardError(f"meta.image_quality must be one of {VALID_IMAGE_QUALITIES}")
    if "image_provider" in m and m["image_provider"] not in VALID_IMAGE_PROVIDERS:
        raise StoryboardError(f"meta.image_provider must be one of {VALID_IMAGE_PROVIDERS}")
    if "image_size" in m and m["image_size"] not in VALID_IMAGE_SIZES:
        raise StoryboardError(f"meta.image_size must be one of {VALID_IMAGE_SIZES}")
    if "renderer" in m and m["renderer"] not in VALID_RENDERERS:
        raise StoryboardError(f"meta.renderer must be one of {VALID_RENDERERS}")
    if "intensity" in m and not _valid_intensity(m["intensity"]):
        raise StoryboardError(f"meta.intensity must be one of {VALID_INTENSITIES} or a non-negative number")
    for s in data["slides"]:
        if "index" not in s or "narration" not in s:
            raise StoryboardError(f"slide missing 'index'/'narration': {s.get('index')}")
        t = s.get("type", "slide")
        if t not in VALID_SCENE_TYPES:
            raise StoryboardError(f"slide {s.get('index')}: unknown type '{t}'")
        if t == "slide":
            has_img = bool(s.get("image"))
            has_prompt = bool((s.get("image_prompt") or "").strip())
            if not has_img and not has_prompt:
                raise StoryboardError(f"slide {s.get('index')}: type 'slide' requires 'image' or 'image_prompt'")
        else:
            _validate_props(s)
        if "image_tag" in s and s["image_tag"] not in VALID_IMAGE_TAGS:
            raise StoryboardError(f"slide {s.get('index')}: image_tag must be one of {VALID_IMAGE_TAGS}")
        if "fit" in s and s["fit"] not in VALID_FITS:
            raise StoryboardError(f"slide {s.get('index')}: fit must be one of {VALID_FITS}")
        if "intensity" in s and not _valid_intensity(s["intensity"]):
            raise StoryboardError(f"slide {s.get('index')}: intensity must be one of {VALID_INTENSITIES} or a non-negative number")
        for co in s.get("callouts", []):
            box = co.get("box", [])
            if len(box) != 4 or not _in_unit(*box):
                raise StoryboardError(f"callout box must be 4 unit coords: {box}")
            if co.get("style") not in VALID_STYLES:
                raise StoryboardError(f"bad callout style: {co.get('style')}")
    return True


def normalize_transition(slide):
    """Return (flat_transition, seconds_or_None) for a slide, accepting BOTH the flat contract
    (slide['transition'] in {dip,in,out,none} + slide['transition_seconds']) AND a legacy OBJECT
    {'in','out','seconds'} the design plan sometimes emits — so a stray object can't silently degrade
    the authored per-scene rhythm to the uniform meta default. `flat` is None when unknown/absent."""
    t = (slide or {}).get("transition")
    sec = (slide or {}).get("transition_seconds")
    if isinstance(t, dict):
        in_on = (t.get("in") or "none") not in ("none", "", None)
        out_on = (t.get("out") or "none") not in ("none", "", None)
        flat = "dip" if (in_on and out_on) else "in" if in_on else "out" if out_on else "none"
        return flat, (sec if sec is not None else t.get("seconds"))
    return (t if t in ("dip", "in", "out", "none") else None), sec
