"use client";

import { useState } from "react";
import { VideoMetadata } from "../types";
import { Eye, ThumbsUp, MessageCircle, TrendingUp, Play } from "lucide-react";

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

/** Derive 3 thumbnail URLs from a YouTube video ID at 0%, 40%, 75% of duration */
function getYoutubeThumbnails(url: string): string[] {
  const match = url?.match(/(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([\w-]+)/);
  const id = match?.[1];
  if (!id) return [];
  // YouTube provides mqdefault / hqdefault / sddefault — use hqdefault as base
  return [
    `https://img.youtube.com/vi/${id}/0.jpg`,
    `https://img.youtube.com/vi/${id}/1.jpg`,
    `https://img.youtube.com/vi/${id}/2.jpg`,
  ];
}

// ── YouTube SVG logo (exact brand red #FF0000) ─────────────────────────────
function YoutubeLogo() {
  return (
    <svg width="22" height="16" viewBox="0 0 22 16" fill="none">
      <rect width="22" height="16" rx="4" fill="#FF0000" />
      <path d="M9 4.5L15 8L9 11.5V4.5Z" fill="white" />
    </svg>
  );
}

// ── Instagram SVG logo (brand gradient) ────────────────────────────────────
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
  const [thumbErrors, setThumbErrors] = useState<Record<number, boolean>>({});
  const isYoutube   = video.platform === "youtube";
  const isInstagram = video.platform === "instagram";

  // ── Embed / frame logic ─────────────────────────────────────────────────
  const getYoutubeEmbedUrl = () => {
    if (!video.url) return null;
    const match = video.url.match(
      /(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([\w-]+)/
    );
    const id = match?.[1];
    return id ? `https://www.youtube.com/embed/${id}` : null;
  };

  const getInstagramEmbedUrl = () => {
    if (!video.url) return null;
    const match = video.url.match(/\/reel\/([\w-]+)/);
    const id = match?.[1];
    return id ? `https://www.instagram.com/p/${id}/embed` : null;
  };

  const ytEmbedUrl  = isYoutube   ? getYoutubeEmbedUrl()   : null;
  const igEmbedUrl  = isInstagram ? getInstagramEmbedUrl()  : null;
  const ytThumbs    = isYoutube   ? getYoutubeThumbnails(video.url) : [];

  // ── Metrics row ─────────────────────────────────────────────────────────
  const metrics = isYoutube
    ? [
        { label: "VIEWS",     value: formatCount(video.views),    icon: Eye           },
        { label: "LIKES",     value: formatCount(video.likes),    icon: ThumbsUp      },
        { label: "COMMENTS",  value: formatCount(video.comments), icon: MessageCircle },
        {
          label: "ENGAGEMENT",
          value: video.engagement_rate ? `${video.engagement_rate.toFixed(1)}%` : "—",
          icon: TrendingUp, highlight: true,
        },
      ]
    : [
        { label: "EST. PLAYS", value: formatCount(video.views),    icon: Play          },
        { label: "LIKES",      value: formatCount(video.likes),    icon: ThumbsUp      },
        { label: "COMMENTS",   value: formatCount(video.comments), icon: MessageCircle },
        {
          label: "ENGAGEMENT",
          value: video.engagement_rate ? `${video.engagement_rate.toFixed(1)}%` : "—",
          icon: TrendingUp, highlight: true,
        },
      ];

  return (
    <div className="bg-white rounded-2xl border border-neutral-200 shadow-card overflow-hidden card-lift">

      {/* ── Header ─────────────────────────────────────────────────────── */}
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
          {video.video_id === "A" ? `yt_${video.views ? Math.floor(video.views / 1000) : "–"}` : `ig_${video.likes ? Math.floor(video.likes / 10) : "–"}`}
        </span>
      </div>

      {/* ── Media area ─────────────────────────────────────────────────── */}
      {isYoutube ? (
        /* YouTube: always 16:9 iframe embed */
        <div className="frame-landscape">
          <div>
            {ytEmbedUrl ? (
              <iframe
                src={ytEmbedUrl}
                className="w-full h-full"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            ) : (
              /* fallback: 3-frame thumbnail strip */
              <div className="thumb-strip w-full h-full">
                {ytThumbs.map((src, i) => (
                  <img
                    key={i}
                    src={thumbErrors[i] ? "" : src}
                    alt={`Frame ${i + 1}`}
                    className="w-full h-full object-cover"
                    onError={() => setThumbErrors((p) => ({ ...p, [i]: true }))}
                  />
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
        </div>
      ) : (
        /* Instagram: Standard iframe inside 16:9 frame. No clipping/shifting to prevent Instagram from triggering a clickjacking redirect. */
        <div className="frame-landscape">
          {igEmbedUrl ? (
            <iframe
              src={igEmbedUrl}
              className="w-full h-full"
              frameBorder="0"
              scrolling="no"
              allowTransparency
              allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
              allowFullScreen
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-black">
              <Play className="w-12 h-12" style={{ color: "#9E9E9E" }} />
            </div>
          )}
        </div>
      )}

      {/* ── Metrics row ────────────────────────────────────────────────── */}
      <div
        className="grid grid-cols-4 border-t"
        style={{ borderColor: "#E0E0E0" }}
      >
        {metrics.map((m, idx) => (
          <div
            key={m.label}
            className="py-3 px-2 text-center"
            style={{
              borderRight: idx < metrics.length - 1 ? "1px solid #E0E0E0" : "none",
            }}
          >
            <p className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: "#9E9E9E" }}>
              {m.label}
            </p>
            <p
              className="text-[15px] font-bold"
              style={{ color: m.highlight ? "#FF4F00" : "#2B2B2B" }}
            >
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* ── Creator row ────────────────────────────────────────────────── */}
      <div
        className="px-5 py-3 border-t flex items-center justify-between"
        style={{ borderColor: "#E0E0E0" }}
      >
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
                ? formatCount(video.follower_count) +
                  (isYoutube ? " Subscribers" : " Followers")
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