import { CRISIS_RESOURCES } from "@/lib/resources";

export default function ResourceList() {
  return (
    <ul className="space-y-3">
      {CRISIS_RESOURCES.map((r) => (
        <li key={r.name} className="rounded-2xl border border-line bg-surface p-4">
          <p className="font-bold">{r.name}</p>
          <p className="mt-1 text-muted">{r.detail}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {r.actions.map((a) => (
              <a
                key={a.href}
                href={a.href}
                className="rounded-full bg-accent px-4 py-2 text-sm font-bold text-white dark:text-[#1c1733]"
              >
                {a.label}
              </a>
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
