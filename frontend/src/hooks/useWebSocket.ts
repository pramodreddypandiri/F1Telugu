"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { io, Socket } from "socket.io-client";
import { WS_URL } from "@/utils/constants";

interface LeaderboardData {
  current_lap: number;
  total_laps: number;
  positions: DriverPosition[];
}

interface DriverPosition {
  position: number;
  driver_name: string;
  team: string;
  gap: string;
  last_lap_time: string;
}

interface AudioChunk {
  audio: string; // base64
}

interface RaceEvent {
  type: string;
  data: Record<string, unknown>;
}

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  const [leaderboard, setLeaderboard] = useState<LeaderboardData | null>(null);
  const [audioChunks, setAudioChunks] = useState<string[]>([]);
  const [raceEvents, setRaceEvents] = useState<RaceEvent[]>([]);

  const onAudioChunkRef = useRef<((audio: string) => void) | null>(null);

  useEffect(() => {
    const socket = io(WS_URL, {
      transports: ["websocket"],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });

    socket.on("connect", () => {
      console.log("Connected to server");
      setIsConnected(true);
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
      setIsConnected(false);
    });

    socket.on("leaderboard_update", (data: LeaderboardData) => {
      setLeaderboard(data);
    });

    socket.on("audio_chunk", (data: AudioChunk) => {
      setAudioChunks((prev) => [...prev, data.audio]);
      onAudioChunkRef.current?.(data.audio);
    });

    socket.on("race_event", (data: RaceEvent) => {
      setRaceEvents((prev) => [...prev.slice(-49), data]);
    });

    socketRef.current = socket;

    return () => {
      socket.close();
    };
  }, []);

  const setOnAudioChunk = useCallback(
    (callback: (audio: string) => void) => {
      onAudioChunkRef.current = callback;
    },
    []
  );

  return {
    socket: socketRef.current,
    isConnected,
    leaderboard,
    audioChunks,
    raceEvents,
    setOnAudioChunk,
  };
}

export type { LeaderboardData, DriverPosition, RaceEvent };
