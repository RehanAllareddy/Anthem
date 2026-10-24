"""Synthesize Echorie's placeholder beat library.

Every loop is rendered from scratch with numpy (no samples, no third-party audio),
so the output is ours to license as CC0. Loops are an exact number of bars long and
any note tail that runs past the end is wrapped back to the start, so they repeat
seamlessly when the mixer tiles them.

Usage:
    python beats/generate_beats.py            # (re)generate all placeholder beats
    python beats/generate_beats.py --only rap-cipher

Hand-added entries in beats.json (anything whose source is not this script) are
left untouched.
"""
from __future__ import annotations

import argparse
import json
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

SR = 44100
BEATS_DIR = Path(__file__).resolve().parent
LOOPS_DIR = BEATS_DIR / "loops" / "generated"
MANIFEST = BEATS_DIR / "beats.json"
GENERATED_SOURCE = "generated://beats/generate_beats.py"
GENERATED_LICENSE = "CC0-1.0 (synthesized by Echorie's generate_beats.py)"

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]


# ---------------------------------------------------------------- spec ------

@dataclass
class BeatSpec:
    id: str
    name: str
    category: str  # upbeat | chill | pop | rap | rock
    bpm: int
    key: str  # e.g. "C major", "A minor"
    mood: str
    progression: List[int]  # scale degrees (1-based), one chord per bar
    drums: Dict[str, str]  # instrument -> 16-step pattern ("x" hit, "o" accent-less ghost, "." rest)
    lead: str  # chords timbre: "pad" | "keys" | "pluck" | "power" | "bell"
    bass: str  # "root8" | "root4" | "808" | "walk" | "sync"
    bars: int = 8
    swing: float = 0.0  # 0..0.5, delays every second 16th
    halftime: bool = False  # trap-style: hats at double resolution
    arp: bool = False
    extra: Dict[str, str] = field(default_factory=dict)

    @property
    def root_midi(self) -> int:
        name, _ = self.key.split()
        return 48 + NOTE_NAMES.index(name)  # octave 3

    @property
    def scale(self) -> List[int]:
        return MINOR if self.key.endswith("minor") else MAJOR


# Patterns: 16 steps per bar.
FOUR_FLOOR = {
    "kick": "x...x...x...x...",
    "snare": "....x.......x...",
    "hat": "..x...x...x...x.",
    "clap": "....x.......x...",
}
POP_DRUMS = {
    "kick": "x.....x...x.....",
    "snare": "....x.......x...",
    "hat": "x.x.x.x.x.x.x.x.",
}
LOFI_DRUMS = {
    "kick": "x......x..x.....",
    "snare": "....x.......x...",
    "hat": "x.x.x.x.x.x.x.xo",
}
BOOMBAP = {
    "kick": "x.......x.x.....",
    "snare": "....x.......x...",
    "hat": "x.x.x.x.x.x.x.x.",
}
TRAP = {
    "kick": "x.....x.........",
    "snare": "........x.......",
    "hat": "x.x.x.x.x.xxx.x.",
}
ROCK_DRUMS = {
    "kick": "x.....x.x.......",
    "snare": "....x.......x...",
    "hat": "x.x.x.x.x.x.x.x.",
    "crash": "x...............",
}

SPECS: List[BeatSpec] = [
    # Upbeat
    BeatSpec("upbeat-sunrise", "Sunrise Sprint", "upbeat", 124, "C major", "bright",
             [1, 5, 6, 4, 1, 5, 4, 4], FOUR_FLOOR, "pluck", "root8", arp=True),
    BeatSpec("upbeat-confetti", "Confetti Rush", "upbeat", 128, "G major", "hype",
             [1, 4, 6, 5, 1, 4, 5, 5], FOUR_FLOOR, "keys", "sync", arp=True),
    BeatSpec("upbeat-golden", "Golden Hour Bounce", "upbeat", 118, "D major", "joyful",
             [4, 1, 5, 6, 4, 1, 5, 5],
             {**FOUR_FLOOR, "hat": "x.xxx.x.x.xxx.x."}, "bell", "sync"),
    # Chill / Down
    BeatSpec("chill-rainy", "Rainy Window", "chill", 72, "A minor", "cozy",
             [1, 6, 3, 7, 1, 6, 4, 5], LOFI_DRUMS, "keys", "root4", swing=0.18),
    BeatSpec("chill-tide", "Slow Tide", "chill", 80, "F major", "peaceful",
             [1, 3, 4, 4, 1, 3, 2, 5], {"kick": "x.......x.......", "hat": "..x...x...x...x."},
             "pad", "root4", swing=0.1),
    BeatSpec("chill-lantern", "Lantern Light", "chill", 68, "E minor", "reflective",
             [1, 4, 6, 5, 1, 4, 7, 7], LOFI_DRUMS, "bell", "root4", swing=0.2),
    # Pop
    BeatSpec("pop-brightside", "Bright Side", "pop", 104, "G major", "hopeful",
             [1, 5, 6, 4, 1, 5, 6, 4], POP_DRUMS, "keys", "root8"),
    BeatSpec("pop-paperhearts", "Paper Hearts", "pop", 96, "C major", "warm",
             [6, 4, 1, 5, 6, 4, 1, 5], {**POP_DRUMS, "clap": "....x.......x..."}, "pluck", "sync", arp=True),
    BeatSpec("pop-neon", "Neon Skies", "pop", 110, "A minor", "dreamy",
             [1, 6, 3, 7, 1, 6, 3, 7], {**POP_DRUMS, "kick": "x...x...x...x..."}, "pad", "root8", arp=True),
    # Rap / Hip-Hop
    BeatSpec("rap-cipher", "Late Night Cipher", "rap", 88, "C minor", "confident",
             [1, 1, 6, 6, 4, 4, 5, 5], BOOMBAP, "keys", "walk", swing=0.15),
    BeatSpec("rap-riseup", "Rise Up Bars", "rap", 92, "G minor", "determined",
             [1, 6, 7, 5, 1, 6, 7, 5], BOOMBAP, "bell", "root4", swing=0.12),
    BeatSpec("rap-skyline", "Skyline Trap", "rap", 140, "F minor", "powerful",
             [1, 1, 6, 6, 3, 3, 7, 7], TRAP, "pad", "808", halftime=True),
    # Rock
    BeatSpec("rock-openroad", "Open Road", "rock", 132, "E major", "free",
             [1, 5, 6, 4, 1, 5, 4, 4], ROCK_DRUMS, "power", "root8"),
    BeatSpec("rock-garage", "Garage Spark", "rock", 140, "A major", "energetic",
             [1, 4, 5, 4, 1, 4, 5, 5], {**ROCK_DRUMS, "kick": "x.x...x.x.x....."}, "power", "root8"),
    BeatSpec("rock-thunder", "Thunder Heart", "rock", 120, "D minor", "brave",
             [1, 6, 3, 7, 1, 6, 7, 7], ROCK_DRUMS, "power", "root8"),
]


# --------------------------------------------------------------- synth ------

def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / max(decay, 1e-4))


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    # One-pole filter; plenty for soft placeholder timbres.
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


_rng = np.random.default_rng(7)


def kick(n808: bool = False) -> np.ndarray:
    dur = 0.9 if n808 else 0.35
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t * (18 if n808 else 30))
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t / (0.45 if n808 else 0.12))
    click = _rng.standard_normal(n) * np.exp(-t / 0.003) * 0.3
    return np.tanh(1.5 * (body + click)) * 0.9


def snare() -> np.ndarray:
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    noise = np.diff(_rng.standard_normal(n + 1)) * np.exp(-t / 0.06) * 0.35
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.5
    return noise + tone


def clap() -> np.ndarray:
    n = int(SR * 0.2)
    t = np.arange(n) / SR
    bursts = sum(np.exp(-np.clip(t - d, 0, None) / 0.008) * (t >= d) for d in (0, 0.01, 0.02))
    tail = np.exp(-t / 0.07)
    return np.diff(_rng.standard_normal(n + 1)) * (bursts * 0.5 + tail * 0.3) * 0.5


def hat(open_: bool = False) -> np.ndarray:
    n = int(SR * (0.25 if open_ else 0.05))
    t = np.arange(n) / SR
    x = np.diff(np.diff(_rng.standard_normal(n + 2)))
    return x * np.exp(-t / (0.08 if open_ else 0.015)) * 0.12


def crash() -> np.ndarray:
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    return np.diff(_rng.standard_normal(n + 1)) * np.exp(-t / 0.4) * 0.12


def tone(freq: float, n: int, kind: str) -> np.ndarray:
    t = np.arange(n) / SR
    if kind == "sine":
        return np.sin(2 * np.pi * freq * t)
    if kind == "tri":
        return 2 * np.abs(2 * ((freq * t) % 1) - 1) - 1
    if kind == "saw":
        # Two slightly detuned saws for width.
        return ((freq * t) % 1 * 2 - 1) * 0.5 + ((freq * 1.004 * t) % 1 * 2 - 1) * 0.5
    raise ValueError(kind)


def chord_notes(spec: BeatSpec, degree: int, octave_shift: int = 0) -> List[int]:
    scale = spec.scale
    idx = degree - 1
    notes = []
    for step in (0, 2, 4):
        i = idx + step
        notes.append(spec.root_midi + 12 * octave_shift + scale[i % 7] + 12 * (i // 7))
    return notes


# -------------------------------------------------------------- render ------

def place(buf: np.ndarray, sample: np.ndarray, at: int, gain: float = 1.0) -> None:
    """Add sample at position, wrapping the tail to the loop start."""
    n = len(buf)
    end = at + len(sample)
    if end <= n:
        buf[at:end] += sample * gain
    else:
        first = n - at
        buf[at:] += sample[:first] * gain
        rest = sample[first:]
        while len(rest):
            take = min(len(rest), n)
            buf[:take] += rest[:take] * gain
            rest = rest[take:]


def render(spec: BeatSpec) -> np.ndarray:
    beat_s = 60.0 / spec.bpm
    bar_n = int(round(beat_s * 4 * SR))
    total = bar_n * spec.bars
    step_n = bar_n / 16

    def step_pos(bar: int, step: int, resolution: int = 16) -> int:
        sn = bar_n / resolution
        swing = spec.swing * sn if (step % 2 == 1 and resolution == 16) else 0
        return int(bar * bar_n + step * sn + swing)

    drums = np.zeros(total)
    music = np.zeros(total)
    bass = np.zeros(total)

    kits = {
        "kick": kick(n808=spec.bass == "808"),
        "snare": snare(),
        "clap": clap(),
        "hat": hat(),
        "crash": crash(),
    }
    gains = {"kick": 1.0, "snare": 0.8, "clap": 0.55, "hat": 1.0, "crash": 1.0}

    for bar in range(spec.bars):
        for inst, pattern in spec.drums.items():
            if inst == "crash" and bar % 4 != 0:
                continue
            for step, ch in enumerate(pattern):
                if ch == ".":
                    continue
                g = gains[inst] * (0.5 if ch == "o" else 1.0)
                # Small velocity humanization, deterministic per position.
                g *= 0.9 + 0.1 * ((bar * 16 + step) * 7 % 5) / 4
                place(drums, kits[inst], step_pos(bar, step), g)
        if spec.halftime and bar % 2 == 1:
            # Trap hat roll in the last beat of every other bar.
            for k in range(8):
                place(drums, kits["hat"], int(bar * bar_n + 3 * beat_s * SR + k * step_n / 2), 0.8)

    # Chords
    for bar, degree in enumerate(spec.progression[: spec.bars]):
        notes = chord_notes(spec, degree, octave_shift=1 if spec.lead in ("pluck", "bell") else 0)
        start = bar * bar_n
        if spec.lead == "pad":
            n = bar_n
            s = sum(tone(midi_hz(m), n, "saw") for m in notes) / 3
            s = lowpass(s, 1400) * env(n, 0.25, 3.0) * 0.32
            place(music, s, start)
        elif spec.lead == "keys":
            for hit in (0, 6, 10) if spec.category != "chill" else (0, 8):
                n = int(bar_n * 0.45)
                s = sum(tone(midi_hz(m), n, "tri") for m in notes) / 3
                s = s * env(n, 0.005, 0.35) * 0.28
                place(music, s, start + int(hit * step_n))
        elif spec.lead == "pluck":
            for hit in range(0, 16, 2):
                n = int(step_n * 3)
                m = notes[(hit // 2) % 3]
                s = tone(midi_hz(m), n, "saw")
                s = lowpass(s, 2500) * env(n, 0.002, 0.09) * 0.22
                place(music, s, start + int(hit * step_n))
        elif spec.lead == "bell":
            for i, hit in enumerate((0, 3, 6, 10)):
                n = int(bar_n * 0.5)
                m = notes[i % 3] + 12
                t = np.arange(n) / SR
                s = (np.sin(2 * np.pi * midi_hz(m) * t) + 0.3 * np.sin(2 * np.pi * midi_hz(m) * 3.01 * t))
                s = s * env(n, 0.002, 0.4) * 0.16
                place(music, s, start + int(hit * step_n))
            n = bar_n
            pad = sum(tone(midi_hz(m - 12), n, "sine") for m in notes) / 3
            place(music, pad * env(n, 0.3, 4.0) * 0.12, start)
        elif spec.lead == "power":
            root = notes[0]
            for hit in range(0, 16, 2):
                n = int(step_n * 2)
                s = tone(midi_hz(root), n, "saw") + tone(midi_hz(root + 7), n, "saw") + tone(midi_hz(root + 12), n, "saw")
                s = np.tanh(3.0 * s / 3) * env(n, 0.002, 0.25)
                s = lowpass(s, 3000) * 0.3
                place(music, s, start + int(hit * step_n))

        if spec.arp:
            arp_notes = chord_notes(spec, degree, octave_shift=2)
            for k in range(16):
                if k % 2 == 1 and spec.category != "upbeat":
                    continue
                n = int(step_n * 1.5)
                m = arp_notes[k % 3]
                s = tone(midi_hz(m), n, "tri") * env(n, 0.002, 0.06) * 0.08
                place(music, s, start + int(k * step_n))

        # Bass
        root = chord_notes(spec, degree)[0] - 12
        if spec.bass == "808":
            continue  # the 808 kick carries the low end
        if spec.bass == "root4":
            hits = [(0, 7, root), (8, 7, root)]
        elif spec.bass == "root8":
            hits = [(k, 2, root) for k in range(0, 16, 2)]
        elif spec.bass == "sync":
            hits = [(0, 3, root), (3, 3, root), (6, 2, root + 12), (10, 3, root), (14, 2, root + 7)]
        elif spec.bass == "walk":
            nxt = chord_notes(spec, spec.progression[(bar + 1) % len(spec.progression)])[0] - 12
            hits = [(0, 6, root), (7, 3, root), (10, 3, root + 7), (14, 2, nxt - 1 if nxt > root else nxt + 1)]
        else:
            raise ValueError(spec.bass)
        for step, length, note in hits:
            n = int(step_n * length)
            s = tone(midi_hz(note), n, "sine") * 0.8 + tone(midi_hz(note), n, "tri") * 0.2
            s = s * env(n, 0.004, length * step_n / SR) * 0.55
            place(bass, s, start + int(step * step_n))

    mix = drums * 0.9 + music + bass
    peak = np.max(np.abs(mix)) or 1.0
    return mix / peak * 0.89  # about -1 dBFS headroom


def write_wav(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


def manifest_entry(spec: BeatSpec, rel_path: str) -> dict:
    return {
        "id": spec.id,
        "name": spec.name,
        "category": spec.category,
        "bpm": spec.bpm,
        "key": spec.key,
        "mood": spec.mood,
        "bars": spec.bars,
        "beats_per_bar": 4,
        "file": rel_path,
        "license": GENERATED_LICENSE,
        "source_url": GENERATED_SOURCE,
        **({"feel": "halftime"} if spec.halftime else {}),
    }


def load_manifest() -> List[dict]:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())["beats"]
    return []


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="generate a single beat id")
    args = parser.parse_args(argv)

    specs = [s for s in SPECS if not args.only or s.id == args.only]
    if not specs:
        raise SystemExit(f"Unknown beat id {args.only!r}")

    generated: Dict[str, dict] = {}
    for spec in specs:
        rel = f"loops/generated/{spec.id}.wav"
        audio = render(spec)
        write_wav(BEATS_DIR / rel, audio)
        generated[spec.id] = manifest_entry(spec, rel)
        print(f"  {spec.id:<22} {spec.bpm:>3} bpm  {len(audio) / SR:5.1f}s  -> {rel}")

    # Keep hand-added beats; refresh generated ones in SPECS order.
    existing = load_manifest()
    hand_added = [b for b in existing if b.get("source_url") != GENERATED_SOURCE]
    previous_generated = {b["id"]: b for b in existing if b.get("source_url") == GENERATED_SOURCE}
    ordered: List[dict] = []
    for spec in SPECS:
        entry = generated.get(spec.id) or previous_generated.get(spec.id) or manifest_entry(spec, f"loops/generated/{spec.id}.wav")
        ordered.append(entry)
    MANIFEST.write_text(json.dumps({"beats": ordered + hand_added}, indent=2) + "\n")
    print(f"Wrote {MANIFEST.relative_to(BEATS_DIR.parent)} ({len(ordered) + len(hand_added)} beats)")


if __name__ == "__main__":
    main()
