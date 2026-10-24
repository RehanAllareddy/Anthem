"use client";

import { useEffect, useRef, useState } from "react";
import { Beat, absolute } from "@/lib/api";

const PREVIEW_SECONDS = 10;

export function usePreviewPlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);

  useEffect(() => () => audioRef.current?.pause(), []);

  const toggle = (beat: Beat) => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.addEventListener("ended", () => setPlayingId(null));
      audioRef.current.addEventListener("timeupdate", () => {
        if (audioRef.current && audioRef.current.currentTime >= PREVIEW_SECONDS) {
          audioRef.current.pause();
          setPlayingId(null);
        }
      });
    }
    const a = audioRef.current;
    if (playingId === beat.id) {
      a.pause();
      setPlayingId(null);
      return;
    }
    a.src = absolute(beat.preview_url);
    a.currentTime = 0;
    a.play().then(() => setPlayingId(beat.id)).catch(() => setPlayingId(null));
  };

  const stop = () => {
    audioRef.current?.pause();
    setPlayingId(null);
  };

  return { playingId, toggle, stop };
}
