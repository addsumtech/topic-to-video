"""Deterministic A/V sanity gate for a rendered video. Probes out.mp4 (video vs audio stream
duration), the per-scene clips (audio sample-rate uniformity), and out.srt (caption-cue count),
and fails on A/V drift or non-uniform clip audio rates — the failure mode that desyncs the
'-c copy' concat. Feeds the AV critic (SKILL.md step 8). No randomness, no wall-clock."""
import glob, os, subprocess, sys

def _ffprobe(args):
    return subprocess.run(["ffprobe", "-v", "error", *args], capture_output=True, text=True).stdout.strip()

def probe_durations(mp4):
    def dur(stream):
        out = _ffprobe(["-select_streams", stream, "-show_entries", "stream=duration",
                        "-of", "default=nw=1:nk=1", mp4])
        try:
            return float(out.splitlines()[0])
        except (ValueError, IndexError):
            return 0.0
    return dur("v:0"), dur("a:0")

def clip_rates(clips_dir):
    rates = []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        out = _ffprobe(["-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                        "-of", "default=nw=1:nk=1", c])
        try:
            rates.append(int(out.splitlines()[0]))
        except (ValueError, IndexError):
            pass
    return rates

def evaluate(v_dur, a_dur, rates, n_cues, n_scenes, drift_tol=0.3):
    drift = abs(v_dur - a_dur)
    uniform = len(set(rates)) <= 1
    issues = []
    if drift > drift_tol:
        issues.append(f"A/V drift {drift:.3f}s > {drift_tol}s (video {v_dur:.2f}s vs audio {a_dur:.2f}s)")
    if not uniform:
        issues.append(f"non-uniform clip audio sample rates {sorted(set(rates))} — '-c copy' concat desyncs")
    if v_dur <= 0 or a_dur <= 0:
        issues.append(f"missing stream (video {v_dur:.2f}s, audio {a_dur:.2f}s)")
    warnings = []
    if n_scenes and n_cues == 0:
        warnings.append("no caption cues in out.srt")
    ok = (drift <= drift_tol) and uniform and v_dur > 0 and a_dur > 0
    return {"ok": ok, "drift": round(drift, 3), "uniform_rates": uniform,
            "issues": issues, "warnings": warnings}

def _count_cues(srt):
    try:
        return open(srt).read().count(" --> ")
    except OSError:
        return 0

def check(out_dir):
    v, a = probe_durations(os.path.join(out_dir, "out.mp4"))
    rates = clip_rates(os.path.join(out_dir, ".clips"))
    n_cues = _count_cues(os.path.join(out_dir, "out.srt"))
    n_scenes = 0
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import storyboard as sb
        n_scenes = len(sb.load(os.path.join(out_dir, "storyboard.json")).get("slides", []))
    except Exception:
        pass
    r = evaluate(v, a, rates, n_cues, n_scenes)
    r.update({"video_dur": round(v, 3), "audio_dur": round(a, 3),
              "rates": sorted(set(rates)), "cues": n_cues, "scenes": n_scenes})
    return r

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    r = check(out_dir)
    print(f"[check_av] {'OK' if r['ok'] else 'FAIL'}  video={r['video_dur']}s audio={r['audio_dur']}s "
          f"drift={r['drift']}s rates={r['rates']} cues={r['cues']}/{r['scenes']}")
    for i in r["issues"]:
        print(f"  ISSUE: {i}")
    for w in r["warnings"]:
        print(f"  warn: {w}")
    sys.exit(0 if r["ok"] else 1)

if __name__ == "__main__":
    main()
