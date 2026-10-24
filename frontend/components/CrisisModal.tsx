"use client";

import { useEffect, useRef } from "react";
import ResourceList from "./ResourceList";

type Props = {
  open: boolean;
  isTeen: boolean;
  onContinue: () => void;
};

// Native <dialog> gives us focus trapping, Esc handling and inert background for free.
export default function CrisisModal({ open, isTeen, onContinue }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="crisis-title"
      onCancel={(e) => {
        e.preventDefault();
        onContinue();
      }}
      className="m-auto w-[min(34rem,calc(100vw-2rem))] rounded-3xl bg-bg p-0 text-ink shadow-2xl"
    >
      <div className="max-h-[85dvh] overflow-y-auto p-6">
        <h2 id="crisis-title" className="text-2xl font-extrabold">
          Thank you for sharing that with us
        </h2>
        <p className="mt-3 text-lg leading-relaxed">
          It sounds like things might be really heavy right now. You deserve support from a real person, and you
          don&apos;t have to go through this alone. These free services are there any time, day or night:
        </p>
        <div className="mt-4">
          <ResourceList />
        </div>
        <p className="mt-4 text-muted">
          {isTeen
            ? "Talking to a trusted adult, like a parent, school counselor, coach, or teacher, can help too. "
            : "Reaching out to someone you trust can help too. "}
          If you&apos;re in immediate danger, call 911.
        </p>
        <p className="mt-4 text-muted">
          If you&apos;d still like your song, you can keep going. We&apos;ll leave what you wrote out of the lyrics and
          keep the song focused on you and what you love.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <a
            href="/support"
            className="rounded-full border border-line bg-surface px-5 py-3 text-center font-bold text-accent"
          >
            See all support options
          </a>
          <button
            type="button"
            autoFocus
            onClick={onContinue}
            className="rounded-full bg-primary px-5 py-3 font-bold text-primary-ink"
          >
            Continue making my song
          </button>
        </div>
      </div>
    </dialog>
  );
}
