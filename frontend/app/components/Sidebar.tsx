"use client";

import {
  Home,
  Video,
  Database,
  Users,
  FileText,
  HelpCircle,
  LogOut,
  Plus,
} from "lucide-react";
import { useState } from "react";

const menuItems = [
  { icon: Home,     label: "Home",          href: "/" },
  { icon: Video,    label: "Video Analysis", href: "/analysis", active: true },
  { icon: Database, label: "Data Sources",   href: "/sources" },
  { icon: Users,    label: "Team",           href: "/team" },
  { icon: FileText, label: "Reports",        href: "/reports" },
];

export default function Sidebar() {
  const [active, setActive] = useState("Video Analysis");

  return (
    <aside
      className="w-56 flex flex-col min-h-screen"
      style={{ background: "#fff", borderRight: "1px solid #E0E0E0" }}
    >
      {/* ── User card ─────────────────────────────────────────────── */}
      <div className="px-4 pt-5 pb-4">
        <div className="flex items-center gap-3 mb-5">
          {/* Avatar with brand primary */}
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-white"
            style={{ background: "#FF4F00" }}
          >
            <Video className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "#2B2B2B" }}>
              Analyst Pro
            </p>
            <p className="text-[11px]" style={{ color: "#9E9E9E" }}>
              Premium Tier
            </p>
          </div>
        </div>

        {/* New Analysis button — brand primary */}
        <button
          className="w-full flex items-center justify-center gap-2 py-2.5 text-white text-sm font-semibold rounded-xl transition-opacity hover:opacity-90"
          style={{ background: "#FF4F00" }}
        >
          <Plus className="w-4 h-4" />
          + New Analysis
        </button>
      </div>

      {/* ── Nav items ─────────────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-2">
        <div className="space-y-0.5">
          {menuItems.map((item) => {
            const isActive = active === item.label;
            return (
              <button
                key={item.label}
                onClick={() => setActive(item.label)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all"
                style={{
                  background:  isActive ? "rgba(255,79,0,0.07)" : "transparent",
                  color:       isActive ? "#FF4F00" : "#757575",
                  fontWeight:  isActive ? 600 : 400,
                  borderLeft:  isActive ? "3px solid #FF4F00" : "3px solid transparent",
                }}
              >
                <item.icon
                  className="w-[18px] h-[18px]"
                  style={{ color: isActive ? "#FF4F00" : "#BDBDBD" }}
                />
                {item.label}
              </button>
            );
          })}
        </div>
      </nav>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <div className="p-3 space-y-0.5" style={{ borderTop: "1px solid #E0E0E0" }}>
        {[
          { icon: HelpCircle, label: "Help"   },
          { icon: LogOut,     label: "Logout" },
        ].map(({ icon: Icon, label }) => (
          <button
            key={label}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors"
            style={{ color: "#757575" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "#2B2B2B";
              (e.currentTarget as HTMLButtonElement).style.background = "#F7F7F7";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "#757575";
              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
            }}
          >
            <Icon className="w-[18px] h-[18px]" style={{ color: "#BDBDBD" }} />
            {label}
          </button>
        ))}
      </div>
    </aside>
  );
}