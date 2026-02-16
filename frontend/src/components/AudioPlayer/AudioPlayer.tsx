"use client";

import { useEffect } from "react";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";

interface AudioPlayerProps {
  isConnected: boolean;
  setOnAudioChunk: (callback: (audio: string) => void) => void;
}

export default function AudioPlayer({
  isConnected,
  setOnAudioChunk,
}: AudioPlayerProps) {
  const { isPlaying, isEnabled, volume, setVolume, handleAudioChunk, enable } =
    useAudioPlayer();

  useEffect(() => {
    setOnAudioChunk(handleAudioChunk);
  }, [setOnAudioChunk, handleAudioChunk]);

  return (
    <div className="bg-[#1a1a2e] border border-[#38383f] rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className={`w-3 h-3 rounded-full ${
            isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
          }`}
        />
        <span className="text-sm font-medium">
          {isConnected ? "తెలుగు కామెంటరీ లైవ్" : "కనెక్ట్ అవుతోంది..."}
        </span>
      </div>

      {/* Audio Visualizer */}
      <div className="flex items-end justify-center gap-[3px] h-12 mb-4">
        {Array.from({ length: 24 }).map((_, i) => (
          <div
            key={i}
            className={`w-1.5 rounded-full transition-all duration-150 ${
              isPlaying ? "bg-[#e10600]" : "bg-[#38383f]"
            }`}
            style={{
              height: isPlaying
                ? `${20 + Math.random() * 80}%`
                : "20%",
              animationDelay: `${i * 0.05}s`,
            }}
          />
        ))}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={enable}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
            isEnabled
              ? "bg-green-600 hover:bg-green-700 text-white"
              : "bg-[#e10600] hover:bg-[#b80500] text-white"
          }`}
        >
          {isPlaying
            ? "🔊 ప్లే అవుతోంది"
            : isEnabled
              ? "✓ రెడీ"
              : "▶ ప్లే"}
        </button>

        {/* Volume */}
        <div className="flex items-center gap-2 flex-1">
          <svg
            className="w-4 h-4 text-gray-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M10 3.75a.75.75 0 00-1.264-.546L4.703 7H3.167a.75.75 0 00-.7.48A6.985 6.985 0 002 10c0 .887.165 1.737.468 2.52.111.29.39.48.7.48h1.535l4.033 3.796A.75.75 0 0010 16.25V3.75z" />
          </svg>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="flex-1 h-1.5 rounded-full appearance-none bg-[#38383f] accent-[#e10600]"
          />
        </div>
      </div>

      {/* Status hint */}
      {!isEnabled && isConnected && (
        <p className="text-xs text-gray-500 mt-3 text-center">
          ఆడియో వినడానికి &quot;ప్లే&quot; నొక్కండి
        </p>
      )}
    </div>
  );
}
