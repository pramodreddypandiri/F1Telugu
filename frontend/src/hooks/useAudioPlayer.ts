"use client";

import { useRef, useState, useCallback } from "react";

export function useAudioPlayer() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const queueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);

  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolumeState] = useState(0.8);

  const initAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
      gainNodeRef.current = audioContextRef.current.createGain();
      gainNodeRef.current.gain.value = volume;
      gainNodeRef.current.connect(audioContextRef.current.destination);
    }
    if (audioContextRef.current.state === "suspended") {
      audioContextRef.current.resume();
    }
  }, [volume]);

  const playNext = useCallback(() => {
    if (!audioContextRef.current || !gainNodeRef.current) return;
    if (queueRef.current.length === 0) {
      isPlayingRef.current = false;
      setIsPlaying(false);
      return;
    }

    const buffer = queueRef.current.shift()!;
    const source = audioContextRef.current.createBufferSource();
    source.buffer = buffer;
    source.connect(gainNodeRef.current);
    source.onended = () => playNext();
    source.start(0);

    isPlayingRef.current = true;
    setIsPlaying(true);
  }, []);

  const handleAudioChunk = useCallback(
    async (base64Audio: string) => {
      initAudioContext();
      if (!audioContextRef.current) return;

      try {
        const binaryStr = atob(base64Audio);
        const bytes = new Uint8Array(binaryStr.length);
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i);
        }

        const audioBuffer = await audioContextRef.current.decodeAudioData(
          bytes.buffer
        );
        queueRef.current.push(audioBuffer);

        if (!isPlayingRef.current) {
          playNext();
        }
      } catch (err) {
        console.error("Error decoding audio:", err);
      }
    },
    [initAudioContext, playNext]
  );

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = v;
    }
  }, []);

  return {
    isPlaying,
    volume,
    setVolume,
    handleAudioChunk,
    initAudioContext,
  };
}
