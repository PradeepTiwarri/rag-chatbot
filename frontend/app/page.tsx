"use client";

import { useState } from "react";
import VideoCard from "./components/VideoCard";
import IngestForm from "./components/IngestForm";
import ChatPanel from "./components/ChatPanel";
import Sidebar from "./components/Sidebar";
import { VideoMetadata } from "./types";
import {
  Bell,
  User,
  Download,
  Check,
} from "lucide-react";

export default function Home() {
  const [videoA, setVideoA] = useState<VideoMetadata | null>(null);
  const [videoB, setVideoB] = useState<VideoMetadata | null>(null);
  const [isIngested, setIsIngested] = useState(false);
  const [viewMode, setViewMode] = useState<"compare" | "solo">("compare");

  const handleIngestComplete = (a: VideoMetadata, b: VideoMetadata) => {
    setVideoA(a);
    setVideoB(b);
    setIsIngested(true);
  };

  // ---------- Ingest Phase: Full-page, no sidebar ----------
  if (!isIngested) {
    return <IngestForm onIngestComplete={handleIngestComplete} />;
  }

  // ---------- Dashboard Phase: Sidebar + Content ----------
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navbar */}
        <header
          className="flex-shrink-0 px-6 py-3 flex items-center justify-between"
          style={{ background: "#fff", borderBottom: "1px solid #E0E0E0" }}
        >
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1">
              <span className="font-display font-extrabold text-lg" style={{ color: "#2B2B2B" }}>RAG</span>
              <span className="font-display font-extrabold text-lg" style={{ color: "#FF4F00" }}>{" "}Video Analyst</span>
            </div>
            <nav className="flex items-center gap-5 ml-4">
              {["Dashboard", "Comparison", "Archive", "Settings"].map((item) => (
                <a
                  key={item}
                  className="text-sm font-medium cursor-pointer transition-colors"
                  style={item === "Dashboard"
                    ? { color: "#FF4F00", textDecoration: "underline", textUnderlineOffset: "4px", textDecorationThickness: "2px" }
                    : { color: "#9E9E9E" }
                  }
                >
                  {item}
                </a>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {/* Videos Loaded Badge */}
            <div className="status-loaded">
              <svg width="14" height="10" viewBox="0 0 22 16" fill="none">
                <rect width="22" height="16" rx="4" fill="#FF0000" />
                <path d="M9 4.5L15 8L9 11.5V8.5V4.5Z" fill="white" />
              </svg>
              <span>
                Videos Loaded:{" "}
                <strong style={{ color: "#FF4F00" }}>YouTube</strong>{" "}
                <Check className="w-3 h-3 inline" style={{ color: "#22c55e" }} /> |{" "}
                <strong style={{ color: "#FF4F00" }}>Instagram</strong>{" "}
                <Check className="w-3 h-3 inline" style={{ color: "#22c55e" }} />
              </span>
            </div>
            <button className="p-2 rounded-full transition-colors" style={{ color: "#9E9E9E" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#F7F7F7")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <Bell className="w-[18px] h-[18px]" />
            </button>
            <button
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ background: "#E0E0E0" }}
            >
              <User className="w-[18px] h-[18px]" style={{ color: "#757575" }} />
            </button>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto px-6 py-6 page-bg">
          {/* Dashboard Header */}
          <div className="flex items-start justify-between mb-6 relative z-10">
            <div>
              <h1 className="text-3xl font-display font-extrabold tracking-tight" style={{ color: "#2B2B2B" }}>
                Video Content Pulse
              </h1>
              <p className="text-sm mt-1" style={{ color: "#9E9E9E" }}>
                Compare YouTube &amp; Instagram Reels with AI-driven retrieval-augmented generation.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Solo / Compare Toggle */}
              <div
                className="flex rounded-xl p-1"
                style={{ background: "#F7F7F7", border: "1px solid #E0E0E0" }}
              >
                {(["solo", "compare"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize"
                    style={viewMode === mode
                      ? { background: "#fff", color: "#2B2B2B", boxShadow: "0 1px 3px rgba(0,0,0,0.10)" }
                      : { color: "#9E9E9E" }
                    }
                  >
                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                  </button>
                ))}
              </div>
              {/* Export */}
              <button
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl transition-colors"
                style={{ background: "#fff", border: "1px solid #E0E0E0", color: "#555" }}
              >
                <Download className="w-4 h-4" />
                Export Analysis
              </button>
            </div>
          </div>

          {/* Video Cards */}
          {videoA && videoB && (
            <div
              className={`grid gap-6 mb-6 relative z-10 ${
                viewMode === "compare" ? "grid-cols-2" : "grid-cols-1 max-w-2xl"
              }`}
            >
              <div id="video-a" className="fade-in-up">
                <VideoCard video={videoA} side="left" />
              </div>
              {viewMode === "compare" && (
                <div
                  id="video-b"
                  className="fade-in-up"
                  style={{ animationDelay: "100ms" }}
                >
                  <VideoCard video={videoB} side="right" />
                </div>
              )}
            </div>
          )}

          {/* Chat Panel */}
          <div className="h-[520px] relative z-10 fade-in-up" style={{ animationDelay: "200ms" }}>
            <ChatPanel videoIds={["A", "B"]} />
          </div>
        </main>
      </div>
    </div>
  );
}