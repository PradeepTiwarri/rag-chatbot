"use client";

import { useState } from "react";
import { VideoMetadata } from "../types";
import { Eye, ThumbsUp, MessageCircle, TrendingUp, Play, ExternalLink } from "lucide-react";

interface VideoCardProps {
  video: VideoMetadata;
  side: "left" | "right";
}

function formatCount(n: number | null | undefined): string {
  if (n == null || isNaN(n as number)) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function getYoutubeVideoId(url: string): string | null {
  const match = url?.match(/(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([\w-]+)/);
  return match?.[1] ?? null;
}

function YoutubeLogo() {
  return (
    <svg width="22" height="16" viewBox="0 0 22 16" fill="none">
      <rect width="22" height="16" rx="4" fill="#FF0000" />
      <path d="M9 4.5L15 8L9 11.5V4.5Z" fill="white" />
    </svg>
  );
}

function InstagramLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <defs>
        <radialGradient id="ig-grad" cx="30%" cy="107%" r="150%">
          <stop offset="0%"   stopColor="#FFD600" />
          <stop offset="30%"  stopColor="#FF6D00" />
          <stop offset="60%"  stopColor="#E1306C" />
          <stop offset="90%"  stopColor="#833AB4" />
          <stop offset="100%" stopColor="#4F5BD5" />
        </radialGradient>
      </defs>
      <rect width="18" height="18" rx="4.5" fill="url(#ig-grad)" />
      <rect x="4.5" y="4.5" width="9" height="9" rx="2.5" stroke="white" strokeWidth="1.4" fill="none" />
      <circle cx="9" cy="9" r="2.5" stroke="white" strokeWidth="1.4" fill="none" />
      <circle cx="13.2" cy="4.8" r="0.9" fill="white" />
    </svg>
  );
}

export default function VideoCard({ video }: VideoCardProps) {
  const [thumbError, setThumbError] = useState(false);
  const isYoutube   = video.platform === "youtube";
  const isInstagram = video.platform === "instagram";

  const ytId       = isYoutube ? getYoutubeVideoId(video.url) : null;
  const ytEmbed    = ytId ? `https://www.youtube.com/embed/${ytId}` : null;
  const ytThumbs   = ytId
    ? [`https://img.youtube.com/vi/${ytId}/0.jpg`, `https://img.youtube.com/vi/${ytId}/1.jpg`, `https://img.youtube.com/vi/${ytId}/2.jpg`]
    : [];

  const igReelId   = isInstagram ? video.url?.match(/\/reel\/([\w-]+)/)?.[1] : null;
  const igEmbed    = igReelId ? `https://www.instagram.com/p/${igReelId}/embed` : null;

  const metrics = isYoutube
    ? [
        { label: "VIEWS",     value: formatCount(video.views),    icon: Eye           },
        { label: "LIKES",     value: formatCount(video.likes),    icon: ThumbsUp      },
        { label: "COMMENTS",  value: formatCount(video.comments), icon: MessageCircle },
        { label: "ENGAGEMENT", value: video.engagement_rate ? `${video.engagement_rate.toFixed(1)}%` : "—", icon: TrendingUp, highlight: true },
      ]
    : [
        { label: "EST. PLAYS", value: formatCount(video.views),    icon: Play          },
        { label: "LIKES",      value: formatCount(video.likes),    icon: ThumbsUp      },
        { label: "COMMENTS",   value: formatCount(video.comments), icon: MessageCircle },
        { label: "ENGAGEMENT", value: video.engagement_rate ? `${video.engagement_rate.toFixed(1)}%` : "—", icon: TrendingUp, highlight: true },
      ];

  return (
    <div className="bg-white rounded-2xl border border-neutral-200 shadow-card overflow-hidden card-lift">

      {/* Header */}
      <div className="px-5 py-3.5 flex items-center justify-between border-b border-neutral-200">
        <div className="flex items-center gap-2.5">
          {isYoutube ? <YoutubeLogo /> : <InstagramLogo />}
          <span className="font-display font-bold text-[15px]" style={{ color: "#2B2B2B" }}>
            {isYoutube ? "YouTube Insight" : "Instagram Reel"}
          </span>
        </div>
        <span
          className="text-[11px] font-mono px-2 py-0.5 rounded"
          style={{ background: "#F7F7F7", color: "#9E9E9E", border: "1px solid #E0E0E0" }}
        >
          {video.video_id === "A"
            ? `yt_${video.views ? Math.floor(video.views / 1000) : "–"}`
            : `ig_${video.likes ? Math.floor(video.likes / 10) : "–"}`}
        </span>
      </div>

      {/* Media */}
      {isYoutube ? (
        <div className="relative w-full overflow-hidden" style={{ height: 480, background: "#1a1a1a" }}>
          {ytEmbed ? (
            <iframe
              src={ytEmbed}
              className="w-full h-full"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          ) : (
            <div className="thumb-strip w-full h-full">
              {ytThumbs.map((src, i) => (
                <img key={i} src={src} alt={`Frame ${i + 1}`} className="w-full h-full object-cover" />
              ))}
            </div>
          )}
          {video.duration_seconds > 0 && (
            <div
              className="absolute bottom-2 right-2 text-white text-[11px] font-mono px-2 py-0.5 rounded z-10"
              style={{ background: "rgba(0,0,0,0.72)" }}
            >
              {formatDuration(video.duration_seconds)}
            </div>
          )}
        </div>
      ) : (
        /* Instagram — use neutral bg, show embed or thumbnail or link fallback */
        <div className="relative w-full overflow-hidden" style={{ height: 480, background: "#F3F3F3" }}>
          {igEmbed ? (
            <iframe
              src={igEmbed}
              className="w-full border-0"
              style={{ height: "100%" }}
              scrolling="no"
              allowTransparency
              allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
            />
          ) : video.thumbnail && !thumbError ? (
            <a href={video.url} target="_blank" rel="noopener noreferrer" className="block relative group h-full">
              <img
                src={video.thumbnail}
                alt={video.title || "Instagram Reel"}
                className="w-full h-full object-cover"
                onError={() => setThumbError(true)}
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center"
                  style={{ background: "rgba(255,255,255,0.30)", backdropFilter: "blur(6px)" }}
                >
                  <Play className="w-8 h-8 text-white ml-1" />
                </div>
              </div>
              {video.duration_seconds > 0 && (
                <div
                  className="absolute bottom-2 right-2 text-white text-[11px] font-mono px-2 py-0.5 rounded z-10"
                  style={{ background: "rgba(0,0,0,0.72)" }}
                >
                  {formatDuration(video.duration_seconds)}
                </div>
              )}
            </a>
          ) : (
            /* Graceful fallback — neutral card with link, no black box */
            <a
              href={video.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex flex-col items-center justify-center gap-3 h-full hover:bg-neutral-100 transition-colors"
            >
              <div
                className="w-14 h-14 rounded-full flex items-center justify-center"
                style={{ background: "linear-gradient(135deg,#E1306C,#833AB4)" }}
              >
                <Play className="w-7 h-7 text-white ml-0.5" />
              </div>
              <span className="text-sm font-medium flex items-center gap-1.5" style={{ color: "#E1306C" }}>
                View on Instagram <ExternalLink className="w-3.5 h-3.5" />
              </span>
            </a>
          )}
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-4 border-t" style={{ borderColor: "#E0E0E0" }}>
        {metrics.map((m, idx) => (
          <div
            key={m.label}
            className="py-3 px-2 text-center"
            style={{ borderRight: idx < metrics.length - 1 ? "1px solid #E0E0E0" : "none" }}
          >
            <p className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: "#9E9E9E" }}>
              {m.label}
            </p>
            <p className="text-[15px] font-bold" style={{ color: m.highlight ? "#FF4F00" : "#2B2B2B" }}>
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* Creator */}
      <div className="px-5 py-3 border-t flex items-center justify-between" style={{ borderColor: "#E0E0E0" }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white"
            style={{
              background: isYoutube
                ? "linear-gradient(135deg,#FF4F00,#CC3F00)"
                : "linear-gradient(135deg,#E1306C,#833AB4)",
            }}
          >
            {video.creator?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "#2B2B2B" }}>
              @{video.creator}
            </p>
            <p className="text-[11px]" style={{ color: "#9E9E9E" }}>
              {video.follower_count
                ? formatCount(video.follower_count) + (isYoutube ? " Subscribers" : " Followers")
                : ""}
            </p>
          </div>
        </div>

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