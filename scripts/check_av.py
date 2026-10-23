"""Deterministic A/V sanity gate for a rendered video. Probes out.mp4 (video vs audio stream
duration), the per-scene clips (audio sample-rate uniformity), and out.srt (caption-cue count),
and fails on A/V drift or non-uniform clip audio rates — the failure mode that desyncs the
'-c copy' concat. Feeds the AV critic (SKILL.md step 8). No randomness, no wall-clock.

AND IT SAYS WHAT IT DID NOT MEASURE. `clip_rates()` returned a bare list, so three different
worlds arrived here as `[]` and all three printed `uniform`: a render with no `.clips/` at all
(the remotion tier never writes one — it muxes in a single pass, so this check does not apply to
it), a `.clips/` full of files ffprobe could not read, and an empty directory. The headline
`rates=[]` reads as a clean result in every one of them. Each clip is now accounted for by name,
and a clip that is PRESENT and unreadable makes the run INCOMPLETE — which is not the same thing
as clean, and is not the same thing as a tier that has no clips to check.
"""
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
    """Back-compatible: just the rates. `clip_probe` is the accounted version."""
    return clip_probe(clips_dir)[0]

def clip_probe(clips_dir):
    """(rates, unreadable, present) — every clip in the universe accounted for.

    `present` is False when there is no `.clips/` directory at all, which is a DIFFERENT statement
    from "the clips are all fine": the remotion tier renders in one pass and never writes clips, so
    for those films this check does not apply and must not report a pass.
    """
    if not os.path.isdir(clips_dir):
        return [], [], False
    rates, unreadable = [], []
    for c in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))):
        out = _ffprobe(["-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                        "-of", "default=nw=1:nk=1", c])
        try:
            rates.append(int(out.splitlines()[0]))
        except (ValueError, IndexError):
            unreadable.append((os.path.basename(c),
                               "ffprobe read no a:0 sample_rate (%s) — a clip whose audio stream cannot be "
                               "probed is not a clip that matches the others"
                               % (out.splitlines()[0][:60] if out.splitlines() else "no output")))
    return rates, unreadable, True

def evaluate(v_dur, a_dur, rates, n_cues, n_scenes, drift_tol=0.3,
             clips_unreadable=(), clips_present=None, srt_present=None, board_note=None):
    drift = abs(v_dur - a_dur)
    uniform = len(set(rates)) <= 1
    issues = []
    if drift > drift_tol:
        issues.append(f"A/V drift {drift:.3f}s > {drift_tol}s (video {v_dur:.2f}s vs audio {a_dur:.2f}s)")
    if not uniform:
        issues.append(f"non-uniform clip audio sample rates {sorted(set(rates))} — '-c copy' concat desyncs — delete .clips/ and re-render to normalise")
    if v_dur <= 0 or a_dur <= 0:
        issues.append(f"missing stream (video {v_dur:.2f}s, audio {a_dur:.2f}s)")
    warnings = []
    if n_scenes and n_cues == 0:
        warnings.append("no caption cues in out.srt")
    # ── what this run could NOT measure, and what it does not apply to ──────────────────────────────
    unreadable = list(clips_unreadable)
    not_measured = ["%s: %s" % (name, why) for name, why in unreadable]
    if srt_present is False and n_scenes:
        not_measured.append("out.srt: absent, so the caption-cue count is 0 by default rather than by "
                            "measurement — the film declares %d scene(s)" % n_scenes)
    if board_note:
        not_measured.append("storyboard.json: %s — the scene count this run compares cues against is 0 by "
                            "default, so a cue/scene mismatch cannot be seen" % board_note)
    not_applicable = []
    if clips_present is False:
        not_applicable.append("clip audio sample-rate uniformity: there is no .clips/ directory. Only "
                              "render.py (the slide/html tier) writes per-scene clips; a remotion film is "
                              "muxed in one pass, so there is nothing here for '-c copy' to desync.")
    elif clips_present and not rates and not unreadable:
        not_applicable.append("clip audio sample-rate uniformity: .clips/ holds no *.mp4")
    ok = (drift <= drift_tol) and uniform and v_dur > 0 and a_dur > 0
    return {"ok": ok, "complete": not not_measured, "drift": round(drift, 3), "uniform_rates": uniform,
            "clips_measured": len(rates), "clips_total": len(rates) + len(unreadable),
            "not_measured": not_measured, "not_applicable": not_applicable,
            "issues": issues, "warnings": warnings}

def _count_cues(srt):
    try:
        return open(srt, encoding="utf-8", errors="replace").read().count(" --> ")
    except OSError:
        return 0

DELIVERY_RATE_MAX = 48000     # AAC delivery (platform guides): the loudness pass once shipped 96 kHz
LOUDNESS_TARGET, LOUDNESS_WARN_LU, TRUE_PEAK_WARN = -14.0, 1.5, -1.0   # convention, not a platform spec (warned)


def delivery_audio(mp4):
    """(sample rate, integrated LUFS, true peak dBTP) of the DELIVERED file — measured on the encoded audio, where a
    request to the mix (a target, a ceiling) has been through the AAC encoder; None for what could not be read."""
    import re
    rate = None
    try:
        rate = int(_ffprobe(["-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                             "-of", "default=nw=1:nk=1", mp4]).splitlines()[0])
    except (ValueError, IndexError):
        pass
    integ = tp = None
    try:
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vn", "-af", "ebur128=peak=true",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        tail = err[err.rfind("Summary:"):] if "Summary:" in err else ""
        m = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
        integ = float(m.group(1)) if m else None
        m = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
        tp = float(m.group(1)) if m and m.group(1) != "-inf" else None
    except Exception:                               # noqa: BLE001 — unmeasured, said by the caller
        pass
    return rate, integ, tp


def check(out_dir):
    v, a = probe_durations(os.path.join(out_dir, "out.mp4"))
    rates, unreadable, clips_present = clip_probe(os.path.join(out_dir, ".clips"))
    srt = os.path.join(out_dir, "out.srt")
    n_cues = _count_cues(srt)
    n_scenes, board_note = 0, None
    board = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board):
        board_note = None                         # nothing claims a scene count; not a failure to measure
    else:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import storyboard as sb
            n_scenes = len(sb.load(board).get("slides", []))
        except Exception as e:                    # noqa: BLE001 — report the reason, never swallow it
            board_note = "%s: %s" % (type(e).__name__, e)
    r = evaluate(v, a, rates, n_cues, n_scenes, clips_unreadable=unreadable,
                 clips_present=clips_present, srt_present=os.path.exists(srt), board_note=board_note)
    r.update({"video_dur": round(v, 3), "audio_dur": round(a, 3),
              "rates": sorted(set(rates)), "cues": n_cues, "scenes": n_scenes})
    # THE DELIVERED AUDIO ITSELF: its rate is a format defect (refused), its loudness a convention (warned)
    mp4 = os.path.join(out_dir, "out.mp4")
    if os.path.exists(mp4) and a > 0:
        rate, integ, tp = delivery_audio(mp4)
        r.update({"delivery_rate": rate, "integrated_lufs": integ, "true_peak_dbtp": tp})
        if rate is None or integ is None:
            r["not_measured"].append("the delivered audio's %s could not be read"
                                     % ("sample rate" if rate is None else "loudness"))
            r["complete"] = False
        if rate is not None and rate > DELIVERY_RATE_MAX:
            r["issues"].append("out.mp4 audio is %d Hz — AAC delivery wants ≤%d Hz (a loudness pass upsamples; "
                               "resample after it)" % (rate, DELIVERY_RATE_MAX))
            r["ok"] = False
        if integ is not None and abs(integ - LOUDNESS_TARGET) > LOUDNESS_WARN_LU:
            r["warnings"].append("out.mp4 measures %.1f LUFS integrated — %.1f LU off the %.0f LUFS convention"
                                 % (integ, integ - LOUDNESS_TARGET, LOUDNESS_TARGET))
        if tp is not None and tp > TRUE_PEAK_WARN:
            r["warnings"].append("out.mp4 peaks at %.1f dBTP after encoding — over the %.0f dBTP ceiling"
                                 % (tp, TRUE_PEAK_WARN))
    return r

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    r = check(out_dir)
    state = "OK" if r["ok"] else "FAIL"
    if r["ok"] and not r["complete"]:
        state = "INCOMPLETE"
    print(f"[check_av] {state}  video={r['video_dur']}s audio={r['audio_dur']}s "
          f"drift={r['drift']}s rates={r['rates']} ({r['clips_measured']}/{r['clips_total']} clip(s) measured) "
          f"cues={r['cues']}/{r['scenes']}")
    for i in r["issues"]:
        print(f"  ISSUE: {i}")
    for n in r["not_measured"]:
        print(f"  NOT MEASURED: {n}")
    for n in r["not_applicable"]:
        print(f"  n/a: {n}")
    for w in r["warnings"]:
        print(f"  warn: {w}")
    sys.exit(0 if (r["ok"] and r["complete"]) else 1)

if __name__ == "__main__":
    main()
