import Link from "next/link";

export default function SupportLink() {
  return (
    <Link
      href="/support"
      className="rounded-full border border-line bg-surface px-4 py-2 text-sm font-semibold text-accent shadow-sm hover:bg-accent-soft"
    >
      Need to talk to someone?
    </Link>
  );
}
