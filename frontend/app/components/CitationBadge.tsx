"use client";

import { Citation } from "../types";
import { Clock } from "lucide-react";

interface CitationBadgeProps {
  citation: Citation;
  onClick?: () => void;
}

export default function CitationBadge({ citation, onClick }: CitationBadgeProps) {
  const isYoutube = citation.video_id === "A";

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2.5 py-1 bg-surface-100 hover:bg-surface-200 border border-surface-200 rounded-full text-xs text-surface-600 transition-colors"
    >
      <Clock className="w-3 h-3 text-surface-400" />
      <span className="font-mono">
        {isYoutube ? "yt" : "ig"}:{citation.timestamp}
      </span>
    </button>
  );
}