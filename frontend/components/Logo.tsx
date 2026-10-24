// Echorie mark: a source dot with two widening echo arcs.
export function LogoMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden fill="none">
      <circle cx="9" cy="16" r="3.5" fill="var(--primary)" />
      <path d="M15 9.5a9 9 0 0 1 0 13" stroke="var(--primary)" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M20.5 5a15 15 0 0 1 0 22" stroke="var(--accent)" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

export default function Logo() {
  return (
    <span className="flex items-center gap-2">
      <LogoMark />
      <span className="text-xl font-extrabold tracking-tight">echorie</span>
    </span>
  );
}
