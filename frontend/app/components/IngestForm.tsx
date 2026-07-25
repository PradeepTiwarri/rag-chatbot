"use client";

import { useState } from "react";
import { IngestResponse, VideoMetadata } from "../types";
import { ShieldCheck, CheckCircle2, Loader2, Circle } from "lucide-react";

interface IngestFormProps {
  onIngestComplete: (videoA: VideoMetadata, videoB: VideoMetadata) => void;
}

type PipelineStep = "idle" | "transcripts" | "embeddings" | "storage" | "done";

export default function IngestForm({ onIngestComplete }: IngestFormProps) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [ytValidated, setYtValidated] = useState(false);
  const [igValidated, setIgValidated] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>("idle");

  const validateYoutube = () => {
    if (youtubeUrl.match(/youtube\.com\/watch|youtu\.be\/|youtube\.com\/shorts\//)) {
      setYtValidated(true);
    }
  };

  const validateInstagram = () => {
    if (instagramUrl.match(/instagram\.com\/reel/)) {
      setIgValidated(true);
    }
  };

  const handleIngest = async () => {
    if (!youtubeUrl || !instagramUrl) {
      alert("Please enter both YouTube and Instagram URLs");
      return;
    }
    

    setIsLoading(true);
    setPipelineStep("transcripts");

    try {
      const response = await fetch(`/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          youtube_url: youtubeUrl,
          instagram_url: instagramUrl,
        }),
      });

      setPipelineStep("embeddings");

      const data: IngestResponse = await response.json();

      setPipelineStep("storage");

      if (
        data.A.status === "success" &&
        data.B.status === "success" &&
        data.A.metadata &&
        data.B.metadata
      ) {
        setPipelineStep("done");
        setTimeout(() => {
          onIngestComplete(data.A.metadata!, data.B.metadata!);
        }, 600);
      } else {
        const errorMsg =
          data.A.error || data.B.error || "Unknown error during ingestion";
        alert(`Ingestion error: ${errorMsg}`);
        setPipelineStep("idle");
      }
    } catch (error) {
      console.error("Ingest error:", error);
      alert("Failed to connect to backend");
      setPipelineStep("idle");
    } finally {
      setIsLoading(false);
    }
  };

  const stepIcon = (step: PipelineStep, current: PipelineStep) => {
    const steps: PipelineStep[] = ["transcripts", "embeddings", "storage"];
    const stepIdx = steps.indexOf(step);
    const currentIdx = steps.indexOf(current);

    if (current === "done" || currentIdx > stepIdx) {
      return <CheckCircle2 className="w-4 h-4 text-accent-500" />;
    }
    if (current === step) {
      return <Loader2 className="w-4 h-4 text-accent-500 animate-spin" />;
    }
    return <Circle className="w-4 h-4 text-surface-400" />;
  };

  const stepTextColor = (step: PipelineStep, current: PipelineStep) => {
    const steps: PipelineStep[] = ["transcripts", "embeddings", "storage"];
    const stepIdx = steps.indexOf(step);
    const currentIdx = steps.indexOf(current);

    if (current === "done" || currentIdx > stepIdx) return "text-surface-800 font-medium";
    if (current === step) return "text-surface-800 font-medium";
    return "text-surface-400";
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-start pt-16 page-bg relative overflow-x-hidden">
      {/* Top Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-6 py-3">
          <div className="flex items-center gap-1">
            <span className="font-display font-extrabold text-lg text-surface-900">
              RAG
            </span>
            <span className="font-display font-extrabold text-lg text-surface-900">
              {" "}Video Analyst
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-6 lg:gap-8">
            <a className="text-sm font-medium text-surface-900 hover:text-accent-600 transition-colors cursor-pointer">
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
          </div>
          <div className="flex items-center gap-3">
            <button className="p-2 rounded-full hover:bg-surface-100 transition-colors">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="text-surface-600">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>
            <button className="w-8 h-8 rounded-full bg-surface-200 flex items-center justify-center">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="text-surface-600">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Title */}
      <div className="mt-6 sm:mt-8 mb-6 sm:mb-10 text-center fade-in-up relative z-10 px-4">
        <h1 className="text-2xl sm:text-4xl md:text-5xl font-display font-extrabold text-surface-900 tracking-tight">
          Ingest Analysis Pipeline
        </h1>
      </div>

      {/* Input Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 w-full max-w-4xl px-4 mb-6 sm:mb-8 fade-in-up relative z-10">
        {/* YouTube Card */}
        <div className="bg-white rounded-2xl border border-surface-200 shadow-card p-6 card-lift">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <rect width="24" height="24" rx="6" fill="#FEE2E2" />
                <path d="M10 8.5L16 12L10 15.5V8.5Z" fill="#EF4444" />
              </svg>
            </div>
            <h3 className="text-lg font-display font-bold text-surface-900">
              YouTube
            </h3>
          </div>
          <p className="text-sm text-surface-500 mb-4">
            Enter a video link to extract high-fidelity transcripts and visual
            metadata for indexing.
          </p>
          <label className="block text-[11px] font-semibold text-surface-500 tracking-wider uppercase mb-1.5">
            Video URL
          </label>
          <input
            type="text"
            value={youtubeUrl}
            onChange={(e) => {
              setYoutubeUrl(e.target.value);
              setYtValidated(false);
            }}
            placeholder="Paste YouTube URL here..."
            className="w-full px-4 py-2.5 bg-white border border-surface-300 rounded-xl text-sm text-surface-800 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-accent-200 focus:border-accent-400 transition-all"
          />
          <p className="text-[11px] text-accent-400 mt-1 font-mono">
            Example: youtube.com/watch?v=dQw4w9WgXcQ
          </p>
          <button
            onClick={validateYoutube}
            className={`mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border text-sm font-medium transition-all ${ytValidated
              ? "border-green-300 bg-green-50 text-green-700"
              : "border-surface-300 bg-white text-surface-700 hover:border-accent-300 hover:bg-accent-50"
              }`}
          >
            <ShieldCheck className="w-4 h-4" />
            {ytValidated ? "Validated ✓" : "Validate Link"}
          </button>
        </div>

        {/* Instagram Card */}
        <div className="bg-white rounded-2xl border border-surface-200 shadow-card p-6 card-lift">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <rect width="24" height="24" rx="6" fill="#FFF7ED" />
                <rect x="6" y="6" width="12" height="12" rx="3" stroke="#F97316" strokeWidth="1.5" fill="none" />
                <circle cx="12" cy="12" r="3" stroke="#F97316" strokeWidth="1.5" fill="none" />
                <circle cx="16" cy="8" r="1" fill="#F97316" />
              </svg>
            </div>
            <h3 className="text-lg font-display font-bold text-surface-900">
              Instagram
            </h3>
          </div>
          <p className="text-sm text-surface-500 mb-4">
            Extract frames and OCR data from Reels for downstream vector search
            indexing.
          </p>
          <label className="block text-[11px] font-semibold text-surface-500 tracking-wider uppercase mb-1.5">
            Reel URL
          </label>
          <input
            type="text"
            value={instagramUrl}
            onChange={(e) => {
              setInstagramUrl(e.target.value);
              setIgValidated(false);
            }}
            placeholder="Paste Instagram Reel URL here..."
            className="w-full px-4 py-2.5 bg-white border border-surface-300 rounded-xl text-sm text-surface-800 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-accent-200 focus:border-accent-400 transition-all"
          />
          <p className="text-[11px] text-accent-400 mt-1 font-mono">
            Example: instagram.com/reels/C4p_ByIxpV/
          </p>
          <button
            onClick={validateInstagram}
            className={`mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border text-sm font-medium transition-all ${igValidated
              ? "border-green-300 bg-green-50 text-green-700"
              : "border-surface-300 bg-white text-surface-700 hover:border-accent-300 hover:bg-accent-50"
              }`}
          >
            <ShieldCheck className="w-4 h-4" />
            {igValidated ? "Validated ✓" : "Validate Link"}
          </button>
        </div>
      </div>

      {/* Analyze Button */}
      <div className="w-full max-w-xl px-4 mb-4 sm:mb-6 fade-in-up relative z-10">
        <button
          onClick={handleIngest}
          disabled={isLoading}
          className="btn-peach w-full py-4 text-base"
        >
          {isLoading ? "ANALYZING VIDEOS..." : "ANALYZE VIDEOS"}
        </button>
      </div>

      {/* Pipeline Progress */}
      {pipelineStep !== "idle" && (
        <div className="bg-white rounded-2xl border border-surface-200 shadow-card px-4 sm:px-8 py-5 max-w-xl w-full mx-4 fade-in-up relative z-10">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 flex-wrap">
            {/* Step 1 */}
            <div className="flex items-center gap-1.5">
              {stepIcon("transcripts", pipelineStep)}
              <span className={`text-[11px] tracking-wider uppercase ${stepTextColor("transcripts", pipelineStep)}`}>
                Fetching Transcripts
              </span>
            </div>
            <div className={`step-line ${pipelineStep === "embeddings" || pipelineStep === "storage" || pipelineStep === "done" ? "active" : ""
              }`} />
            {/* Step 2 */}
            <div className="flex items-center gap-1.5">
              {stepIcon("embeddings", pipelineStep)}
              <span className={`text-[11px] tracking-wider uppercase ${stepTextColor("embeddings", pipelineStep)}`}>
                Generating Embeddings
              </span>
            </div>
            <div className={`step-line ${pipelineStep === "storage" || pipelineStep === "done" ? "active" : ""
              }`} />
            {/* Step 3 */}
            <div className="flex items-center gap-1.5">
              {stepIcon("storage", pipelineStep)}
              <span className={`text-[11px] tracking-wider uppercase ${stepTextColor("storage", pipelineStep)}`}>
                Vector Storage
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
