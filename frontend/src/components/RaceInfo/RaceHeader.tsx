"use client";

interface RaceHeaderProps {
  isConnected: boolean;
}

export default function RaceHeader({ isConnected }: RaceHeaderProps) {
  return (
    <header className="flex items-center justify-between">
      {/* Logo / Title */}
      <div className="flex items-center gap-4">
        <div className="bg-[#e10600] text-white font-black text-2xl px-3 py-1 rounded">
          F1
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            తెలుగు కామెంటరీ
          </h1>
          <p className="text-gray-500 text-sm">
            Telugu Live Commentary
          </p>
        </div>
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-2 bg-[#1a1a2e] border border-[#38383f] px-4 py-2 rounded-full">
        <div
          className={`w-2.5 h-2.5 rounded-full ${
            isConnected
              ? "bg-green-500 animate-pulse"
              : "bg-red-500"
          }`}
        />
        <span className="text-sm text-gray-300">
          {isConnected ? "లైవ్" : "ఆఫ్‌లైన్"}
        </span>
      </div>
    </header>
  );
}
