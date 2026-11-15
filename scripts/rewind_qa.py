#!/usr/bin/env python3
"""rewind_qa — does the picture ever go BACKWARDS? Read from the delivered pixels, on ANY render path.

    python3 scripts/rewind_qa.py <video.mp4> [--plan _plan.json | --cuts 255,450,...] [--json out.json]
    python3 scripts/rewind_qa.py --calibrate          # the synthetic controls must separate

WHY. The owner saw the same defect three times in one week, each time on a path no gate read: two back-to-back
segments of one Blender plate overlapping by 20 frames (slide-maker v2, 1:20 and 1:24); a typed line that printed
almost whole, cleared and retyped (an unclamped ramp, topic-to-video at 8.5 s); a stack that rotated back. The only
rewind guard in the skill read the promo TABLE (recording_continuity), never the picture. This reads the picture.

WHAT IT MEASURES (160x90 luma, the shots from the film's own plan when given, else detected):
  REPLAY  a cut whose first frames match a frame 2+ frames BEFORE the cut: the next shot replays what was just seen.
  RETURN  inside one shot, a region of the frame (a tile of an 8x6 grid) moves AWAY from a state by a clear excursion
          and comes BACK to (nearly) that state within RETURN_WINDOW: a reset, a ping-pong push ("拉进又拉出"), a
          rotation that turns back. Periodic motion (a region returning twice or more in the window: a spinning
          proton, an ambient loop) is a loop by design and not reported. A plan segment of kind "loop" is skipped.
Exit 0 clean · 1 a REPLAY or RETURN · 2 the video could not be read (UNMEASURED). Every run prints a scope line."""
import json
import os
import subprocess
import sys

import numpy as np

W, H = 160, 90
TX, TY = 8, 6                        # the tile grid
RETURN_WINDOW = 90                   # frames (3 s at 30 fps)
STEP = 2                             # frames between samples inside a shot
EXCURSION = 14.0                     # a tile's mean abs luma change (0-255) that is a real departure
BACK = 0.22                          # ...and the return lands within this share of the excursion
NEAR = 7.0                           # ...and within this absolute difference of the state it left
MIN_TILE_SPREAD = 6.0                # a tile with no structure (flat ground) is not judged
COHERENT = 0.85                      # share of the tiles that left which must be back together
REPLAY_FRAC, REPLAY_ABS = 0.25, 4.0  # a post-cut frame this close to a frame k>=2 before the cut
TRANSIENT = 1.3                      # the furthest frame's structure over the start's that says "an element came and went"


def frames(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=%d:%d,format=gray" % (W, H), "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    if not raw or len(raw) % (W * H):
        return None
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def tiles(F):
    """(n, TY, TX) per-tile means and the (n, TY*TX, th*tw) tile pixels"""
    th, tw = H // TY, W // TX
    t = F[:, :th * TY, :tw * TX].reshape(len(F), TY, th, TX, tw).transpose(0, 1, 3, 2, 4).reshape(len(F), TY * TX, th * tw)
    return t


def detect_cuts(F):
    d = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
    med = np.array([np.median(d[max(0, i - 15):i + 15]) for i in range(len(d))])
    return [i + 1 for i in range(len(d)) if d[i] > max(6.0, 6 * med[i] + 2)]


def plan_segments(plan, n):
    """[(start, end, kind)] from a plan file's segments, else from its cuts"""
    segs = plan.get("segments")
    if segs:
        return [(int(s["start"]), int(s["end"]), s.get("kind", "shot")) for s in segs]
    cuts = sorted(int(c) for c in plan.get("cuts") or [])
    b = [0] + [c for c in cuts if 0 < c < n] + [n]
    return [(a, z, "shot") for a, z in zip(b, b[1:])]


def replays(F, cuts):
    out = []
    for c in cuts:
        if c < 3 or c >= len(F):
            continue
        jump = float(np.abs(F[c] - F[c - 1]).mean())
        best = min(((float(np.abs(F[c] - F[c - k]).mean()), k) for k in range(2, min(61, c + 1))), default=None)
        if best and best[0] < REPLAY_FRAC * jump and best[0] < REPLAY_ABS:
            out.append({"kind": "REPLAY", "frame": c, "msg": "the cut at frame %d opens on a frame matching frame %d (%d frames replayed)"
                        % (c, c - best[1], best[1] - 1)})
    return out


def returns(F, a, z):
    """RETURN events inside frames [a, z): the regions that CHANGED come back TOGETHER. A rewind is coherent — the line
    that was cleared is retyped to the same place, the push returns the whole frame — while a camera sliding over
    repeating texture (chart bars, lines of type) makes single tiles look like an earlier frame by coincidence: on the
    slide-maker and QR films a per-tile rule fired on nearly every shot; this one requires >= COHERENT of the tiles
    that left to be back at one moment."""
    idx = list(range(a, z, STEP))
    if len(idx) < 6:
        return []
    T = tiles(F[idx])                                    # (m, k, p)
    m = len(idx)
    win = RETURN_WINDOW // STEP
    struct = T.std(axis=2).max(axis=0) >= MIN_TILE_SPREAD
    struct[(TY - 1) * TX:] = False      # the caption band (bottom row): karaoke and line changes are judged by caption gates
    first = None
    for i in range(m):
        j_end = min(m, i + win + 1)
        if j_end - i < 4:
            break
        D = np.abs(T[i + 1:j_end] - T[i][None]).mean(axis=2)       # (t, k) distance of each tile from its state at i
        exc = np.maximum.accumulate(D, axis=0)
        # the tiles that have left BY each moment must all be back at that moment; a tile that departs later (new content
        # arriving after the candidate return) is not part of this return
        left_t = (exc >= EXCURSION) & struct[None, :]                # (t, k)
        nl_t = left_t.sum(axis=1)
        if nl_t[-1] == 0:
            continue
        back = (D <= np.maximum(BACK * exc, 0)) & (D <= NEAR) & left_t   # (t, k) a tile that left is back
        frac = np.where(nl_t > 0, back.sum(axis=1) / np.maximum(nl_t, 1), 0.0)
        left = left_t[-1]
        nl = int(nl_t[-1])
        hit = np.where(frac >= COHERENT)[0]
        # periodic motion (an ambient loop, a spin) returns again and again: two or more separate return episodes in
        # the window is a loop by design, not a rewind
        episodes = int(np.sum((frac[1:] >= COHERENT) & (frac[:-1] < COHERENT))) + int(frac[0] >= COHERENT)
        if episodes >= 2:
            return []                                   # a periodic shot: near its end a window holds only one return
        if len(hit) and first is None:
            b = int(hit[0])
            peak = int(np.argmax(D[:b + 1, left_t[b]].mean(axis=1)))
            nl = int(nl_t[b])
            if peak >= b:
                continue
            # SOMETHING CAME AND WENT is not a rewind: a label shown and then cleared leaves its ground as it found it,
            # and its tiles carry MORE structure at the furthest frame than at either end. A reset is the reverse (the
            # content vanishes, then returns) and a push that returns keeps its structure throughout. On the QR and
            # ANC films every RETURN that was a label appearing and leaving had this shape.
            lt = left_t[b]
            sd0 = float(T[i][lt].std(axis=1).mean())
            sdp = float(T[i + 1 + peak][lt].std(axis=1).mean())
            if sdp > TRANSIENT * sd0 + 2.0:
                continue
            first = [{"kind": "RETURN", "span": (idx[i], idx[i + 1 + b]), "frame": idx[i + 1 + peak], "msg": "inside the shot %d-%d: %d region(s) leave the picture of frame %d "
                     "(furthest at frame %d) and ALL come back to it at frame %d — a reset, a ping-pong push or a move that turns back"
                     % (a, z, nl, idx[i], idx[i + 1 + peak], idx[i + 1 + b])}]
    return first or []


def judge(path, plan=None, cuts=None):
    F = frames(path)
    if F is None:
        return None, "the video could not be read"
    n = len(F)
    if plan is not None:
        segs = plan_segments(plan, n)
        scope = "the film's own plan (%d segment(s))" % len(segs)
    else:
        cs = sorted(cuts) if cuts is not None else detect_cuts(F)
        b = [0] + [c for c in cs if 0 < c < n] + [n]
        segs = [(a, z, "shot") for a, z in zip(b, b[1:])]
        scope = "%s cuts (%d segment(s))" % ("given" if cuts is not None else "DETECTED", len(segs))
    cut_frames = [s[0] for s in segs[1:]]
    probs = replays(F, cut_frames)
    for a, z, kind in segs:
        if kind == "loop":
            continue
        probs += returns(F, a, z)
    return probs, "%d frames, %s" % (n, scope)


def calibrate():
    """synthetic controls: a ping-pong push, a reset, a replayed cut MUST be caught; a steady push, a loop, holds MUST NOT"""
    import tempfile
    rng = np.random.default_rng(3)
    base = (rng.random((360, 640)) * 255).astype(np.uint8)
    base = np.repeat(np.repeat(base[::8, ::8], 8, 0), 8, 1)[:360, :640]

    def clip(fn, n):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "c.mp4")
        pr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", "640x360", "-r", "30", "-i", "-",
                               "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "12", p], stdin=subprocess.PIPE)
        for f in range(n):
            pr.stdin.write(fn(f).astype(np.uint8).tobytes())
        pr.stdin.close(); pr.wait()
        return p

    def shift(dx):
        return np.roll(base, int(round(dx)), axis=1)
    cases = {
        "ping-pong push": (lambda f: shift(40 * np.sin(np.pi * min(f, 60) / 60)), 90, True),
        "reset (typed then cleared)": (lambda f: np.where(np.arange(640)[None, :] < (600 if f < 6 else 10 * f), base, 0), 90, True),
        "steady push": (lambda f: shift(f * 0.8), 90, False),
        "hold": (lambda f: base, 90, False),
        "loop (5 turns)": (lambda f: shift(30 * np.sin(2 * np.pi * f / 18)), 90, False),
        # a label shown for a second on a plain ground, then cleared: an element that came and went, not a rewind
        "label shown, then cleared": (lambda f: np.where((20 <= f < 50) & (np.arange(640)[None, :] < 320)
                                                          & (np.arange(360)[:, None] < 180), base, 90), 90, False),
        # two segments of one take cut back to back, the second starting 20 frames before the first ended (slide-maker v2)
        "replayed cut": (lambda f: shift(1.5 * (f if f < 45 else f - 20)), 90, True, [45]),
        "a cut inside one take (no overlap)": (lambda f: shift(1.5 * f), 90, False, [45]),
    }
    ok = True
    for name, case in cases.items():
        fn, n, want = case[:3]
        probs, _ = judge(clip(fn, n), cuts=case[3] if len(case) > 3 else [])
        got = bool(probs)
        ok &= got == want
        print("[rewind] calibrate %-28s %s (want %s)" % (name, "CAUGHT" if got else "clean", "caught" if want else "clean"))
    return 0 if ok else 1


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    if argv[0] == "--calibrate":
        return calibrate()
    plan = json.load(open(argv[argv.index("--plan") + 1])) if "--plan" in argv else None
    cuts = [int(x) for x in argv[argv.index("--cuts") + 1].split(",") if x.strip()] if "--cuts" in argv else None
    probs, scope = judge(argv[0], plan, cuts)
    if probs is None:
        print("[rewind] UNMEASURED: %s" % scope)
        return 2
    for p in probs:
        print("[rewind] %s %s" % (p["kind"], p["msg"]))
    print("[rewind] scope: %s — %d problem(s)" % (scope, len(probs)))
    if "--json" in argv:
        json.dump(probs, open(argv[argv.index("--json") + 1], "w"), indent=1)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
