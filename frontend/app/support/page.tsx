import Link from "next/link";
import ResourceList from "@/components/ResourceList";

export const metadata = { title: "Support · Anthem" };

export default function SupportPage() {
  return (
    <div className="pt-4">
      <h1 className="text-3xl font-extrabold">You don&apos;t have to go through it alone</h1>
      <p className="mt-3 text-lg leading-relaxed text-muted">
        If you&apos;re struggling, thinking about hurting yourself, or don&apos;t feel safe, please reach out. These services
        are free, confidential, and available 24/7 in the US.
      </p>
      <div className="mt-6">
        <ResourceList />
      </div>
      <div className="mt-6 space-y-3 rounded-2xl bg-surface-2 p-5 text-muted">
        <p>
          <strong className="text-ink">In immediate danger?</strong> Call 911 or go to your nearest emergency room.
        </p>
        <p>
          <strong className="text-ink">Under 18?</strong> A parent, school counselor, teacher, coach, or another adult you
          trust can help you find support.
        </p>
        <p>
          <strong className="text-ink">Outside the US?</strong>{" "}
          <a className="font-semibold text-accent underline" href="https://findahelpline.com" target="_blank" rel="noreferrer">
            findahelpline.com
          </a>{" "}
          lists free helplines in many countries.
        </p>
      </div>
      <Link href="/" className="mt-8 inline-flex rounded-full px-5 py-3 font-bold text-muted hover:text-ink">
        ← Back to Anthem
      </Link>
    </div>
  );
}
