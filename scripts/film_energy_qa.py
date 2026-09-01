#!/usr/bin/env python3
"""Does this film USE the fact that it is a film? — a post-render gate on out.mp4.

    python3 scripts/film_energy_qa.py <out_dir>

WHY THIS EXISTS. The remotion tier's whole claim over the html tier is TIME: motion, cutting, light that
changes. A delivered 30-beat film was described by its own author as something the html tier could have
produced, and the measurement agreed — so the claim was not being cashed, and nothing in the pipeline could
tell. Every other gate here asks whether a frame is correct. None asked whether the film moves.

THE FLOORS COME FROM REAL FILMS, not from taste. Four official product launch films were downloaded and
measured with the same instrument as the deck under test — greyscale at 12fps, 192x108:

    film                     frame-diff p75   median ink   luminance range
    Apple  iPhone 17 Pro           0.0357        24.3%          0.270
    OpenAI Codex Micro             0.0075        64.4%          0.330
    Figma  Config launches         0.0481        36.1%          0.903
    Anthropic Keep thinking        0.0381        42.1%          0.350
    ---------------------------------------------------------------------
    the film that prompted this    0.0023         4.3%          0.079

Three of those four are largely LIVE ACTION (Apple adds offline PBR renders), which a DOM compositor cannot
reach and should not chase. Figma's is the reachable one: entirely generative, no camera, and unambiguously
launch-grade. That it sits at the TOP of the motion and luminance columns is the useful part.

Each floor is HALF the lowest reference, deliberately lenient — this is a floor, not a target, and passing it
says only that the film is not a slideshow. The film above fails all three by 3.3x, 5.6x and 3.4x.

WHAT THE NUMBERS DO NOT SAY. Four films is a small corpus and three of them are a different production
category. Ink is measured against a per-frame median ground, so a full-bleed gradient reads as empty — which
is intended, a gradient is not content, but it means a deliberately atmospheric film will score low. A quiet
film can be right; `meta.energy_waiver` accepts one, and requires a written reason, because the discipline
this codebase runs on is that an accepted warning is a decision someone made rather than one that defaulted.
"""
import json
import os
import subprocess
import sys

# Half the lowest of the four reference films, per the table above.
MOTION_P75_FLOOR = 0.0037     # lowest reference 0.0075 (OpenAI, a talking-head film — the quietest kind)
INK_FLOOR = 0.12              # lowest reference 0.243 (Apple: dark frames, one lit subject)
LUMA_RANGE_FLOOR = 0.135      # lowest reference 0.270 (Apple)

REFERENCE = {                 # kept here so a later reader can re-derive the floors rather than trust them
    "Apple iPhone 17 Pro": (0.0357, 0.243, 0.270),
    "OpenAI Codex Micro": (0.0075, 0.644, 0.330),
    "Figma Config": (0.0481, 0.361, 0.903),
    "Anthropic Keep thinking": (0.0381, 0.421, 0.350),
}


def measure(path, fps=12, w=192, h=108):
    """Greyscale frame-difference, ink coverage and luminance spread. Same instrument for every film."""
    try:
        import numpy as np
    except ImportError:
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                          "fps=%d,scale=%d:%d" % (fps, w, h), "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h)
    if n < 8:
        return None
    F = np.frombuffer(raw[:n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32) / 255.0
    d = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
    ink = [float((np.abs(f - np.median(f)) > 0.10).mean()) for f in F[::2]]
    lum = F.mean(axis=(1, 2))
    return {
        "seconds": n / fps,
        "motion_p50": float(np.percentile(d, 50)),
        "motion_p75": float(np.percentile(d, 75)),
        "motion_p90": float(np.percentile(d, 90)),
        "ink_median": float(np.median(ink)),
        "luma_range": float(np.percentile(lum, 95) - np.percentile(lum, 5)),
    }


def check(out_dir):
    mp4 = os.path.join(out_dir, "out.mp4")
    if not os.path.exists(mp4):
        return ["no out.mp4 — this gate reads the delivered film, so it runs after the render"], [], None
    meta = {}
    sb = os.path.join(out_dir, "storyboard.json")
    if os.path.exists(sb):
        try:
            meta = json.load(open(sb, encoding="utf-8")).get("meta") or {}
        except Exception:                                        # noqa: BLE001 - a broken board is another gate's job
            meta = {}
    m = measure(mp4)
    if m is None:
        return ["could not decode %s (needs ffmpeg + numpy)" % mp4], [], None

    errs, warns = [], []
    # p75 rather than p90: measured across the corpus, p90's lowest reference sits close enough to a
    # slideshow that a half-floor would let one through. p75 separates them by 3.3x.
    if m["motion_p75"] < MOTION_P75_FLOOR:
        errs.append("MOTION: frame-diff p75 is %.4f, under the %.4f floor (half the quietest reference "
                    "film's %.4f). Three quarters of this film's frames are within %.2f%% of the frame "
                    "before them — that is a slideshow, and the html tier renders slideshows for a "
                    "fraction of the cost. What this tier is FOR is time."
                    % (m["motion_p75"], MOTION_P75_FLOOR, 0.0075, m["motion_p75"] * 100))
    if m["ink_median"] < INK_FLOOR:
        errs.append("DENSITY: the median frame carries %.1f%% ink, under the %.0f%% floor (half of the "
                    "sparsest reference, Apple's 24.3%%). Apple's sparse frames hold one lit object; an "
                    "empty frame with a caption on it is not sparse, it is unfinished."
                    % (m["ink_median"] * 100, INK_FLOOR * 100))
    if m["luma_range"] < LUMA_RANGE_FLOOR:
        errs.append("LIGHT: luminance spans %.3f across the film, under the %.3f floor (half of Apple's "
                    "0.270; Figma's is 0.903). Nothing gets brighter or darker — the film has no light, "
                    "only a palette." % (m["luma_range"], LUMA_RANGE_FLOOR))

    waiver = (meta.get("energy_waiver") or "").strip()
    if errs and waiver:
        warns = ["ACCEPTED by meta.energy_waiver: %s" % waiver] + ["waived — " + e for e in errs]
        errs = []
    elif errs:
        errs.append("If this film is deliberately quiet, say so in `meta.energy_waiver` with the reason. "
                    "A waiver is a decision someone made; silence is one that defaulted.")
    return errs, warns, m


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: film_energy_qa.py <out_dir>")
        return 2
    out_dir = os.path.abspath(argv[0])
    errs, warns, m = check(out_dir)
    if m:
        print("[film_energy] %.0fs  motion p50/p75/p90 %.4f/%.4f/%.4f  ink %.1f%%  light %.3f"
              % (m["seconds"], m["motion_p50"], m["motion_p75"], m["motion_p90"],
                 m["ink_median"] * 100, m["luma_range"]))
        print("              reference floors: motion p75 >= %.4f · ink >= %.0f%% · light >= %.3f"
              % (MOTION_P75_FLOOR, INK_FLOOR * 100, LUMA_RANGE_FLOOR))
    for w in warns:
        print("[film_energy] WARN  %s" % w)
    for e in errs:
        print("[film_energy] ERROR %s" % e)
    print("[film_energy] %s  %d error(s), %d warning(s)"
          % ("FAIL" if errs else "OK", len(errs), len(warns)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
