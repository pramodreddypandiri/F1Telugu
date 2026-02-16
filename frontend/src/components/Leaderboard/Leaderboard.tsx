"use client";

import type { LeaderboardData, DriverPosition } from "@/hooks/useWebSocket";
import { TEAM_COLORS, POSITION_COLORS } from "@/utils/constants";

interface LeaderboardProps {
  data: LeaderboardData | null;
}

function DriverRow({ driver }: { driver: DriverPosition }) {
  const teamColor = TEAM_COLORS[driver.team] || "#6B7280";
  const posColor = POSITION_COLORS[driver.position];

  return (
    <div className="grid grid-cols-[3rem_1fr_8rem_5rem_6rem] gap-3 items-center bg-[#15151e] hover:bg-[#1e1e30] p-3 rounded-lg transition-colors">
      {/* Position */}
      <div className="flex justify-center">
        <span
          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
          style={{
            backgroundColor: posColor || "#38383f",
            color: posColor ? "#000" : "#fff",
          }}
        >
          {driver.position}
        </span>
      </div>

      {/* Driver Name with team color bar */}
      <div className="flex items-center gap-2">
        <div
          className="w-1 h-8 rounded-full"
          style={{ backgroundColor: teamColor }}
        />
        <div>
          <div className="text-white font-semibold text-sm">
            {driver.driver_name}
          </div>
          <div className="text-gray-500 text-xs">{driver.team}</div>
        </div>
      </div>

      {/* Gap */}
      <div className="text-right">
        <span
          className={`text-sm font-mono ${
            driver.position === 1 ? "text-[#e10600] font-bold" : "text-gray-400"
          }`}
        >
          {driver.position === 1 ? "లీడర్" : driver.gap || "-"}
        </span>
      </div>

      {/* Last Lap */}
      <div className="text-right text-gray-500 text-xs font-mono">
        {driver.last_lap_time || "-"}
      </div>

      {/* Status indicator */}
      <div className="text-right">
        <span className="text-xs text-gray-600">—</span>
      </div>
    </div>
  );
}

export default function Leaderboard({ data }: LeaderboardProps) {
  const positions = data?.positions || [];
  const currentLap = data?.current_lap || 0;
  const totalLaps = data?.total_laps || 0;

  return (
    <div className="bg-[#1a1a2e] border border-[#38383f] rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">లీడర్‌బోర్డ్</h2>
        {totalLaps > 0 && (
          <div className="bg-[#15151e] px-3 py-1 rounded-full">
            <span className="text-[#e10600] font-bold text-sm">
              ల్యాప్ {currentLap}
            </span>
            <span className="text-gray-500 text-sm"> / {totalLaps}</span>
          </div>
        )}
      </div>

      {/* Column Headers */}
      <div className="grid grid-cols-[3rem_1fr_8rem_5rem_6rem] gap-3 text-gray-500 text-xs uppercase tracking-wider mb-2 px-3">
        <div className="text-center">POS</div>
        <div>డ్రైవర్</div>
        <div className="text-right">గ్యాప్</div>
        <div className="text-right">ల్యాప్</div>
        <div className="text-right">స్థితి</div>
      </div>

      {/* Driver Rows */}
      <div className="space-y-1">
        {positions.length > 0 ? (
          positions.map((driver) => (
            <DriverRow key={driver.driver_name} driver={driver} />
          ))
        ) : (
          <div className="text-center text-gray-500 py-12">
            <p className="text-lg mb-2">రేసు డేటా కోసం వేచి ఉంది...</p>
            <p className="text-sm">Waiting for race data</p>
          </div>
        )}
      </div>
    </div>
  );
}
