"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import LyricsKaraoke from "@/components/LyricsKaraoke";
import { Beat, CATEGORY_LABELS, Song, absolute, api } from "@/lib/api";
import { clearCheckIn } from "@/lib/checkin";
import { usePreviewPlayer } from "@/lib/usePreviewPlayer";

export default function SongPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const audioRef = useRef<HTMLAudioElement>(null);
  const [song, setSong] = useState<Song | null>(null);
  const [error, setError] = useState("");
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showBeats, setShowBeats] = useState(false);
  const [beats, setBeats] = useState<Beat[]>([]);
  const [remixing, setRemixing] = useState(false);
  const preview = usePreviewPlayer();

  useEffect(() => {
    api
      .song(id)
      .then((s) => (s.status === "done" ? setSong(s) : router.replace(`/generating?job=${id}`)))
      .catch((e) => setError((e as Error).message));
  }, [id, router]);

  // Smooth time updates for karaoke while playing (timeupdate only fires ~4x/sec).
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const tick = () => {
      if (audioRef.current) setTime(audioRef.current.currentTime);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  const openBeats = async () => {
    setShowBeats((v) => !v);
    if (!beats.length) {
      try {
        setBeats((await api.beats()).beats);
      } catch {
        setError("We couldn't load the beats.");
      }
    }
  };

  const remix = async (beatId: string) => {
    setRemixing(true);
    preview.stop();
    audioRef.current?.pause();
    try {
      const { job_id } = await api.remix(id, beatId);
      router.push(`/generating?job=${job_id}`);
    } catch (e) {
      setError((e as Error).message);
      setRemixing(false);
    }
  };

  if (error && !song) {
    return (
      <div className="pt-10 text-center">
        <h1 className="text-3xl font-extrabold">This song isn&apos;t available</h1>
        <p role="alert" className="mt-3 text-lg text-muted">
          {error}
        </p>
        <p className="mt-2 text-muted">Songs are deleted from our server after 24 hours to protect your privacy.</p>
        <Link href="/check-in" className="mt-8 inline-flex rounded-full bg-primary px-8 py-3 font-bold text-primary-ink">
          Make a new song
        </Link>
      </div>
    );
  }
  if (!song) return <p className="pt-10 text-center text-muted">Loading your song…</p>;

  const src = absolute(song.audio_url!);
  const format = (song.audio_format ?? "mp3").toUpperCase();

  return (
    <div className="pt-4">
      <p className="font-bold text-primary">Your song is ready 🎉</p>
      <h1 className="mt-1 text-4xl font-extrabold leading-tight">{song.title}</h1>

      <div className="sticky top-2 z-10 mt-6 rounded-3xl border border-line bg-surface p-4 shadow-sm">
        <audio
          ref={audioRef}
          src={src}
          controls
          preload="auto"
          className="w-full"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
          onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
          onSeeked={(e) => setTime(e.currentTarget.currentTime)}
        >
          Your browser doesn&apos;t support audio playback.
        </audio>
        <div className="mt-3 flex flex-wrap gap-2">
          <a href={`${src}?download=1`} download className="rounded-full bg-primary px-5 py-2.5 font-bold text-primary-ink">
            Download {format}
          </a>
          <button
            type="button"
            onClick={openBeats}
            aria-expanded={showBeats}
            aria-controls="remix-beats"
            className="rounded-full border-2 border-line px-5 py-2 font-bold text-ink hover:border-primary"
          >
            Try a different beat
          </button>
          <button
            type="button"
            onClick={() => {
              clearCheckIn();
              router.push("/");
            }}
            className="rounded-full px-5 py-2 font-bold text-muted hover:text-ink"
          >
            Start over
          </button>
        </div>
      </div>

      {showBeats && (
        <section id="remix-beats" className="mt-6 rounded-3xl bg-surface-2 p-4" aria-label="Choose a new beat">
          <p className="font-semibold">Same lyrics and voice, new beat. Preview one, then choose it.</p>
          {error && (
            <p role="alert" className="mt-2 font-semibold text-danger">
              {error}
            </p>
          )}
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {beats
              .filter((b) => b.id !== song.beat_id)
              .map((b) => (
                <li key={b.id} className="flex items-center gap-2 rounded-2xl bg-surface p-2">
                  <button
                    type="button"
                    onClick={() => preview.toggle(b)}
                    aria-label={`${preview.playingId === b.id ? "Stop" : "Play"} preview of ${b.name}`}
                    className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-accent-soft text-accent"
                  >
                    {preview.playingId === b.id ? "■" : "▶"}
                  </button>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-bold">{b.name}</span>
                    <span className="text-sm text-muted">
                      {CATEGORY_LABELS[b.category]} · {b.bpm} BPM
                    </span>
                  </span>
                  <button
                    type="button"
                    disabled={remixing}
                    onClick={() => remix(b.id)}
                    className="rounded-full bg-primary px-4 py-2 text-sm font-bold text-primary-ink disabled:opacity-60"
                  >
                    Use
                  </button>
                </li>
              ))}
          </ul>
        </section>
      )}

      <section className="mt-8" aria-label="Lyrics">
        <h2 className="sr-only">Lyrics</h2>
        <LyricsKaraoke
          song={song}
          time={time}
          playing={playing}
          onSeek={(t) => {
            if (!audioRef.current) return;
            audioRef.current.currentTime = t;
            audioRef.current.play().catch(() => {});
          }}
        />
      </section>

      <p className="mt-10 rounded-2xl bg-surface-2 p-4 text-muted">
        🔒 This song is private: only people with this link can hear it, and it&apos;s deleted from our server within 24
        hours. Download it to keep it. It&apos;s yours to share if you want to.
      </p>
    </div>
  );
}
