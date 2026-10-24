"use client";

import { useEffect, useState } from "react";

// 4s in, 2s hold, 6s out: a slow exhale helps calm the nervous system.
const PHASES = [
  { label: "Breathe in", seconds: 4 },
  { label: "Hold", seconds: 2 },
  { label: "Breathe out", seconds: 6 },
];
const CYCLE = PHASES.reduce((s, p) => s + p.seconds, 0);

export default function BreathingGuide() {
  const [t, setT] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setT((x) => (x + 1) % CYCLE), 1000);
    return () => clearInterval(id);
  }, []);

  let acc = 0;
  const phase = PHASES.find((p) => (acc += p.seconds) > t) ?? PHASES[0];

  return (
    <div className="flex flex-col items-center gap-6">
      <div className="relative grid h-56 w-56 place-items-center" aria-hidden>
        <div className="absolute inset-0 rounded-full bg-primary-soft opacity-60" />
        <div
          className="absolute inset-4 rounded-full bg-primary/25"
          style={{ animation: `breathe ${CYCLE}s ease-in-out infinite` }}
        />
        <div
          className="absolute inset-12 rounded-full bg-accent-soft"
          style={{ animation: `breathe ${CYCLE}s ease-in-out infinite` }}
        />
      </div>
      {/* Announcing every phase change would be noisy for screen readers; describe it once instead. */}
      <p className="text-2xl font-bold" aria-hidden>
        {phase.label}
      </p>
      <p className="sr-only">Breathing exercise: breathe in for 4 seconds, hold for 2, then breathe out for 6.</p>
    </div>
  );
}
