"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import CrisisModal from "@/components/CrisisModal";
import { api } from "@/lib/api";
import { AgeRange, CheckIn, FEELINGS, MESSAGES, loadCheckIn, saveCheckIn } from "@/lib/checkin";

const STEPS = ["name", "age", "hobbies", "feelings", "messages"] as const;
type Step = (typeof STEPS)[number];

const HOBBY_IDEAS = ["Music", "Drawing", "Gaming", "Soccer", "Reading", "Cooking", "Dancing", "Hiking", "Pets", "Coding"];

const chip = (on: boolean) =>
  `rounded-full border-2 px-4 py-2 font-semibold transition ${
    on ? "border-primary bg-primary text-primary-ink" : "border-line bg-surface text-ink hover:border-primary"
  }`;

export default function CheckInPage() {
  const router = useRouter();
  const [data, setData] = useState<CheckIn | null>(null);
  const [step, setStep] = useState(0);
  const [hobbyDraft, setHobbyDraft] = useState("");
  const [error, setError] = useState("");
  const [screening, setScreening] = useState(false);
  const [crisisOpen, setCrisisOpen] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => setData(loadCheckIn()), []);
  useEffect(() => {
    if (data) saveCheckIn(data);
  }, [data]);
  // Move focus to the new question so keyboard and screen reader users stay oriented.
  useEffect(() => {
    headingRef.current?.focus();
    setError("");
  }, [step]);

  if (!data) return null;
  const current: Step = STEPS[step];
  const update = (patch: Partial<CheckIn>) => setData((d) => (d ? { ...d, ...patch } : d));
  const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  const addHobby = (h: string) => {
    const v = h.trim().slice(0, 40);
    if (!v || data.hobbies.length >= 5 || data.hobbies.some((x) => x.toLowerCase() === v.toLowerCase())) return;
    update({ hobbies: [...data.hobbies, v] });
    setHobbyDraft("");
  };

  const validate = (): string => {
    if (current === "name" && !data.name.trim()) return "Add a name or nickname for your song.";
    if (current === "age" && !data.ageRange) return "Choose an age range.";
    if (current === "hobbies" && data.hobbies.length < 2) return "Add at least 2 things you love.";
    if (current === "feelings" && data.feelings.length === 0) return "Choose at least one.";
    return "";
  };

  const advance = () => {
    if (step < STEPS.length - 1) setStep(step + 1);
    else router.push("/beats");
  };

  const next = async (e?: FormEvent) => {
    e?.preventDefault();
    if (current === "hobbies" && hobbyDraft.trim()) {
      addHobby(hobbyDraft);
      return;
    }
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }
    if (current === "feelings") {
      const text = data.freeText.trim();
      if (!text) {
        update({ freeTextScreened: false });
        return advance();
      }
      setScreening(true);
      try {
        const result = await api.screen(text, data.ageRange || "25+");
        if (result.flagged) {
          // Don't build the song around what they shared; check in with them first.
          update({ freeTextScreened: false });
          setCrisisOpen(true);
          return;
        }
        update({ freeTextScreened: true });
      } catch {
        // If screening is unavailable, leave the free text out of the song entirely.
        update({ freeTextScreened: false });
      } finally {
        setScreening(false);
      }
    }
    advance();
  };

  const isTeen = data.ageRange === "13-17";

  return (
    <div className="pt-4">
      <div className="flex items-center gap-3">
        <div
          className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-label="Check-in progress"
          aria-valuemin={1}
          aria-valuemax={STEPS.length}
          aria-valuenow={step + 1}
        >
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
        </div>
        <span className="text-sm text-muted">
          {step + 1} of {STEPS.length}
        </span>
      </div>

      <form onSubmit={next} className="mt-8" noValidate>
        {current === "name" && (
          <Question headingRef={headingRef} title="What should we call you?" hint="It'll be in your song.">
            <label htmlFor="name" className="sr-only">
              Name or nickname
            </label>
            <input
              id="name"
              autoComplete="given-name"
              maxLength={30}
              value={data.name}
              onChange={(e) => update({ name: e.target.value })}
              className="w-full rounded-2xl border-2 border-line bg-surface px-5 py-4 text-xl outline-none focus:border-primary"
              placeholder="e.g. Maya"
            />
          </Question>
        )}

        {current === "age" && (
          <Question headingRef={headingRef} title="How old are you?" hint="Keeps the tone just right.">
            <div role="radiogroup" aria-label="Age range" className="flex flex-wrap gap-3">
              {(["13-17", "18-24", "25+"] as AgeRange[]).map((a) => (
                <button
                  key={a}
                  type="button"
                  role="radio"
                  aria-checked={data.ageRange === a}
                  onClick={() => update({ ageRange: a })}
                  className={`${chip(data.ageRange === a)} px-6 py-3 text-lg`}
                >
                  {a}
                </button>
              ))}
            </div>
          </Question>
        )}

        {current === "hobbies" && (
          <Question headingRef={headingRef} title="What do you love?" hint="Add 2 to 5 things.">
            <div className="flex gap-2">
              <label htmlFor="hobby" className="sr-only">
                Add a hobby
              </label>
              <input
                id="hobby"
                maxLength={40}
                value={hobbyDraft}
                disabled={data.hobbies.length >= 5}
                onChange={(e) => setHobbyDraft(e.target.value)}
                className="min-w-0 flex-1 rounded-2xl border-2 border-line bg-surface px-4 py-3 text-lg outline-none focus:border-primary disabled:opacity-60"
                placeholder={data.hobbies.length >= 5 ? "That's 5, perfect!" : "Type and press Enter"}
              />
              <button
                type="button"
                onClick={() => addHobby(hobbyDraft)}
                disabled={!hobbyDraft.trim() || data.hobbies.length >= 5}
                className="rounded-2xl bg-accent-soft px-5 font-bold text-accent disabled:opacity-50"
              >
                Add
              </button>
            </div>
            {data.hobbies.length > 0 && (
              <ul className="mt-4 flex flex-wrap gap-2" aria-label="Your hobbies">
                {data.hobbies.map((h) => (
                  <li key={h}>
                    <button
                      type="button"
                      onClick={() => update({ hobbies: data.hobbies.filter((x) => x !== h) })}
                      className="rounded-full bg-primary px-4 py-2 font-semibold text-primary-ink"
                      aria-label={`Remove ${h}`}
                    >
                      {h} <span aria-hidden>×</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Suggestions">
              {HOBBY_IDEAS.filter((i) => !data.hobbies.includes(i)).map((i) => (
                <button key={i} type="button" onClick={() => addHobby(i)} disabled={data.hobbies.length >= 5} className={`${chip(false)} text-sm disabled:opacity-50`}>
                  + {i}
                </button>
              ))}
            </div>
          </Question>
        )}

        {current === "feelings" && (
          <Question headingRef={headingRef} title="How are you feeling?" hint="Pick any that fit.">
            <div role="group" aria-label="Feelings" className="flex flex-wrap gap-2">
              {FEELINGS.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  aria-pressed={data.feelings.includes(f.id)}
                  onClick={() => update({ feelings: toggle(data.feelings, f.id) })}
                  className={chip(data.feelings.includes(f.id))}
                >
                  {f.label}
                </button>
              ))}
            </div>
            {data.feelings.includes("other") && (
              <div className="mt-4">
                <label htmlFor="other" className="font-semibold">
                  In a word or two, how are you feeling?
                </label>
                <input
                  id="other"
                  maxLength={60}
                  value={data.feelingsOther}
                  onChange={(e) => update({ feelingsOther: e.target.value })}
                  className="mt-2 w-full rounded-2xl border-2 border-line bg-surface px-4 py-3 outline-none focus:border-primary"
                />
              </div>
            )}
            <div className="mt-6">
              <label htmlFor="free" className="font-semibold">
                What&apos;s going on? <span className="font-normal text-muted">(optional)</span>
              </label>
              <p id="free-hint" className="mt-1 text-sm text-muted">
                Never saved.
              </p>
              <textarea
                id="free"
                aria-describedby="free-hint"
                rows={4}
                maxLength={1000}
                value={data.freeText}
                onChange={(e) => update({ freeText: e.target.value, freeTextScreened: false })}
                className="mt-2 w-full rounded-2xl border-2 border-line bg-surface px-4 py-3 outline-none focus:border-primary"
              />
            </div>
          </Question>
        )}

        {current === "messages" && (
          <Question headingRef={headingRef} title="What do you need to hear?" hint="Pick any, or write your own.">
            <div role="group" aria-label="Messages" className="flex flex-wrap gap-2">
              {MESSAGES.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  aria-pressed={data.messages.includes(m.id)}
                  onClick={() => update({ messages: toggle(data.messages, m.id) })}
                  className={chip(data.messages.includes(m.id))}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <label htmlFor="custom" className="mt-6 block font-semibold">
              Your own words <span className="font-normal text-muted">(optional)</span>
            </label>
            <input
              id="custom"
              maxLength={80}
              value={data.customMessage}
              onChange={(e) => update({ customMessage: e.target.value })}
              placeholder="e.g. Keep being kind to yourself"
              className="mt-2 w-full rounded-2xl border-2 border-line bg-surface px-4 py-3 outline-none focus:border-primary"
            />
          </Question>
        )}

        {error && (
          <p role="alert" className="mt-4 font-semibold text-danger">
            {error}
          </p>
        )}

        <div className="mt-10 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => (step === 0 ? router.push("/") : setStep(step - 1))}
            className="rounded-full px-5 py-3 font-bold text-muted hover:text-ink"
          >
            ← Back
          </button>
          <button
            type="submit"
            disabled={screening}
            className="rounded-full bg-primary px-8 py-3 text-lg font-bold text-primary-ink shadow-sm hover:brightness-110 disabled:opacity-70"
          >
            {screening ? "One moment…" : step === STEPS.length - 1 ? "Choose a beat →" : "Next →"}
          </button>
        </div>
      </form>

      <CrisisModal
        open={crisisOpen}
        isTeen={isTeen}
        onContinue={() => {
          setCrisisOpen(false);
          advance();
        }}
      />
    </div>
  );
}

function Question({
  title,
  hint,
  headingRef,
  children,
}: {
  title: string;
  hint: string;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
  children: React.ReactNode;
}) {
  return (
    <fieldset>
      <legend className="contents">
        <h1 ref={headingRef} tabIndex={-1} className="text-3xl font-extrabold leading-tight tracking-tight outline-none sm:text-4xl">
          {title}
        </h1>
      </legend>
      <p className="mt-2 text-muted">{hint}</p>
      <div className="mt-6">{children}</div>
    </fieldset>
  );
}
