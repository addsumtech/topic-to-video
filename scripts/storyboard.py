"""The data contract shared by every pipeline stage. No media I/O."""
import json

class StoryboardError(ValueError):
    pass

VALID_STYLES = {"highlight", "arrow", "box"}
VALID_SCENE_TYPES = {"slide", "title", "chart", "timeline"}
ANIMATED_TYPES = {"title", "chart", "timeline"}
VALID_CHART_KINDS = {"bars", "line", "counter"}

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
        for d in data:
            if not isinstance(d, dict) or not _is_num(d.get("value")):
                raise StoryboardError(f"slide {s.get('index')}: every chart data item needs a numeric 'value'")
    elif t == "timeline":
        events = p.get("events")
        if not isinstance(events, list) or not events:
            raise StoryboardError(f"slide {s.get('index')}: timeline needs non-empty 'events' list")
        for e in events:
            if not (isinstance(e, dict) and isinstance(e.get("date"), str) and isinstance(e.get("label"), str)):
                raise StoryboardError(f"slide {s.get('index')}: every timeline event needs 'date' and 'label' strings")

def validate(data):
    if "meta" not in data or "slides" not in data:
        raise StoryboardError("storyboard needs 'meta' and 'slides'")
    if not data["slides"]:
        raise StoryboardError("storyboard has no slides")
    for s in data["slides"]:
        if "index" not in s or "narration" not in s:
            raise StoryboardError(f"slide missing 'index'/'narration': {s.get('index')}")
        t = s.get("type", "slide")
        if t not in VALID_SCENE_TYPES:
            raise StoryboardError(f"slide {s.get('index')}: unknown type '{t}'")
        if t == "slide":
            if "image" not in s or not s["image"]:
                raise StoryboardError(f"slide {s.get('index')}: type 'slide' requires 'image'")
        else:
            _validate_props(s)
        for co in s.get("callouts", []):
            box = co.get("box", [])
            if len(box) != 4 or not _in_unit(*box):
                raise StoryboardError(f"callout box must be 4 unit coords: {box}")
            if co.get("style") not in VALID_STYLES:
                raise StoryboardError(f"bad callout style: {co.get('style')}")
    return True
