"""Lay vocal lines over a looped beat, each line starting on a downbeat."""
from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pydub import AudioSegment, effects
from pydub.silence import detect_leading_silence

from .beats import Beat, load_loop

VOCAL_TARGET_DBFS = -16.0
BEAT_TARGET_DBFS = -21.0  # sits under the vocals
INTRO_MIN_MS = 3000
OUTRO_BARS = 2


@dataclass
class VocalLine:
    section: int  # index into lyrics sections
    section_type: str  # verse | chorus
    text: str
    clip: Path


def has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") or shutil.which("avconv"))


def export_audio(audio: AudioSegment, out: Path) -> Path:
    """Export MP3 when ffmpeg is available, otherwise WAV (dev fallback)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if has_ffmpeg():
        target = out.with_suffix(".mp3")
        audio.export(target, format="mp3", bitrate="192k", tags={"artist": "Anthem"})
    else:
        target = out.with_suffix(".wav")
        audio.export(target, format="wav")
    return target


def _trim(seg: AudioSegment) -> AudioSegment:
    start = detect_leading_silence(seg, silence_threshold=-45.0, chunk_size=5)
    end = detect_leading_silence(seg.reverse(), silence_threshold=-45.0, chunk_size=5)
    trimmed = seg[start : len(seg) - end]
    return trimmed if len(trimmed) > 100 else seg


def _level(seg: AudioSegment, target: float) -> AudioSegment:
    return seg if seg.dBFS == float("-inf") else seg.apply_gain(target - seg.dBFS)


def _chorus_fx(seg: AudioSegment, bpm: float) -> AudioSegment:
    """A light double and a tempo-synced echo make choruses feel bigger."""
    eighth = int(60_000 / bpm / 2)
    out = seg + AudioSegment.silent(duration=eighth * 2 + 50, frame_rate=seg.frame_rate)
    out = out.overlay(seg - 9, position=18)  # thickening double
    out = out.overlay(seg.low_pass_filter(3000) - 14, position=eighth)
    out = out.overlay(seg.low_pass_filter(2200) - 20, position=eighth * 2)
    return out


def mix_song(
    beat: Beat,
    lines: List[VocalLine],
    bars_per_line: int,
    out_base: Path,
) -> Tuple[Path, List[dict], int]:
    """Return (audio path, timeline, duration_ms).

    Timeline entries: {"section", "line", "text", "start", "end"} in seconds.
    """
    loop = load_loop(beat)
    bar_ms = len(loop) / beat.bars  # measured from the file, so loops stay sample-aligned
    feel_bpm = beat.feel_bpm

    intro_bars = max(2, math.ceil(INTRO_MIN_MS / bar_ms))
    if intro_bars % 2:
        intro_bars += 1  # land vocals on a phrase boundary

    placed: List[Tuple[int, AudioSegment]] = []
    timeline: List[dict] = []
    cursor_bar = intro_bars
    prev_section = None
    line_in_section = 0
    clip_cache = {}

    for line in lines:
        if prev_section is not None and line.section != prev_section:
            cursor_bar += 1  # one bar breather between sections
            line_in_section = 0
        prev_section = line.section

        if line.clip not in clip_cache:
            clip_cache[line.clip] = _level(
                _trim(AudioSegment.from_file(line.clip)).set_frame_rate(44100).set_channels(2),
                VOCAL_TARGET_DBFS,
            )
        voc = clip_cache[line.clip]
        start_ms = int(round(cursor_bar * bar_ms))
        dry_len = len(voc)
        if line.section_type == "chorus":
            voc = _chorus_fx(voc, feel_bpm)
        placed.append((start_ms, voc))
        timeline.append(
            {
                "section": line.section,
                "line": line_in_section,
                "text": line.text,
                "start": round(start_ms / 1000, 3),
                "end": round((start_ms + dry_len) / 1000, 3),
            }
        )
        line_in_section += 1
        # Long lines spill into extra bars rather than being sped up.
        cursor_bar += max(bars_per_line, math.ceil((dry_len + 120) / bar_ms))

    total_bars = cursor_bar + OUTRO_BARS
    total_ms = int(round(total_bars * bar_ms))
    tail = max((s + len(v) for s, v in placed), default=0)
    if tail > total_ms:
        total_ms = int(math.ceil(tail / bar_ms) * bar_ms)

    beat_track = _level(loop, BEAT_TARGET_DBFS)
    beat_track = (beat_track * math.ceil(total_ms / len(beat_track) + 1))[:total_ms]

    vocals = AudioSegment.silent(duration=total_ms, frame_rate=44100).set_channels(2)
    for start_ms, voc in placed:
        vocals = vocals.overlay(voc, position=start_ms)

    song = beat_track.overlay(vocals)
    song = effects.normalize(song, headroom=1.0)
    song = song.fade_in(1200).fade_out(int(min(OUTRO_BARS * bar_ms, 6000)))
    return export_audio(song, out_base), timeline, total_ms
