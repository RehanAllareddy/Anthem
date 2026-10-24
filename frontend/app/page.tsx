import Link from "next/link";

const STEPS = [
  { title: "Check in", body: "A few gentle questions about you and how you're feeling." },
  { title: "Pick a beat", body: "Upbeat, chill, pop, rap, or rock: whatever fits your mood." },
  { title: "Hear your song", body: "Original lyrics written for you, sung or rapped over your beat." },
];

export default function Welcome() {
  return (
    <div className="pt-6 sm:pt-12">
      <p className="font-bold text-primary">Hi there 👋</p>
      <h1 className="mt-2 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
        A song that&apos;s
        <br />
        all about <span className="text-accent">you</span>.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
        When things feel heavy, stressful, or a little gray, Anthem writes you a personal, uplifting song with your name,
        the things you love, and the words you need to hear right now.
      </p>

      <ol className="mt-8 grid gap-3 sm:grid-cols-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="rounded-2xl border border-line bg-surface p-4">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-primary-soft font-bold text-primary">
              {i + 1}
            </span>
            <p className="mt-3 font-bold">{s.title}</p>
            <p className="mt-1 text-muted">{s.body}</p>
          </li>
        ))}
      </ol>

      <Link
        href="/check-in"
        className="mt-8 inline-flex rounded-full bg-primary px-8 py-4 text-lg font-bold text-primary-ink shadow-sm hover:brightness-110"
      >
        Let&apos;s begin
      </Link>

      <div className="mt-10 space-y-3 rounded-2xl bg-surface-2 p-5 text-muted">
        <p>
          <strong className="text-ink">A gentle note:</strong> Anthem is a wellbeing tool to lift your mood. It isn&apos;t a
          replacement for therapy, counseling, or medical care. If you&apos;re struggling, please reach out to someone you
          trust or use the support link at the top of every page.
        </p>
        <p>
          <strong className="text-ink">Your privacy:</strong> No account needed. We never save what you write about how
          you&apos;re feeling. Your song and its lyrics are private and deleted from our servers within 24 hours. Download it if you&apos;d like to keep or share it.
        </p>
      </div>
    </div>
  );
}
