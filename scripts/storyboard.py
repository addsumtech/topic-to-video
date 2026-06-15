"""The data contract shared by every pipeline stage. No media I/O."""
import json

class StoryboardError(ValueError):
    pass

VALID_STYLES = {"highlight", "arrow", "box"}

def new_slide(index, image, narration="", notes=""):
    return {
        "index": index,
        "image": image,
        "narration": narration,
        "notes": notes,
        "audio": None,
        "duration": None,
        "motion": {"type": "kenburns", "from": [0.5, 0.5, 1.0], "to": [0.5, 0.5, 1.12]},
        "callouts": [],
        "captions": [],
    }

def new_storyboard(meta_overrides=None):
    meta = {"aspect": "16:9", "width": 1920, "height": 1080, "fps": 30,
            "voice": "say:Samantha", "captions": True}
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

def validate(data):
    if "meta" not in data or "slides" not in data:
        raise StoryboardError("storyboard needs 'meta' and 'slides'")
    if not data["slides"]:
        raise StoryboardError("storyboard has no slides")
    for s in data["slides"]:
        for key in ("index", "image", "narration"):
            if key not in s:
                raise StoryboardError(f"slide missing '{key}': {s.get('index')}")
        for co in s.get("callouts", []):
            box = co.get("box", [])
            if len(box) != 4 or not _in_unit(*box):
                raise StoryboardError(f"callout box must be 4 unit coords: {box}")
            if co.get("style") not in VALID_STYLES:
                raise StoryboardError(f"bad callout style: {co.get('style')}")
    return True
