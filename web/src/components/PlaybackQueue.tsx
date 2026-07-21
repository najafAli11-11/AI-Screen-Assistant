import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AudioData } from '../hooks/useWebSocket';

interface PlaybackQueueResult {
  enqueue: (audio: AudioData) => void;
  isPlaying: boolean;
  queuedCount: number;
  currentIndex: number | null;
  clear: () => void;
}

// If the next expected sentence has not arrived after this long (e.g. its TTS
// failed on the backend and only an error was emitted), skip ahead to the
// lowest queued sentence so playback never deadlocks on a missing index.
const GAP_TIMEOUT_MS = 3000;

export function usePlaybackQueue(): PlaybackQueueResult {
  const [queue, setQueue] = useState<AudioData[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);
  const activeAudio = useRef<HTMLAudioElement | null>(null);
  // Next sentence index we are allowed to play. Enforces strict in-order
  // playback regardless of network arrival order (spec 5.5).
  const nextIndexRef = useRef(0);
  const gapTimer = useRef<number | null>(null);

  const clearGapTimer = useCallback(() => {
    if (gapTimer.current !== null) {
      window.clearTimeout(gapTimer.current);
      gapTimer.current = null;
    }
  }, []);

  useEffect(() => {
    if (isPlaying || queue.length === 0) return;

    const sorted = [...queue].sort((a, b) => a.index - b.index);
    const next = sorted.find(item => item.index === nextIndexRef.current);

    if (!next) {
      // The expected sentence is not here yet. Wait briefly for it, then skip
      // forward to the earliest available sentence to avoid stalling forever.
      clearGapTimer();
      gapTimer.current = window.setTimeout(() => {
        gapTimer.current = null;
        nextIndexRef.current = sorted[0].index;
        // Nudge the effect to re-run.
        setQueue(previous => [...previous]);
      }, GAP_TIMEOUT_MS);
      return;
    }

    clearGapTimer();
    setIsPlaying(true);
    setCurrentIndex(next.index);

    const audio = new Audio(`data:audio/${next.format};base64,${next.audio}`);
    activeAudio.current = audio;
    const finish = () => {
      nextIndexRef.current = next.index + 1;
      setQueue(previous => previous.filter(item => item.index !== next.index));
      setCurrentIndex(null);
      setIsPlaying(false);
      activeAudio.current = null;
    };
    audio.onended = finish;
    audio.onerror = finish;
    audio.play().catch(finish);
  }, [clearGapTimer, isPlaying, queue]);

  const enqueue = useCallback((audio: AudioData) => {
    setQueue(previous => (previous.some(item => item.index === audio.index) ? previous : [...previous, audio]));
  }, []);

  const clear = useCallback(() => {
    clearGapTimer();
    activeAudio.current?.pause();
    activeAudio.current = null;
    nextIndexRef.current = 0;
    setQueue([]);
    setIsPlaying(false);
    setCurrentIndex(null);
  }, [clearGapTimer]);

  return useMemo(() => ({
    enqueue,
    isPlaying,
    queuedCount: queue.length,
    currentIndex,
    clear,
  }), [clear, currentIndex, enqueue, isPlaying, queue.length]);
}
