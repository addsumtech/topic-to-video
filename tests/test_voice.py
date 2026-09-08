"""The narration as a signal — and the properties that separate a signal from an ornament.

`VoiceSignal` shipped for months with a header claiming it "reads the real narration via @remotion/media-utils
visualizeAudio". It did not: the package was not a dependency and the bars were three sines of the frame
number. Nothing failed, because nothing here could tell the difference between a waveform and a sine bank —
they are both bars of varying height, and every gate this project owns measures pixels moving.

The difference a viewer can see is GAPS. Speech stops between phrases; a sine bank never does. So these tests
pin that property on both paths — the live analysis and the synthetic stand-in a standalone render gets — and
pin the two invariants the measured curve was fitted for: silence reads as silence, and the picture does not
change when the same voice is quieter.
"""
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")

_NEEDS_NODE = pytest.mark.skipif(
    not (shutil.which("npx") and shutil.which("node") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")
_NEEDS_FFMPEG = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _run(body, files=()):
    """Bundle a probe against the real module and run it under node."""
    tmp = tempfile.mkdtemp(prefix="voice_", dir=_REM)
    try:
        entry = os.path.join(tmp, "probe.ts")
        head = ("import {_internals as V} from %s;\n"
                "import {visualizeAudio} from '@remotion/media-utils';\n"
                "const out: any = {};\nconst FILES: any = %s;\n"
                % (json.dumps(os.path.join(_REM, "src", "runtime", "voice")), json.dumps(dict(files))))
        open(entry, "w", encoding="utf-8").write(head + body + "\nconsole.log(JSON.stringify(out));\n")
        outf = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--outfile=" + outf,
                            "--log-level=error"], cwd=_REM, capture_output=True, text=True)
        assert b.returncode == 0, b.stdout + b.stderr
        r = subprocess.run(["node", outf], cwd=_REM, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _speech_like(dirpath, gain_db=0):
    """A deterministic stand-in for narration: 0.6s of voiced tone, 0.4s of nothing, four times over.

    A committed mp3 would be a real recording nobody can regenerate, and a fixture drawn from the demo film
    would tie the test to that film's copy. What the assertions below actually need is a clip that is loud
    part of the time and silent the rest — which ffmpeg can state exactly, so the expected answer is known
    rather than merely observed."""
    sr = 48000
    out = os.path.join(dirpath, "speech%d.raw" % gain_db)
    # a two-formant tone reads to an FFT much more like a voice than a pure sine: energy low, harmonics above.
    # Everything stays INSIDE the complex graph — ffmpeg refuses `-af` on a stream fed from one.
    graph = ("sine=frequency=180:sample_rate={sr}:duration=4,volume=0.7[a];"
             "sine=frequency=760:sample_rate={sr}:duration=4,volume=0.3[b];"
             "[a][b]amix=inputs=2,volume='if(lt(mod(t,1.0),0.6),1,0)':eval=frame{g}[o]").format(
                 sr=sr, g=(",volume=%ddB" % gain_db) if gain_db else "")
    cmd = ["ffmpeg", "-v", "error", "-filter_complex", graph, "-map", "[o]",
           "-ac", "1", "-ar", str(sr), "-f", "f32le", out, "-y"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out, sr


_ANALYSE = """
  const fs = require('fs');
  function levels(path: string, sr: number, n: number) {
    const b = fs.readFileSync(path);
    const wave = new Float32Array(b.buffer, b.byteOffset, b.length / 4);
    const ad: any = {resultId: path, channelWaveforms: [wave], sampleRate: sr,
      durationInSeconds: wave.length / sr, numberOfChannels: 1, isRemote: false};
    const bins = V.binsFor(n);
    const rows: number[][] = [];
    for (let f = 0; f < Math.floor(ad.durationInSeconds * 30); f++) {
      // the WHOLE live path — fold, then tilt, then curve. Measuring `fold().map(curve)` here would test a
      // pipeline the register does not use, which is how a test goes green on code nobody runs.
      rows.push(V.tilted(V.fold(visualizeAudio({audioData: ad, frame: f, fps: 30, numberOfSamples: bins}), n))
        .map(V.curve));
    }
    return rows;
  }
"""


@_NEEDS_NODE
@_NEEDS_FFMPEG
def test_a_silence_reads_as_silence_and_a_voice_reads_as_a_voice(tmp_path):
    """The one property the sine bank could never have. The clip is loud for 0.6s of every second and off for
    the other 0.4s, so the answer is known in advance: the quiet frames must collapse and the loud ones must
    not."""
    raw, sr = _speech_like(str(tmp_path))
    out = _run(_ANALYSE + """
      const rows = levels(FILES.raw, FILES.sr, 72);
      const peak = rows.map((r) => Math.max(...r));
      // a frame is 1/30s; classify by where its centre sits inside the 1s cycle, keeping clear of the edges
      const quiet: number[] = [], loud: number[] = [];
      rows.forEach((_, f) => {
        const ph = ((f + 0.5) / 30) % 1;
        if (ph > 0.68 && ph < 0.96) quiet.push(peak[f]);
        else if (ph > 0.08 && ph < 0.52) loud.push(peak[f]);
      });
      const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / Math.max(1, a.length);
      out.quiet = mean(quiet); out.loud = mean(loud);
      out.quietMax = Math.max(...quiet); out.frames = rows.length;
    """, files={"raw": raw, "sr": sr})
    assert out["frames"] > 100, out
    assert out["loud"] > 0.45, "a voiced frame does not read as voiced: %r" % out
    assert out["quiet"] < 0.02, "the gaps between phrases are not silent: %r" % out
    assert out["quietMax"] < 0.12, "some silent frame still draws a tall bar: %r" % out


@_NEEDS_NODE
@_NEEDS_FFMPEG
def test_the_same_voice_quieter_draws_the_same_picture(tmp_path):
    """`tts.py` masters narration to -14 LUFS, but a film may be handed a raw file, and a user may hand it a
    voice recorded 20 dB down. Normalising against the CLIP's peak (which is what `visualizeAudio` does, and
    the reason the curve constants are stated as absolute numbers at all) makes the register's appearance a
    property of the SPEECH rather than of the recording level."""
    loud, sr = _speech_like(str(tmp_path), 0)
    quiet, _ = _speech_like(str(tmp_path), -20)
    out = _run(_ANALYSE + """
      const a = levels(FILES.loud, FILES.sr, 48), b = levels(FILES.quiet, FILES.sr, 48);
      let worst = 0;
      const fa: number[] = [], fb: number[] = [];
      for (let f = 0; f < Math.min(a.length, b.length); f++)
        for (let i = 0; i < a[f].length; i++) {
          worst = Math.max(worst, Math.abs(a[f][i] - b[f][i]));
          fa.push(a[f][i]); fb.push(b[f][i]);
        }
      fa.sort((x, y) => x - y); fb.sort((x, y) => x - y);
      const q = (arr: number[], p: number) => arr[Math.min(arr.length - 1, Math.floor(p * arr.length))];
      out.worst = worst; out.n = Math.min(a.length, b.length);
      out.pct = [0.3, 0.5, 0.7, 0.9, 0.99].map((p) => Math.abs(q(fa, p) - q(fb, p)));
    """, files={"loud": loud, "quiet": quiet, "sr": sr})
    assert out["n"] > 100
    # The DISTRIBUTION is what a viewer sees, and it is unchanged.
    assert max(out["pct"]) < 0.005, "the shape of the waveform moved with the level: %r" % out["pct"]
    # No single bar moves visibly either. It is not bit-identical, and the reason is worth writing down: the
    # analysis quantises to int16 before the FFT, so a clip 20 dB down carries 20 dB less of the quantiser's
    # range and its quiet bins land on slightly different steps. That floor is ~0.02 of a bar's height on a
    # pure tone — invisible, and it does not grow with the attenuation of real speech (a real clip measured
    # identical to three decimals at every percentile).
    assert out["worst"] < 0.03, "a 20 dB attenuation changed a bar by %.3f" % out["worst"]


@_NEEDS_NODE
def test_the_synthetic_stand_in_also_stops_talking(tmp_path):
    """Every standalone still and every energy-sweep row is measured on the stand-in, so if IT never goes
    quiet, the library's own record of this register describes something no viewer will ever see. It is also
    the fallback if a narration file is ever unreadable — a fallback that behaves unlike the real thing turns
    a missing asset into a silently different shot."""
    out = _run("""
      const peak: number[] = [];
      for (let f = 0; f < 300; f++) peak.push(Math.max(...V.synth(64, f, 30, 0)));
      out.min = Math.min(...peak); out.max = Math.max(...peak);
      out.quietFrac = peak.filter((p) => p < 0.08).length / peak.length;
      out.deterministic = JSON.stringify(V.synth(64, 41, 30, 3)) === JSON.stringify(V.synth(64, 41, 30, 3));
      out.differsBySeed = JSON.stringify(V.synth(64, 41, 30, 0)) !== JSON.stringify(V.synth(64, 41, 30, 3));
      out.bounded = peak.every((p) => p >= 0 && p <= 1);
    """)
    assert out["deterministic"] and out["bounded"], out
    assert out["differsBySeed"], "every register drawing the stand-in would draw the identical waveform"
    assert out["max"] > 0.6, "the stand-in never gets loud: %r" % out
    assert out["quietFrac"] > 0.08, "the stand-in never stops talking — the exact defect this replaced: %r" % out


@_NEEDS_NODE
def test_the_bin_count_can_never_make_visualizeAudio_throw():
    """`visualizeAudio` rejects a non-power-of-two with a TypeError. A register asks for the number of bars its
    composition has room for — 72 at 16:9, 39 at 9:16 — and must not have to know that."""
    out = _run("""
      out.rows = [1, 8, 9, 40, 64, 72, 127, 129, 256].map((n) => {
        const b = V.binsFor(n);
        return [n, b, (b & (b - 1)) === 0, b >= n, V.fold(new Array(b).fill(0.5), n).length];
      });
    """)
    for n, bins, pow2, big_enough, folded in out["rows"]:
        assert pow2, "binsFor(%d) = %d is not a power of two" % (n, bins)
        # `fold` must never repeat a bin across two buckets, and this is what guarantees it up to the cap
        assert big_enough, "binsFor(%d) = %d cannot fill %d buckets without repeating one" % (n, bins, n)
        assert folded == n, (n, folded)


@_NEEDS_NODE
def test_asking_for_more_bars_than_the_fft_can_resolve_is_capped_not_faked():
    """The cap lives in `Voice`, so a register that asks for 400 bars gets 256 real ones rather than 400 with
    a fringe of identical twins. A register CAN ask — `SpectrumPulse` sizes its bar count from the ring's
    circumference, which on a large frame is free to exceed what a 30fps FFT window resolves."""
    src = open(os.path.join(_REM, "src", "runtime", "voice.tsx"), encoding="utf-8").read()
    body = src[src.index("export const Voice"):]
    assert "Math.min(256" in body.split("return src")[0], (
        "Voice no longer caps `samples`, so fold() can be asked to invent buckets")


@_NEEDS_NODE
def test_folding_averages_and_never_invents():
    """A bucket must lie inside the bins it covers. Anything else — a peak-pick, an interpolation past the
    ends — would be the module inventing signal, which is the same class of defect as the sine bank."""
    out = _run("""
      const src = Array.from({length: 64}, (_, i) => (i % 7) / 6);
      const f = V.fold(src, 16);
      out.len = f.length;
      out.inRange = f.every((v: number) => v >= Math.min(...src) - 1e-12 && v <= Math.max(...src) + 1e-12);
      out.mean = f.reduce((a: number, b: number) => a + b, 0) / f.length;
      out.srcMean = src.reduce((a, b) => a + b, 0) / src.length;
      out.zeroStaysZero = V.fold(new Array(32).fill(0), 8).every((v: number) => v === 0);
    """)
    assert out["len"] == 16 and out["inRange"] and out["zeroStaysZero"]
    assert abs(out["mean"] - out["srcMean"]) < 0.02, out


@_NEEDS_NODE
def test_the_curve_is_monotone_and_leaves_silence_at_zero():
    out = _run("""
      const xs = [0, 1e-6, 1e-4, 1e-3, 1e-2, 0.1, 0.3, 1];
      out.ys = xs.map(V.curve);
      out.neg = V.curve(-1);
    """)
    ys = out["ys"]
    assert ys[0] == 0, "silence is not zero: %r" % ys[0]
    assert out["neg"] == 0, "a negative magnitude must clamp, not reflect"
    assert all(a < b for a, b in zip(ys, ys[1:])), ys
    assert ys[-1] <= 1
    # compressive, not linear: 100x the energy is well under 100x the bar, or a plosive is the only thing seen
    assert ys[4] / max(1e-9, ys[3]) < 6, ys


def test_the_register_no_longer_claims_what_it_does_not_do():
    """The failure that started this file was a COMMENT — the code was honest about being sines, the header was
    not. So the check is on both halves: the dependency exists, and the shot goes through the shared lens."""
    pkg = json.load(open(os.path.join(_REM, "package.json"), encoding="utf-8"))
    assert "@remotion/media-utils" in pkg["dependencies"], (
        "the register's claim to read the narration rests on a package that is not declared")
    src = open(os.path.join(_REM, "src", "shots", "VoiceSignal.tsx"), encoding="utf-8").read()
    assert "from '../runtime/voice'" in src, "VoiceSignal is not reading the shared voice module"
    assert "Math.sin(i * 0.34" not in src, "the sine bank came back"
    assert "useCurrentFrame" not in src, (
        "VoiceSignal reads the raw frame again — it would animate through the cross-dissolve and ignore "
        "reduced motion")


def test_the_film_hands_every_beat_its_own_narration():
    """The whole mechanism: without this provider the register is audio-reactive in principle and synthetic in
    every delivered film, which is indistinguishable from the bug it replaced."""
    film = open(os.path.join(_REM, "src", "Film.tsx"), encoding="utf-8").read()
    assert "NarrationContext.Provider" in film, "the film provides no narration to its shots"
    assert "value={sc.mp3 ?? null}" in film, "the provider does not carry THIS beat's audio"
    # it must be INSIDE the per-scene Sequence, or every beat analyses the same file
    seq = film.split("<TransitionSeries.Sequence")[1]
    assert seq.index("NarrationContext.Provider") < seq.index("</TransitionSeries.Sequence>"), (
        "the narration provider is outside the per-scene Sequence")

@_NEEDS_NODE
@_NEEDS_FFMPEG
def test_level_reaches_both_ends_on_both_paths(tmp_path):
    """`level` is what a register modulates by rather than draws — a label's opacity, a ring's swell. Both
    paths must therefore span the same usable range, or a standalone still pulses differently from the
    delivered film and stops being evidence about it.

    It pins the ENDS, not the median, and the reason is in `voice.tsx`: what separates real speech from any
    synthesised fixture here is dynamics, not spectrum. A gated tone is either fully on or fully off, so its
    median frame is also its loudest; a real voice spends most of its frames in between. The constants that
    align the two medians were measured on real narration and are recorded there — a fixture that could
    re-derive them would be a model of speech, and the test would then be measuring the model."""
    raw, sr = _speech_like(str(tmp_path))
    out = _run(_ANALYSE + """
      const rows = levels(FILES.raw, FILES.sr, 64);
      const live = rows.map((r) => V.levelOf(r, V.LIVE_LEVEL));
      const syn: number[] = [];
      for (let f = 0; f < 400; f++) syn.push(V.levelOf(V.synth(64, f, 30, 0), V.SYNTH_LEVEL));
      out.liveMin = Math.min(...live); out.liveMax = Math.max(...live);
      out.synMin = Math.min(...syn); out.synMax = Math.max(...syn);
      out.pinned = syn.filter((v) => v >= 0.999).length / syn.length;
      out.zero = V.levelOf(new Array(64).fill(0), V.LIVE_LEVEL);
      out.mono = V.levelOf(new Array(64).fill(0.4), V.LIVE_LEVEL)
               > V.levelOf(new Array(64).fill(0.2), V.LIVE_LEVEL);
      out.clamped = V.levelOf(new Array(64).fill(1), 4);   // a hot signal must not run past 1
    """, files={"raw": raw, "sr": sr})
    assert out["zero"] == 0 and out["mono"] and out["clamped"] == 1, out
    for k in ("liveMin", "synMin"):
        assert out[k] < 0.02, "%s never reaches silence: %r" % (k, out[k])
    for k in ("liveMax", "synMax"):
        # half the range, not more: this fixture is two tones, so its spectrum is narrower than speech and
        # its ceiling correspondingly lower (real narration measures 0.75 against the fixture's 0.60). What
        # is being checked is that a loud frame USES the range — a modulation that never passes halfway is
        # one nobody sees.
        assert out[k] > 0.5, "%s never reaches the top of the range: %r" % (k, out[k])
    assert out["pinned"] < 0.02, (
        "the stand-in sits at the ceiling %.0f%% of the time — a modulation that is always 1 is not one"
        % (100 * out["pinned"]))


@_NEEDS_NODE
def test_the_tilt_shows_the_spectrum_and_never_invents_a_signal():
    """A voice rolls off with frequency, so raw magnitudes draw three tall bars and a flat line — a bass
    meter, not a picture of speech. The tilt is the correction every spectrum analyser has. What makes it a
    display transform rather than an invention is that it MULTIPLIES: silence times any gain is silence."""
    out = _run("""
      out.silence = V.tilted(new Array(32).fill(0));
      const flat = V.tilted(new Array(32).fill(0.1));
      out.first = flat[0]; out.last = flat[flat.length - 1];
      out.monotone = flat.every((v: number, i: number) => i === 0 || v > flat[i - 1]);
      out.single = V.tilted([0.4]);            // one bucket: no frequency axis to tilt along
    """)
    assert all(v == 0 for v in out["silence"]), "the tilt lifted silence off the floor"
    assert abs(out["first"] - 0.1) < 1e-12, "the lowest bucket must pass through untouched"
    assert out["last"] > out["first"] * 3, "the high end is not lifted enough to be visible"
    assert out["monotone"], "the gain is not monotone in frequency"
    assert out["single"] == [0.4], "a single bucket divided by zero"
    # AND it must be in the path the register actually renders. Every measurement above builds the pipeline
    # itself, so removing the tilt from `LiveVoice` leaves them all green — a mutation run proved exactly
    # that. This is the one assertion that reads the composition rather than reconstructing it.
    src = open(os.path.join(_REM, "src", "runtime", "voice.tsx"), encoding="utf-8").read()
    live = src[src.index("const LiveVoice"):src.index("/** Give me the voice")]
    assert "tilted(fold(" in live, (
        "the live path no longer tilts what it draws — the register is a bass meter again")
