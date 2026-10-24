// Same-origin: app/api/[...path]/route.ts proxies these calls to the backend.
export const API_URL = "/api";

export type Category = "upbeat" | "chill" | "pop" | "rap" | "rock";

export const CATEGORY_LABELS: Record<Category, string> = {
  upbeat: "Upbeat",
  chill: "Chill / Down",
  pop: "Pop",
  rap: "Rap / Hip-Hop",
  rock: "Rock",
};

export type Beat = {
  id: string;
  name: string;
  category: Category;
  bpm: number;
  key: string;
  mood: string;
  license: string;
  source_url: string;
  preview_url: string;
};

export type Voice = { id: string; label: string; description: string };

export type TimelineLine = { section: number; line: number; text: string; start: number; end: number };

export type Song = {
  id: string;
  status: "queued" | "writing" | "singing" | "mixing" | "done" | "error";
  stage: string;
  progress: number;
  error: string | null;
  beat_id: string;
  voice_id: string;
  title?: string;
  sections?: { type: "verse" | "chorus"; lines: string[] }[];
  timeline?: TimelineLine[];
  duration?: number;
  audio_url?: string;
  audio_format?: string;
  expires_at?: number;
};

export type ScreenResult = { flagged: boolean; category: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {}
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  beats: () => request<{ categories: Category[]; beats: Beat[] }>("/beats"),
  voices: () => request<{ provider: string; voices: Voice[] }>("/voices"),
  screen: (text: string, age_range: string) =>
    request<ScreenResult>("/screen", { method: "POST", body: JSON.stringify({ text, age_range }) }),
  createSong: (body: unknown) =>
    request<{ job_id: string }>("/songs", { method: "POST", body: JSON.stringify(body) }),
  song: (id: string) => request<Song>(`/songs/${id}`),
  remix: (id: string, beat_id: string) =>
    request<{ job_id: string }>(`/songs/${id}/remix`, { method: "POST", body: JSON.stringify({ beat_id }) }),
};

export const absolute = (path: string) => `${API_URL}${path}`;
