"use client";

import { useRef, useState, useCallback } from "react";

export function useAudioPlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const queueRef = useRef<string[]>([]); // base64 audio strings
  const isPlayingRef = useRef(false);

  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolumeState] = useState(0.8);
  const [isEnabled, setIsEnabled] = useState(false);

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsPlaying(false);
      return;
    }

    const base64Audio = queueRef.current.shift()!;
    const binaryStr = atob(base64Audio);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }

    const blob = new Blob([bytes], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);

    const audio = audioRef.current!;
    audio.src = url;
    audio.volume = volume;
    audio.play().catch((err) => {
      console.error("Audio play error:", err);
      isPlayingRef.current = false;
      setIsPlaying(false);
    });

    audio.onended = () => {
      URL.revokeObjectURL(url);
      playNext();
    };

    audio.onerror = () => {
      console.error("Audio decode error");
      URL.revokeObjectURL(url);
      playNext();
    };

    isPlayingRef.current = true;
    setIsPlaying(true);
  }, [volume]);

  const handleAudioChunk = useCallback(
    (base64Audio: string) => {
      if (!isEnabled) return;

      console.log(
        `[AudioPlayer] Received chunk (${Math.round(base64Audio.length / 1024)} KB)`
      );

      queueRef.current.push(base64Audio);

      if (!isPlayingRef.current) {
        playNext();
      }
    },
    [isEnabled, playNext]
  );

  const enable = useCallback(() => {
    // Create the audio element on user gesture
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.volume = volume;
    }
    setIsEnabled(true);
    console.log("[AudioPlayer] Enabled - ready to receive audio");
  }, [volume]);

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
    if (audioRef.current) {
      audioRef.current.volume = v;
    }
  }, []);

  return {
    isPlaying,
    isEnabled,
    volume,
    setVolume,
    handleAudioChunk,
    enable,
  };
}
