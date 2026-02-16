"use client";

import { useWebSocket } from "@/hooks/useWebSocket";
import RaceHeader from "@/components/RaceInfo/RaceHeader";
import AudioPlayer from "@/components/AudioPlayer/AudioPlayer";
import Leaderboard from "@/components/Leaderboard/Leaderboard";
import RaceInfo from "@/components/RaceInfo/RaceInfo";

export default function Home() {
  const { isConnected, leaderboard, setOnAudioChunk } = useWebSocket();

  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* Header */}
      <RaceHeader isConnected={isConnected} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Left - Leaderboard (2/3 width) */}
        <div className="lg:col-span-2">
          <Leaderboard data={leaderboard} />
        </div>

        {/* Right - Sidebar (1/3 width) */}
        <div className="space-y-6">
          <AudioPlayer
            isConnected={isConnected}
            setOnAudioChunk={setOnAudioChunk}
          />
          <RaceInfo />
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-12 text-center text-gray-600 text-xs">
        F1 తెలుగు కామెంటరీ &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
