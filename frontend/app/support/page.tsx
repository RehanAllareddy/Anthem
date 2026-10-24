import Link from "next/link";
import ResourceList from "@/components/ResourceList";

export const metadata = { title: "Support · Echorie" };

const MORE = [
  { label: "In immediate danger?", body: "Call 911." },
  { label: "Under 18?", body: "A parent, school counselor, or adult you trust can help." },
];

export default function SupportPage() {
  return (
    <div className="pt-6">
      <h1 className="text-4xl font-extrabold tracking-tight">You&apos;re not alone.</h1>
      <p className="mt-3 text-lg text-muted">Free, confidential, 24/7 in the US.</p>
      <div className="mt-8">
        <ResourceList />
      </div>
      <ul className="mt-8 space-y-2 text-muted">
        {MORE.map((m) => (
          <li key={m.label}>
            <strong className="text-ink">{m.label}</strong> {m.body}
          </li>
        ))}
        <li>
          <strong className="text-ink">Outside the US?</strong>{" "}
          <a className="font-semibold text-accent underline" href="https://findahelpline.com" target="_blank" rel="noreferrer">
            findahelpline.com
          </a>
        </li>
      </ul>
      <Link href="/" className="mt-10 inline-flex font-bold text-muted hover:text-ink">
        ← Back
      </Link>
    </div>
  );
}
