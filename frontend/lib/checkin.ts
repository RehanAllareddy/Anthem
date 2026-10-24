"use client";

// Answers live only in this browser tab (sessionStorage) and are cleared when
// the tab closes or the user starts over. Nothing is sent anywhere until they
// create their song.

export type AgeRange = "13-17" | "18-24" | "25+";

export type CheckIn = {
  name: string;
  ageRange: AgeRange | "";
  hobbies: string[];
  feelings: string[];
  feelingsOther: string;
  freeText: string;
  freeTextScreened: boolean; // false => don't send freeText with the song request
  messages: string[];
  customMessage: string;
  beatId: string;
  voiceId: string;
};

export const EMPTY_CHECKIN: CheckIn = {
  name: "",
  ageRange: "",
  hobbies: [],
  feelings: [],
  feelingsOther: "",
  freeText: "",
  freeTextScreened: false,
  messages: [],
  customMessage: "",
  beatId: "",
  voiceId: "warm",
};

const KEY = "anthem.checkin";

export function loadCheckIn(): CheckIn {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? { ...EMPTY_CHECKIN, ...JSON.parse(raw) } : { ...EMPTY_CHECKIN };
  } catch {
    return { ...EMPTY_CHECKIN };
  }
}

export function saveCheckIn(c: CheckIn) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(c));
  } catch {}
}

export function clearCheckIn() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {}
}

export function isComplete(c: CheckIn) {
  return Boolean(c.name.trim() && c.ageRange && c.hobbies.length >= 2 && c.feelings.length >= 1);
}

export function toSongRequest(c: CheckIn) {
  return {
    name: c.name.trim(),
    age_range: c.ageRange,
    hobbies: c.hobbies,
    feelings: c.feelings,
    feelings_other: c.feelings.includes("other") && c.feelingsOther.trim() ? c.feelingsOther.trim() : null,
    free_text: c.freeTextScreened && c.freeText.trim() ? c.freeText.trim() : null,
    messages: c.messages,
    custom_message: c.customMessage.trim() || null,
    beat_id: c.beatId,
    voice_id: c.voiceId,
  };
}

export const FEELINGS = [
  { id: "anxious", label: "Anxious" },
  { id: "stressed", label: "Stressed" },
  { id: "sad", label: "Sad / down" },
  { id: "overwhelmed", label: "Overwhelmed" },
  { id: "lonely", label: "Lonely" },
  { id: "unmotivated", label: "Unmotivated" },
  { id: "other", label: "Something else" },
];

export const MESSAGES = [
  { id: "got_this", label: "You've got this" },
  { id: "okay_to_rest", label: "It's okay to rest" },
  { id: "not_alone", label: "You're not alone" },
  { id: "amazing", label: "You're amazing" },
  { id: "proud", label: "I'm proud of you" },
  { id: "one_step", label: "One step at a time" },
];
