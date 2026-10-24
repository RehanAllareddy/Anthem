"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import BreathingGuide from "@/components/BreathingGuide";
import { Song, api } from "@/lib/api";

// A job that hasn't left "queued" by now almost certainly isn't going to.
const STUCK_AFTER_MS = 60_000;

const PROMPTS = [
  "Let your shoulders drop away from your ears.",
  "Unclench your jaw. Soften your hands.",
  "Notice five things you can see around you.",
  "You showed up for yourself today. That matters.",
  "Feel your feet on the ground. You're right here.",
  "There's no rush. Just this breath.",
];

function Generating() {
  const router = useRouter();
  const jobId = useSearchParams().get("job");
  const [song, setSong] = useState<Song | null>(null);
  const [failed, setFailed] = useState("");
  const [prompt, setPrompt] = useState(0);
  const [stuck, setStuck] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setPrompt((p) => (p + 1) % PROMPTS.length), 9000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    const poll = async () => {
      try {
        const s = await api.song(jobId);
        if (cancelled) return;
        setSong(s);
        if (s.status === "done") return router.replace(`/song/${jobId}`);
        if (s.status === "error") return;
        setStuck(s.status === "queued" && Date.now() - started > STUCK_AFTER_MS);
      } catch (e) {
        if (cancelled) return;
        setFailed((e as Error).message);
        return;
      }
      timer = setTimeout(poll, 2000);
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId, router]);

  const error = !jobId ? "We couldn't find your song." : failed || (song?.status === "error" ? song.error : "");

  if (error) {
    return (
      <div className="pt-10 text-center">
        <h1 className="text-3xl font-extrabold">Hmm, that didn&apos;t work</h1>
        <p role="alert" className="mt-3 text-lg text-muted">
          {error}
        </p>
        <Link href="/beats" className="mt-8 inline-flex rounded-full bg-primary px-8 py-3 font-bold text-primary-ink">
          Try again
        </Link>
      </div>
    );
  }

  const pct = Math.round((song?.progress ?? 0.03) * 100);
  return (
    <div className="flex flex-col items-center pt-6 text-center">
      <h1 className="text-3xl font-extrabold">Making your song…</h1>
      <p className="mt-2 text-lg text-muted">While we work, breathe along with the circle.</p>
      <div className="mt-8">
        <BreathingGuide />
      </div>
      <p className="mt-8 min-h-14 max-w-md text-lg italic text-muted">{PROMPTS[prompt]}</p>
      <div className="mt-6 w-full max-w-md">
        <div
          role="progressbar"
          aria-label="Song progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          className="h-2 overflow-hidden rounded-full bg-surface-2"
        >
          <div className="h-full rounded-full bg-primary transition-all duration-700" style={{ width: `${Math.max(pct, 3)}%` }} />
        </div>
        <p className="mt-3 font-semibold" role="status">
          {song?.stage ?? "Getting ready"}…
        </p>
        <p className="mt-1 text-sm text-muted">This usually takes about a minute.</p>
        {stuck && (
          <div role="alert" className="mt-6 rounded-2xl bg-surface-2 p-4 text-left">
            <p className="font-semibold">This is taking longer than it should.</p>
            <p className="mt-1 text-muted">
              Your song hasn&apos;t started yet. You can keep waiting, or go back and try again.
            </p>
            <Link href="/beats" className="mt-3 inline-flex rounded-full bg-primary px-5 py-2 font-bold text-primary-ink">
              Try again
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GeneratingPage() {
  return (
    <Suspense fallback={null}>
      <Generating />
    </Suspense>
  );
}
