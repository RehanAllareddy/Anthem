import Link from "next/link";

const STEPS = ["Check in", "Pick a beat", "Listen"];
const PROMISES = ["No account", "Private", "Deleted in 24h"];

export default function Welcome() {
  return (
    <section className="flex min-h-[70dvh] flex-col justify-center py-10">
      <h1 className="text-5xl font-extrabold leading-[1.05] tracking-tight sm:text-7xl">
        Your feelings.
        <br />
        <span className="text-gradient">Your song.</span>
      </h1>
      <p className="mt-6 max-w-md text-lg text-muted">
        An uplifting song with your name in it, ready in about a minute.
      </p>

      <div className="mt-10 flex flex-wrap items-center gap-4">
        <Link
          href="/check-in"
          className="rounded-full bg-primary px-8 py-4 text-lg font-bold text-primary-ink shadow-lg shadow-primary/20 transition hover:-translate-y-0.5 hover:brightness-110"
        >
          Make my song
        </Link>
        <ol className="flex items-center gap-2 text-sm font-semibold text-muted" aria-label="How it works">
          {STEPS.map((s, i) => (
            <li key={s} className="flex items-center gap-2">
              {i > 0 && <span aria-hidden>·</span>}
              {s}
            </li>
          ))}
        </ol>
      </div>

      <ul className="mt-14 flex flex-wrap gap-2" aria-label="Your privacy">
        {PROMISES.map((p) => (
          <li key={p} className="rounded-full bg-surface/70 px-3 py-1 text-sm text-muted ring-1 ring-line backdrop-blur">
            {p}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-muted">A wellbeing tool, not a replacement for therapy or medical care.</p>
    </section>
  );
}
