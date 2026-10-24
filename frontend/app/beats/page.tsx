"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import BeatCard from "@/components/BeatCard";
import { Beat, CATEGORY_LABELS, Category, Voice, api } from "@/lib/api";
import { usePreviewPlayer } from "@/lib/usePreviewPlayer";
import { CheckIn, isComplete, loadCheckIn, saveCheckIn, toSongRequest } from "@/lib/checkin";

export default function BeatsPage() {
  const router = useRouter();
  const [data, setData] = useState<CheckIn | null>(null);
  const [beats, setBeats] = useState<Beat[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [filter, setFilter] = useState<Category | "all">("all");
  const [loadError, setLoadError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const preview = usePreviewPlayer();

  useEffect(() => {
    const c = loadCheckIn();
    if (!isComplete(c)) {
      router.replace("/check-in");
      return;
    }
    setData(c);
    Promise.all([api.beats(), api.voices()])
      .then(([b, v]) => {
        setBeats(b.beats);
        setCategories(b.categories);
        setVoices(v.voices);
      })
      .catch(() => setLoadError("We couldn't load the beats. Is the Anthem server running?"));
  }, [router]);

  if (!data) return null;
  const update = (patch: Partial<CheckIn>) => {
    const next = { ...data, ...patch };
    setData(next);
    saveCheckIn(next);
  };
  const shown = beats.filter((b) => filter === "all" || b.category === filter);

  const create = async () => {
    if (!data.beatId) {
      setSubmitError("Pick a beat first.");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    preview.stop();
    try {
      const { job_id } = await api.createSong(toSongRequest(data));
      // The free text has done its job; don't keep it around in the browser either.
      update({ freeText: "", freeTextScreened: false });
      router.push(`/generating?job=${job_id}`);
    } catch (e) {
      setSubmitError((e as Error).message);
      setSubmitting(false);
    }
  };

  return (
    <div className="pt-4">
      <h1 className="text-3xl font-extrabold">Pick your beat, {data.name}</h1>
      <p className="mt-2 text-lg text-muted">Tap play to hear a 10-second preview, then choose the one that feels right.</p>

      <div className="mt-6 flex gap-2 overflow-x-auto pb-2" role="group" aria-label="Filter beats by style">
        {(["all", ...categories] as const).map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={filter === c}
            onClick={() => setFilter(c)}
            className={`shrink-0 rounded-full border-2 px-4 py-2 font-semibold ${
              filter === c ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface text-ink"
            }`}
          >
            {c === "all" ? "All" : CATEGORY_LABELS[c]}
          </button>
        ))}
      </div>

      {loadError && (
        <p role="alert" className="mt-6 font-semibold text-danger">
          {loadError}
        </p>
      )}

      <ul role="radiogroup" aria-label="Beats" className="mt-4 grid gap-3 sm:grid-cols-2">
        {shown.map((b) => (
          <BeatCard
            key={b.id}
            beat={b}
            selected={data.beatId === b.id}
            playing={preview.playingId === b.id}
            onSelect={() => update({ beatId: b.id })}
            onTogglePreview={() => preview.toggle(b)}
          />
        ))}
      </ul>

      {voices.length > 0 && (
        <section className="mt-10">
          <h2 className="text-2xl font-extrabold">Choose a voice</h2>
          <div role="radiogroup" aria-label="Voice" className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {voices.map((v) => (
              <button
                key={v.id}
                type="button"
                role="radio"
                aria-checked={data.voiceId === v.id}
                onClick={() => update({ voiceId: v.id })}
                className={`rounded-2xl border-2 p-4 text-left ${
                  data.voiceId === v.id ? "border-primary bg-primary-soft" : "border-line bg-surface"
                }`}
              >
                <span className="block font-bold">{v.label}</span>
                <span className="text-sm text-muted">{v.description}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {submitError && (
        <p role="alert" className="mt-6 font-semibold text-danger">
          {submitError}
        </p>
      )}

      <div className="mt-10 flex items-center justify-between gap-3">
        <button type="button" onClick={() => router.push("/check-in")} className="rounded-full px-5 py-3 font-bold text-muted hover:text-ink">
          ← Back
        </button>
        <button
          type="button"
          onClick={create}
          disabled={submitting || !data.beatId}
          className="rounded-full bg-primary px-8 py-3 text-lg font-bold text-primary-ink shadow-sm hover:brightness-110 disabled:opacity-60"
        >
          {submitting ? "Starting…" : "Create my song ✨"}
        </button>
      </div>
    </div>
  );
}
