import Link from "next/link";

export default function SupportLink() {
  return (
    <Link
      href="/support"
      className="flex items-center gap-1.5 rounded-full bg-surface/70 px-3.5 py-2 text-sm font-semibold text-accent shadow-sm ring-1 ring-line backdrop-blur hover:bg-accent-soft"
    >
      <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" aria-hidden fill="currentColor">
        <path d="M12 21s-7.5-4.6-9.6-9.2C1 8.6 3 5 6.5 5c2 0 3.6 1.1 4.5 2.6h2C13.9 6.1 15.5 5 17.5 5 21 5 23 8.6 21.6 11.8 19.5 16.4 12 21 12 21Z" />
      </svg>
      <span className="sm:hidden">Need to talk?</span>
      <span className="hidden sm:inline">Need to talk to someone?</span>
    </Link>
  );
}
