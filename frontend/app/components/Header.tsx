"use client";

import React, { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, Database, Cpu, ExternalLink } from "lucide-react";

interface HeaderProps {
  onRefreshData: () => void;
  onOpenLeadership: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onRefreshData, onOpenLeadership }) => {
  const [health, setHealth] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHealth = async () => {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.warn("Could not fetch health status:", e);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch("/api/cache/refresh", { method: "POST" });
      await fetchHealth();
      onRefreshData();
    } catch (e) {
      console.error("Cache refresh error:", e);
    } finally {
      setTimeout(() => setRefreshing(false), 500);
    }
  };

  const isMondayLive = health?.monday_integration?.connected;

  return (
    <header className="h-14 border-b border-border bg-panel px-4 flex items-center justify-between select-none">
      {/* Brand */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded bg-gradient-to-br from-accent-sky-dark to-accent-sky flex items-center justify-center font-mono-data font-bold text-white text-sm shadow-sm">
          SK
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-sm tracking-wide text-text-primary uppercase">
              Skylark Drones
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-[#1f293d] text-accent-sky border border-[#2b3954] font-mono-data text-[10px]">
              BI AGENT v1.0
            </span>
          </div>
          <p className="text-[11px] text-text-secondary hidden sm:block">
            Ops Analyst Cockpit · Deals Pipeline & Work Orders Intelligence
          </p>
        </div>
      </div>

      {/* Status Badges */}
      <div className="flex items-center space-x-3">
        {/* Monday.com Sync Status */}
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-card border border-border text-xs">
          <Database className="w-3.5 h-3.5 text-accent-sky" />
          <span className="text-text-secondary text-[11px]">monday.com:</span>
          <span className={`font-mono-data text-[11px] font-medium ${isMondayLive ? 'text-accent-emerald' : 'text-accent-amber'}`}>
            {isMondayLive ? "Live API (v2)" : "Resilient Data Sandbox"}
          </span>
          <span className={`w-1.5 h-1.5 rounded-full ${isMondayLive ? 'bg-accent-emerald animate-pulse' : 'bg-accent-amber'}`} />
        </div>

        {/* LLM Status */}
        <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-card border border-border text-xs">
          <Cpu className="w-3.5 h-3.5 text-text-secondary" />
          <span className="text-text-secondary text-[11px]">Model:</span>
          <span className="font-mono-data text-[11px] text-text-primary">
            {health?.llm_provider?.configured ? "Groq (llama-3.3-70b)" : "Deterministic Ops Planner"}
          </span>
        </div>

        {/* Leadership Brief Action */}
        <button
          onClick={onOpenLeadership}
          className="px-3 py-1.5 rounded bg-accent-sky/10 hover:bg-accent-sky/20 border border-accent-sky/30 text-accent-sky text-xs font-medium transition-colors flex items-center space-x-1.5"
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Leadership Brief</span>
        </button>

        {/* Cache Refresh */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          title="Force refresh in-memory cache"
          className="p-1.5 rounded bg-card hover:bg-card-hover border border-border text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-accent-sky' : ''}`} />
        </button>
      </div>
    </header>
  );
};
