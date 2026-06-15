"""Narration text -> per-slide audio. Default macOS 'say'; cloud optional.

Voice spec in storyboard meta['voice']:
  "say:Samantha"        -> local macOS say, voice Samantha
  "openai:alloy"        -> OpenAI TTS (needs OPENAI_API_KEY); falls back to say
"""
import argparse, os
import _common
import storyboard as sb

def _say(text, out_path, voice, rate=175):
    # say writes AIFF directly; ffprobe reads its real duration later.
    _common.run(["say", "-v", voice, "-r", str(rate), "-o", out_path, text])

def _openai(text, out_path, voice):
    # Optional upgrade. Lazy import so the skill never hard-depends on it.
    import requests
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("no OPENAI_API_KEY")
    r = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "gpt-4o-mini-tts", "voice": voice, "input": text},
        timeout=60)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)

def _provider(voice_spec):
    if ":" in voice_spec:
        prov, name = voice_spec.split(":", 1)
    else:
        prov, name = "say", voice_spec
    return prov, name

def synthesize(out_dir, only=None):
    path = os.path.join(out_dir, "storyboard.json")
    data = sb.load(path)
    audio_dir = os.path.join(out_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    prov, name = _provider(data["meta"].get("voice", "say:Samantha"))

    for s in data["slides"]:
        if only and s["index"] != only:
            continue
        text = (s.get("narration") or "").strip() or " "
        ext = "aiff" if prov == "say" else "mp3"
        rel = os.path.join("audio", f"{s['index']:02d}.{ext}")
        dest = os.path.join(out_dir, rel)
        try:
            if prov == "openai":
                _openai(text, dest, name)
            else:
                _say(text, dest, name)
        except Exception as e:
            print(f"[tts] {prov} failed ({e}); falling back to say:Samantha")
            rel = os.path.join("audio", f"{s['index']:02d}.aiff")
            dest = os.path.join(out_dir, rel)
            _say(text, dest, "Samantha")
        s["audio"] = rel
        s["duration"] = round(_common.audio_duration(dest), 3)

    sb.save(data, path)
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--only", type=int, default=None)
    a = ap.parse_args()
    data = synthesize(a.out_dir, a.only)
    total = sum(s["duration"] or 0 for s in data["slides"])
    print(f"Synthesized {len(data['slides'])} clips, ~{total:.1f}s total.")

if __name__ == "__main__":
    main()
