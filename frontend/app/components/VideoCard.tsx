"use client";

import { useState } from "react";
import { VideoMetadata } from "../types";
import {
  Eye,
  ThumbsUp,
  MessageCircle,
  TrendingUp,
  Share2,
  Play,
} from "lucide-react";

interface VideoCardProps {
  video: VideoMetadata;
  side: "left" | "right";
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function VideoCard({ video, side }: VideoCardProps) {
  const [imageError, setImageError] = useState(false);

  const getEmbedUrl = () => {
    if (!video.url) return null;
    if (video.platform === "youtube") {
      const match = video.url.match(
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/
      );
      const videoId = match?.[1];
      return videoId ? `https://www.youtube.com/embed/${videoId}` : null;
    }
    if (video.platform === "instagram") {
      const match = video.url.match(/\/reel\/([\w-]+)/);
      const reelId = match?.[1];
      return reelId ? `https://www.instagram.com/p/${reelId}/embed` : null;
    }
    return null;
  };

  const embedUrl = getEmbedUrl();

  const isYoutube = video.platform === "youtube";

  // Metric configs
  const metrics = isYoutube
    ? [
        { label: "VIEWS", value: formatCount(video.views), icon: Eye },
        { label: "LIKES", value: formatCount(video.likes), icon: ThumbsUp },
        {
          label: "COMMENTS",
          value: formatCount(video.comments),
          icon: MessageCircle,
        },
        {
          label: "ENGAGEMENT",
          value: `${video.engagement_rate.toFixed(1)}%`,
          icon: TrendingUp,
          highlight: true,
        },
      ]
    : [
        { label: "PLAYS", value: formatCount(video.views), icon: Play },
        { label: "LIKES", value: formatCount(video.likes), icon: ThumbsUp },
        { label: "SHARES", value: formatCount(video.comments), icon: Share2 },
        {
          label: "ENGAGEMENT",
          value: `${video.engagement_rate.toFixed(1)}%`,
          icon: TrendingUp,
          highlight: true,
        },
      ];

  return (
    <div className="bg-white rounded-2xl border border-surface-200 shadow-card overflow-hidden card-lift">
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isYoutube ? (
            <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M10 8.5L16 12L10 15.5V8.5Z" fill="#EF4444" />
              </svg>
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <rect
                  x="4"
                  y="4"
                  width="16"
                  height="16"
                  rx="4"
                  stroke="#F97316"
                  strokeWidth="1.5"
                  fill="none"
                />
                <circle
                  cx="12"
                  cy="12"
                  r="3.5"
                  stroke="#F97316"
                  strokeWidth="1.5"
                  fill="none"
                />
                <circle cx="17" cy="7" r="1.2" fill="#F97316" />
              </svg>
            </div>
          )}
          <span className="font-display font-bold text-surface-900">
            {isYoutube ? "YouTube Insight" : "Instagram Reel"}
          </span>
        </div>
        <span className="text-[11px] text-surface-400 font-mono bg-surface-100 px-2 py-0.5 rounded">
          {video.video_id}
        </span>
      </div>

      {/* Video Embed / Thumbnail */}
      {embedUrl ? (
        <div className="relative aspect-video bg-surface-900">
          <iframe
            src={embedUrl}
            className="w-full h-full"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
          {/* Duration overlay */}
          {video.duration_seconds > 0 && (
            <div className="absolute bottom-2 right-2 bg-black/70 text-white text-[11px] font-mono px-2 py-0.5 rounded">
              {formatDuration(video.duration_seconds)}
            </div>
          )}
        </div>
      ) : video.thumbnail && !imageError ? (
        <div className="relative aspect-video bg-surface-100">
          <img
            src={video.thumbnail}
            alt={video.title || "Video thumbnail"}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
          <div className="video-overlay absolute inset-0" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-14 h-14 rounded-full bg-black/40 backdrop-blur-sm flex items-center justify-center">
              <Play className="w-6 h-6 text-white ml-0.5" />
            </div>
          </div>
          {video.duration_seconds > 0 && (
            <div className="absolute bottom-2 right-2 bg-black/70 text-white text-[11px] font-mono px-2 py-0.5 rounded">
              {formatDuration(video.duration_seconds)}
            </div>
          )}
        </div>
      ) : (
        <div className="aspect-video bg-gradient-to-br from-surface-100 to-surface-200 flex items-center justify-center">
          <Play className="w-12 h-12 text-surface-300" />
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-4 divide-x divide-surface-200 border-t border-surface-200">
        {metrics.map((m) => (
          <div key={m.label} className="py-3 px-2 text-center">
            <p className="text-[10px] text-surface-400 uppercase tracking-wider mb-0.5">
              {m.label}
            </p>
            <p
              className={`text-base font-bold ${
                m.highlight ? "text-accent-500" : "text-surface-900"
              }`}
            >
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* Creator Info */}
      <div className="px-5 py-3 border-t border-surface-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-surface-200 to-surface-300 flex items-center justify-center text-surface-500 text-xs font-semibold">
            {video.creator?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <p className="text-sm font-semibold text-surface-900">
              @{video.creator}
            </p>
            <p className="text-[11px] text-surface-400">
              {video.follower_count
                ? formatCount(video.follower_count) +
                  (isYoutube ? " Subscribers" : " Followers")
                : ""}
            </p>
          </div>
        </div>

        {/* Hashtags */}
        {video.hashtags && video.hashtags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap justify-end">
            {video.hashtags.slice(0, 3).map((tag) => (
              <span key={tag} className="tag-pill">
                {tag.startsWith("#") ? tag : `#${tag}`}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}