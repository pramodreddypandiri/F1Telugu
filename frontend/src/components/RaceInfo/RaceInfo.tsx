"use client";

export default function RaceInfo() {
  return (
    <div className="bg-[#1a1a2e] border border-[#38383f] rounded-xl p-5">
      <h3 className="text-lg font-bold mb-3">రేసు సమాచారం</h3>
      <div className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-400">ట్రాక్</span>
          <span className="font-semibold">—</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">సర్క్యూట్ పొడవు</span>
          <span className="font-semibold">—</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">మొత్తం ల్యాప్స్</span>
          <span className="font-semibold">—</span>
        </div>
      </div>
    </div>
  );
}
