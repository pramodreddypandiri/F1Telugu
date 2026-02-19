"use client";

import { useEffect, useRef } from "react";
import { CommentaryText } from "@/hooks/useWebSocket";

interface CommentaryFeedProps {
  feed: CommentaryText[];
}

export default function CommentaryFeed({ feed }: CommentaryFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest entry
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed]);

  return (
    <div className="bg-[#1a1a2e] border border-[#38383f] rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold">కామెంటరీ</h3>
        <span className="text-xs text-gray-500">Telugu · English</span>
      </div>

      {/* Feed */}
      <div className="space-y-3 max-h-80 overflow-y-auto pr-1 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-[#38383f]">
        {feed.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-6">
            కామెంటరీ కోసం వేచి ఉంది...
          </p>
        ) : (
          feed.map((entry, i) => (
            <CommentaryEntry
              key={i}
              entry={entry}
              isLatest={i === feed.length - 1}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function CommentaryEntry({
  entry,
  isLatest,
}: {
  entry: CommentaryText;
  isLatest: boolean;
}) {
  return (
    <div
      className={`rounded-lg p-3 border transition-colors ${
        isLatest
          ? "border-[#e10600] bg-[#e10600]/10"
          : "border-[#38383f] bg-[#12122a]"
      }`}
    >
      {/* Telugu — primary, larger */}
      <p
        className={`font-semibold leading-snug mb-1 ${
          isLatest ? "text-white" : "text-gray-200"
        }`}
        lang="te"
      >
        {entry.telugu}
      </p>

      {/* English — secondary, muted */}
      <p className="text-xs text-gray-500 leading-snug">{entry.english}</p>
    </div>
  );
}
