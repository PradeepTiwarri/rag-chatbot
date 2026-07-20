"use client";

import { useChat } from "@ai-sdk/react";
import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Mic, Paperclip, Trash2, MoreVertical } from "lucide-react";
import CitationBadge from "./CitationBadge";
import QuickActions from "./QuickActions";
import { Citation } from "../types";

interface ChatPanelProps {
  videoIds: string[];
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export default function ChatPanel({ videoIds }: ChatPanelProps) {
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    setInput,
  } = useChat({
    api: `${API_URL}/api/chat`,
    body: { video_ids: videoIds },
    onError: (error) => {
      console.error("Chat error:", error);
    },
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [citations, setCitations] = useState<Record<string, Citation[]>>({});

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Parse citations from message content
  const parseCitations = (
    content: string
  ): { text: string; citations: Citation[] } => {
    const citationRegex = /\[(yt|ig):([\d\-s]+)\]/g;
    const foundCitations: Citation[] = [];
    let cleanText = content;

    let match;
    while ((match = citationRegex.exec(content)) !== null) {
      foundCitations.push({
        video_id: match[1] === "yt" ? "A" : "B",
        timestamp: match[2],
        text: "",
      });
      cleanText = cleanText.replace(match[0], "");
    }

    return { text: cleanText, citations: foundCitations };
  };

  const handleQuickAction = (question: string) => {
    setInput(question);
    const fakeEvent = { preventDefault: () => { } } as React.FormEvent;
    handleSubmit(fakeEvent);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-surface-200 shadow-card overflow-hidden min-w-0">
      {/* Header */}
      <div className="px-3 sm:px-5 py-3 sm:py-4 border-b border-surface-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 8V4H8" />
              <rect x="2" y="2" width="20" height="20" rx="5" />
              <path d="M2 12h20" />
              <path d="M12 2v20" />
            </svg>
          </div>
          <div>
            <span className="font-display font-bold text-surface-900">
              Video Analyst Assistant
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-[11px] text-surface-500">Llama 3.1</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 rounded-lg hover:bg-surface-100 transition-colors text-surface-400 hover:text-surface-600">
            <Trash2 className="w-4 h-4" />
          </button>
          <button className="p-2 rounded-lg hover:bg-surface-100 transition-colors text-surface-400 hover:text-surface-600">
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 sm:px-5 py-3 sm:py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-surface-400 mt-12">
            <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-accent-50 flex items-center justify-center">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#F97316"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-surface-600">
              Ask me anything about these videos!
            </p>
            <p className="text-xs mt-1 text-surface-400">
              Try: &quot;Compare the engagement rates&quot; or &quot;What did
              they say in the opening?&quot;
            </p>
          </div>
        )}

        {messages.map((message) => {
          const { text, citations: msgCitations } = parseCitations(
            message.content
          );

          return (
            <div
              key={message.id}
              className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"
                }`}
            >
              {message.role === "assistant" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center flex-shrink-0 mt-1">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M12 8V4H8" />
                    <rect x="2" y="2" width="20" height="20" rx="5" />
                    <path d="M2 12h20" />
                    <path d="M12 2v20" />
                  </svg>
                </div>
              )}

              <div
                className={`max-w-[90%] sm:max-w-[75%] rounded-2xl px-3 sm:px-4 py-2.5 sm:py-3 ${message.role === "user"
                    ? "bg-accent-50 border border-accent-100 text-surface-800"
                    : "bg-surface-100 border border-surface-200 text-surface-800"
                  }`}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {text}
                </p>

                {msgCitations.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2.5 pt-2 border-t border-surface-200">
                    {msgCitations.map((citation, idx) => (
                      <CitationBadge
                        key={idx}
                        citation={citation}
                        onClick={() => {
                          const videoElement = document.getElementById(
                            citation.video_id === "A" ? "video-a" : "video-b"
                          );
                          videoElement?.scrollIntoView({
                            behavior: "smooth",
                            block: "center",
                          });
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 8V4H8" />
                <rect x="2" y="2" width="20" height="20" rx="5" />
                <path d="M2 12h20" />
                <path d="M12 2v20" />
              </svg>
            </div>
            <div className="bg-surface-100 border border-surface-200 rounded-2xl px-4 py-3 flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-surface-400 animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-2 h-2 rounded-full bg-surface-400 animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-2 h-2 rounded-full bg-surface-400 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <div className="px-3 sm:px-5 pt-3 border-t border-surface-200">
        <QuickActions onActionClick={handleQuickAction} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-3 sm:px-5 pb-3 sm:pb-4">
        <div className="flex items-center gap-2 bg-surface-100 border border-surface-200 rounded-2xl px-4 py-2 focus-within:ring-2 focus-within:ring-accent-200 focus-within:border-accent-400 transition-all">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder="Ask AI about these videos..."
            className="flex-1 bg-transparent text-sm text-surface-800 placeholder-surface-400 focus:outline-none py-1"
            disabled={isLoading}
          />
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="p-1.5 rounded-lg hover:bg-surface-200 transition-colors text-surface-400"
            >
              <Mic className="w-4 h-4" />
            </button>
            <button
              type="button"
              className="p-1.5 rounded-lg hover:bg-surface-200 transition-colors text-surface-400"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="p-2 bg-accent-500 hover:bg-accent-600 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed send-glow"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}