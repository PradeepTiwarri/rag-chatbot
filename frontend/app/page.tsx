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
  Menu,
} from "lucide-react";

export default function Home() {
  const [videoA, setVideoA] = useState<VideoMetadata | null>(null);
  const [videoB, setVideoB] = useState<VideoMetadata | null>(null);
  const [isIngested, setIsIngested] = useState(false);
  const [viewMode, setViewMode] = useState<"compare" | "solo">("compare");
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top Navbar */}
        <header
          className="flex-shrink-0 px-4 sm:px-6 py-3 flex items-center justify-between gap-3"
          style={{ background: "#fff", borderBottom: "1px solid #E0E0E0" }}
        >
          <div className="flex items-center gap-3 sm:gap-6 min-w-0">
            {/* Mobile hamburger */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-neutral-100 transition-colors lg:hidden flex-shrink-0"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" style={{ color: "#555" }} />
            </button>

            <div className="flex items-center gap-1 flex-shrink-0">
              <span className="font-display font-extrabold text-base sm:text-lg" style={{ color: "#2B2B2B" }}>RAG</span>
              <span className="font-display font-extrabold text-base sm:text-lg" style={{ color: "#FF4F00" }}>{" "}Video Analyst</span>
            </div>

            {/* Desktop nav links — hidden on mobile */}
            <nav className="hidden md:flex items-center gap-5 ml-4">
              {["Dashboard", "Comparison", "Archive", "Settings"].map((item) => (
                <a
                  key={item}
                  className="text-sm font-medium cursor-pointer transition-colors whitespace-nowrap"
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

          <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
            {/* Videos Loaded Badge — hidden on small screens */}
            <div className="status-loaded hidden lg:inline-flex">
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
              className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: "#E0E0E0" }}
            >
              <User className="w-[18px] h-[18px]" style={{ color: "#757575" }} />
            </button>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto px-4 sm:px-6 py-4 sm:py-6 page-bg">
          {/* Dashboard Header */}
          <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-4 sm:mb-6 gap-3 relative z-10">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-display font-extrabold tracking-tight" style={{ color: "#2B2B2B" }}>
                Video Content Pulse
              </h1>
              <p className="text-xs sm:text-sm mt-1" style={{ color: "#9E9E9E" }}>
                Compare YouTube &amp; Instagram Reels with AI-driven retrieval-augmented generation.
              </p>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
              {/* Solo / Compare Toggle */}
              <div
                className="flex rounded-xl p-1"
                style={{ background: "#F7F7F7", border: "1px solid #E0E0E0" }}
              >
                {(["solo", "compare"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className="px-3 sm:px-4 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all capitalize"
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
                className="flex items-center gap-2 px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium rounded-xl transition-colors"
                style={{ background: "#fff", border: "1px solid #E0E0E0", color: "#555" }}
              >
                <Download className="w-4 h-4" />
                <span className="hidden sm:inline">Export Analysis</span>
                <span className="sm:hidden">Export</span>
              </button>
            </div>
          </div>

          {/* Video Cards — responsive: 1-col on mobile, 2-col on desktop compare */}
          {videoA && videoB && (
            <div
              className={`grid gap-4 sm:gap-6 mb-4 sm:mb-6 relative z-10 ${
                viewMode === "compare"
                  ? "grid-cols-1 lg:grid-cols-2"
                  : "grid-cols-1 max-w-2xl"
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

          {/* Chat Panel — responsive height */}
          <div className="h-[400px] sm:h-[480px] lg:h-[520px] relative z-10 fade-in-up" style={{ animationDelay: "200ms" }}>
            <ChatPanel videoIds={["A", "B"]} />
          </div>
        </main>
      </div>
    </div>
  );
}