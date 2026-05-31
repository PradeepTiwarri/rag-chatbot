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
  { icon: Home, label: "Home", href: "/" },
  { icon: Video, label: "Video Analysis", href: "/analysis", active: true },
  { icon: Database, label: "Data Sources", href: "/sources" },
  { icon: Users, label: "Team", href: "/team" },
  { icon: FileText, label: "Reports", href: "/reports" },
];

export default function Sidebar() {
  const [active, setActive] = useState("Video Analysis");

  return (
    <aside className="w-56 bg-white border-r border-surface-200 flex flex-col min-h-screen">
      {/* User Card */}
      <div className="px-4 pt-6 pb-4">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center text-white">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-surface-900">
              Analyst Pro
            </p>
            <p className="text-[11px] text-surface-500">Premium Tier</p>
          </div>
        </div>

        {/* New Analysis Button */}
        <button className="w-full flex items-center justify-center gap-2 py-2.5 bg-accent-500 hover:bg-accent-600 text-white text-sm font-semibold rounded-lg transition-colors">
          <Plus className="w-4 h-4" />
          New Analysis
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2">
        <div className="space-y-0.5">
          {menuItems.map((item) => (
            <button
              key={item.label}
              onClick={() => setActive(item.label)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                active === item.label
                  ? "bg-accent-50 text-accent-600 font-semibold border-l-[3px] border-accent-500"
                  : "text-surface-600 hover:text-surface-900 hover:bg-surface-100"
              }`}
            >
              <item.icon
                className={`w-[18px] h-[18px] ${
                  active === item.label ? "text-accent-500" : "text-surface-400"
                }`}
              />
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-surface-200 space-y-0.5">
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-surface-600 hover:text-surface-900 hover:bg-surface-100 transition-colors">
          <HelpCircle className="w-[18px] h-[18px] text-surface-400" />
          Help
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-surface-600 hover:text-surface-900 hover:bg-surface-100 transition-colors">
          <LogOut className="w-[18px] h-[18px] text-surface-400" />
          Logout
        </button>
      </div>
    </aside>
  );
}