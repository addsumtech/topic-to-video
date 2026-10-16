"""The data contract shared by every pipeline stage. No media I/O."""
import json

class StoryboardError(ValueError):
    pass

VALID_STYLES = {"highlight", "arrow", "box"}
VALID_SCENE_TYPES = {"slide", "title", "chart", "timeline", "keypoints", "compare", "html", "cinematic", "cinematic3d"}
ANIMATED_TYPES = {"title", "chart", "timeline", "keypoints", "compare", "html"}
VALID_CHART_KINDS = {"bars", "line", "counter", "slope", "dumbbell", "dist", "scatter", "small_multiples"}
VALID_IMAGE_SOURCES = {"none", "openai"}
VALID_IMAGE_PROVIDERS = {"auto", "codex", "openai"}
VALID_IMAGE_TAGS = {"motif", "broll", "asserted"}
VALID_FITS = {"contain", "cover"}
VALID_IMAGE_QUALITIES = {"low", "medium", "high"}
VALID_IMAGE_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}   # gpt-image-2 supported sizes
VALID_RENDERERS = {"local", "remotion", "remotion-legacy"}
# local = ffmpeg+Chrome (default). remotion/remotion = the bespoke-shot cinematic tier (LIBRARY.md).
# remotion-legacy = the retired generic-scene machinery (kept one release for migration).
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

# THE FIELDS A FILM'S TOOLS READ FROM ITS SLIDES THAT ONLY THE CONTENT PLAN WRITES. seam_plan derives the cuts and the
# camera from `relation`, energy_skeleton reads `energy`, rhythm_qa reads `climax`/`hold`, the critics read `stage`.
# On the GPS test film the board was built from the plan by hand without them, and seam_plan reported "no beat
# declares new-topic / payoff / close — every seam stays the default cut" until they were copied over.
PLAN_FIELDS = ("relation", "energy", "stage", "climax", "hold")


def from_content_plan(plan, meta_overrides=None):
    """A from-scratch film's board: one slide per content beat, in order, carrying PLAN_FIELDS (narration empty —
    the scriptwriter writes it at step 4)."""
    data = new_storyboard(meta_overrides)
    for i, b in enumerate([b for b in (plan or {}).get("beats") or [] if isinstance(b, dict)], 1):
        s = {"index": i, "narration": ""}
        s.update({k: b[k] for k in PLAN_FIELDS if k in b})
        data["slides"].append(s)
    if (plan or {}).get("arc_kind"):
        data["meta"].setdefault("arc_kind", plan["arc_kind"])
    return data


def plan_fields_missing(slides, plan):
    """{field: n slides missing it} for the PLAN_FIELDS the content plan has and the board does not — matched BY
    POSITION, and only when the two hold the same number of beats (a board edited since the plan cannot be mapped)."""
    beats = [b for b in (plan or {}).get("beats") or [] if isinstance(b, dict)]
    if not beats or len(beats) != len(slides):
        return {}
    out = {}
    for k in PLAN_FIELDS:
        n = sum(1 for s, b in zip(slides, beats) if k in b and k not in s)
        if n:
            out[k] = n
    return out


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
    if t in ("cinematic", "cinematic3d"):
        # The Remotion cinematic tier carries its content in ANY of three forms (top-level OR inside props):
        # a shot-based SET (`stage`+`shots`, the paradigm), true-3D `planes` (P6), or legacy depth `layers`
        # (+ optional camera/lens). cinematic3d specifically needs `planes`. Any one is enough to render —
        # requiring `layers` alone wrongly rejected every shot-based / 3D board (render_remotion draws them).
        def _f(key):
            return s.get(key) or (p.get(key) if isinstance(p, dict) else None)
        layers, stage, shots, planes = _f("layers"), _f("stage"), _f("shots"), _f("planes")
        component = _f("component")   # a BESPOKE component draws the whole beat itself — satisfies either type
        if t == "cinematic3d":
            if not (isinstance(planes, list) and planes) and not component:
                raise StoryboardError(f"slide {s.get('index')}: cinematic3d scene needs a non-empty 'planes' list "
                                      f"(or a `component` that renders the beat itself)")
            return
        ok = (isinstance(layers, list) and layers) or (stage and shots) or (isinstance(planes, list) and planes) or component
        if not ok:
            raise StoryboardError(f"slide {s.get('index')}: cinematic scene needs `stage`+`shots`, or `planes`, "
                                  f"or a non-empty `layers` list, or a `component`")
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
        if m.get("renderer") == "remotion":
            # the bespoke-shot tier: a scene renders a `shot` (a register id), NOT the type/image contract.
            if not isinstance(s.get("shot"), str) or not s.get("shot"):
                raise StoryboardError(f"slide {s.get('index')}: remotion tier requires a `shot` (a register id)")
            continue
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


def main(argv):
    """`storyboard.py <out_dir> --from-plan [key=value ...]` — write a from-scratch film's board from content_plan.json,
    the interview's meta given as key=value (numbers and true/false parsed). Refuses to overwrite an existing board."""
    if len(argv) < 2 or argv[1] != "--from-plan":
        print("usage: storyboard.py <out_dir> --from-plan [language=zh renderer=remotion aspect=16:9 target_seconds=70 ...]")
        return 2
    import os
    out_dir = argv[0]
    path = os.path.join(out_dir, "storyboard.json")
    if os.path.exists(path):
        print("[storyboard] %s already exists — not overwritten" % path)
        return 2
    meta = {}
    for kv in argv[2:]:
        k, _, v = kv.partition("=")
        v = {"true": True, "false": False}.get(v.lower(), v)
        if isinstance(v, str):
            try:
                v = float(v) if "." in v else int(v)
            except ValueError:
                pass
        meta[k] = v
    plan = json.load(open(os.path.join(out_dir, "content_plan.json"), encoding="utf-8"))
    data = from_content_plan(plan, meta)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("[storyboard] %d slide(s) from content_plan.json, carrying %s" % (len(data["slides"]), ", ".join(PLAN_FIELDS)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
