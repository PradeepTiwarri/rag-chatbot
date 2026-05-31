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
        <header className="bg-white border-b border-surface-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1.5">
              <span className="font-display font-extrabold text-lg text-surface-900">
                RAG
              </span>
              <span className="font-display font-extrabold text-lg text-accent-500">
                Video Analyst
              </span>
            </div>
            <nav className="flex items-center gap-5 ml-4">
              <a className="text-sm font-semibold text-accent-500 underline underline-offset-4 decoration-2 decoration-accent-500 cursor-pointer">
                Dashboard
              </a>
              <a className="text-sm font-medium text-surface-500 hover:text-accent-600 transition-colors cursor-pointer">
                Comparison
              </a>
              <a className="text-sm font-medium text-surface-500 hover:text-accent-600 transition-colors cursor-pointer">
                Archive
              </a>
              <a className="text-sm font-medium text-surface-500 hover:text-accent-600 transition-colors cursor-pointer">
                Settings
              </a>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {/* Videos Loaded Badge */}
            <div className="status-loaded">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M10 8.5L16 12L10 15.5V8.5Z" fill="#F97316" />
              </svg>
              <span>
                Videos Loaded:{" "}
                <strong className="text-accent-600">YouTube</strong>{" "}
                <Check className="w-3 h-3 inline text-green-500" /> |{" "}
                <strong className="text-accent-600">Instagram</strong>{" "}
                <Check className="w-3 h-3 inline text-green-500" />
              </span>
            </div>
            <button className="p-2 rounded-full hover:bg-surface-100 transition-colors">
              <Bell className="w-[18px] h-[18px] text-surface-500" />
            </button>
            <button className="w-8 h-8 rounded-full bg-surface-200 flex items-center justify-center">
              <User className="w-[18px] h-[18px] text-surface-500" />
            </button>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto px-6 py-6 page-bg">
          {/* Dashboard Header */}
          <div className="flex items-start justify-between mb-6 relative z-10">
            <div>
              <h1 className="text-3xl font-display font-extrabold text-surface-900 tracking-tight">
                Video Content Pulse
              </h1>
              <p className="text-surface-500 text-sm mt-1">
                Compare YouTube &amp; Instagram Reels with AI-driven
                retrieval-augmented generation.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Solo / Compare Toggle */}
              <div className="flex bg-surface-100 rounded-xl p-1 border border-surface-200">
                <button
                  onClick={() => setViewMode("solo")}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    viewMode === "solo"
                      ? "bg-white shadow-sm text-surface-900"
                      : "text-surface-500 hover:text-surface-700"
                  }`}
                >
                  Solo
                </button>
                <button
                  onClick={() => setViewMode("compare")}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    viewMode === "compare"
                      ? "bg-white shadow-sm text-surface-900"
                      : "text-surface-500 hover:text-surface-700"
                  }`}
                >
                  Compare
                </button>
              </div>
              {/* Export */}
              <button className="flex items-center gap-2 px-4 py-2 bg-white border border-surface-200 rounded-xl text-sm font-medium text-surface-700 hover:bg-surface-50 transition-colors shadow-sm">
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