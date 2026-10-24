"use client";

import { useEffect, useRef } from "react";
import { Song, TimelineLine } from "@/lib/api";

type Props = {
  song: Song;
  time: number;
  playing: boolean;
  onSeek: (seconds: number) => void;
};

const SECTION_LABEL = { verse: "Verse", chorus: "Chorus" } as const;

// Word timings aren't returned by TTS, so spread each line's duration across its
// words by length. Close enough to read along with.
function wordProgress(line: TimelineLine, time: number) {
  const words = line.text.split(" ");
  const total = line.text.length || 1;
  const frac = (time - line.start) / Math.max(0.1, line.end - line.start);
  let acc = 0;
  return words.map((w) => {
    const startFrac = acc / total;
    acc += w.length + 1;
    return { word: w, sung: frac >= startFrac };
  });
}

export default function LyricsKaraoke({ song, time, playing, onSeek }: Props) {
  const timeline = song.timeline ?? [];
  const activeIndex = timeline.findIndex((l, i) => time >= l.start && time < (timeline[i + 1]?.start ?? Infinity) && time < l.end + 1.5);
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!playing || !activeRef.current) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    activeRef.current.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }, [activeIndex, playing]);

  const sections = song.sections ?? [];
  return (
    <div className="space-y-8">
      {sections.map((section, si) => (
        <section key={si} aria-label={`${SECTION_LABEL[section.type]} ${si + 1}`}>
          <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-accent">{SECTION_LABEL[section.type]}</h3>
          <ol className="space-y-1">
            {timeline
              .map((l, i) => ({ l, i }))
              .filter(({ l }) => l.section === si)
              .map(({ l, i }) => {
                const active = i === activeIndex;
                return (
                  <li key={i}>
                    <button
                      type="button"
                      ref={active ? activeRef : undefined}
                      aria-current={active ? "true" : undefined}
                      onClick={() => onSeek(l.start)}
                      className={`w-full rounded-xl px-3 py-2 text-left text-xl leading-snug transition-colors sm:text-2xl ${
                        active ? "bg-highlight font-bold text-ink" : "text-muted hover:bg-surface-2"
                      }`}
                    >
                      {active
                        ? wordProgress(l, time).map((w, wi) => (
                            <span key={wi} className={w.sung ? "text-ink" : "text-muted"}>
                              {w.word}{" "}
                            </span>
                          ))
                        : l.text}
                    </button>
                  </li>
                );
              })}
          </ol>
        </section>
      ))}
    </div>
  );
}
