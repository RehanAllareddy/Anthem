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
          Thank you for telling us
        </h2>
        <p className="mt-3 text-lg leading-relaxed">
          It sounds really heavy right now. You deserve support from a real person, free and any time:
        </p>
        <div className="mt-4">
          <ResourceList />
        </div>
        <p className="mt-4 text-muted">
          {isTeen ? "A trusted adult, like a parent or school counselor, can help too. " : "Someone you trust can help too. "}
          In immediate danger? Call 911.
        </p>
        <p className="mt-2 text-muted">You can still make your song. We&apos;ll leave what you wrote out of it.</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <a
            href="/support"
            className="rounded-full border border-line bg-surface px-5 py-3 text-center font-bold text-accent"
          >
            More support
          </a>
          <button
            type="button"
            autoFocus
            onClick={onContinue}
            className="rounded-full bg-primary px-5 py-3 font-bold text-primary-ink"
          >
            Continue to my song
          </button>
        </div>
      </div>
    </dialog>
  );
}
