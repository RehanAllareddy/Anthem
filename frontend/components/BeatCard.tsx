"use client";

import { Beat, CATEGORY_LABELS } from "@/lib/api";

type Props = {
  beat: Beat;
  selected: boolean;
  playing: boolean;
  onSelect: () => void;
  onTogglePreview: () => void;
};

export default function BeatCard({ beat, selected, playing, onSelect, onTogglePreview }: Props) {
  return (
    <li
      className={`flex items-center gap-3 rounded-2xl border-2 bg-surface p-4 transition ${
        selected ? "border-primary shadow-md" : "border-line"
      }`}
    >
      <button
        type="button"
        onClick={onTogglePreview}
        aria-label={`${playing ? "Stop" : "Play"} 10-second preview of ${beat.name}`}
        className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-accent-soft text-accent hover:brightness-95"
      >
        {playing ? (
          <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden fill="currentColor">
            <rect x="6" y="5" width="4" height="14" rx="1" />
            <rect x="14" y="5" width="4" height="14" rx="1" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" className="ml-0.5 h-5 w-5" aria-hidden fill="currentColor">
            <path d="M7 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L8.5 4.64A1 1 0 0 0 7 5.5Z" />
          </svg>
        )}
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={selected}
        onClick={onSelect}
        className="flex min-w-0 flex-1 flex-col items-start text-left"
      >
        <span className="font-bold">{beat.name}</span>
        <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted">
          <span>{CATEGORY_LABELS[beat.category]}</span>
          <span>{beat.bpm} BPM</span>
          <span className="rounded-full bg-primary-soft px-2 text-ink">{beat.mood}</span>
        </span>
      </button>
      <span
        aria-hidden
        className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 ${
          selected ? "border-primary bg-primary text-primary-ink" : "border-line"
        }`}
      >
        {selected ? "✓" : ""}
      </span>
    </li>
  );
}
