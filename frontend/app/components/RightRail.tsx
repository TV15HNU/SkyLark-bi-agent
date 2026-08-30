"use client";

import React, { useState } from "react";
import { 
  BarChart2, 
  Briefcase, 
  FileSpreadsheet, 
  Layers, 
  ShieldCheck, 
  Pin, 
  Copy, 
  Check, 
  TrendingUp, 
  AlertCircle,
  ExternalLink,
  ChevronRight
} from "lucide-react";
import { PipelineCard, WorkOrdersCard, JoinInspectorCard, LeadershipDeckCard } from "./GenerativeCards";

interface RightRailProps {
  pinnedData: any;
  onSelectPrompt: (p: string) => void;
}

export const RightRail: React.FC<RightRailProps> = ({ pinnedData, onSelectPrompt }) => {
  const [activeTab, setActiveTab] = useState<"pinned" | "kpis" | "join" | "leadership">("pinned");
  const [copied, setCopied] = useState(false);

  return (
    <aside className="w-80 border-l border-border bg-panel flex flex-col h-[calc(100vh-3.5rem)] overflow-y-auto select-none text-xs hidden xl:flex">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center space-x-1.5 font-semibold text-text-primary text-[11px] uppercase tracking-wider">
          <Pin className="w-3.5 h-3.5 text-accent-sky" />
          <span>Pinned Intelligence</span>
        </div>
        <div className="flex space-x-1 p-0.5 rounded-md bg-card border border-border/80 font-mono-data text-[10px]">
          <button
            onClick={() => setActiveTab("pinned")}
            className={`px-2 py-0.5 rounded transition-all ${
              activeTab === "pinned" ? "bg-accent-sky text-panel font-semibold shadow-xs" : "text-text-muted hover:text-text-primary"
            }`}
          >
            Live
          </button>
          <button
            onClick={() => setActiveTab("leadership")}
            className={`px-2 py-0.5 rounded transition-all ${
              activeTab === "leadership" ? "bg-accent-sky text-panel font-semibold shadow-xs" : "text-text-muted hover:text-text-primary"
            }`}
          >
            Exec Deck
          </button>
          <button
            onClick={() => setActiveTab("join")}
            className={`px-2 py-0.5 rounded transition-all ${
              activeTab === "join" ? "bg-accent-sky text-panel font-semibold shadow-xs" : "text-text-muted hover:text-text-primary"
            }`}
          >
            Join
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="p-3 flex-1 overflow-y-auto space-y-3">
        {activeTab === "pinned" && (
          <div>
            {pinnedData ? (
              <div>
                <div className="text-[10px] text-text-secondary uppercase tracking-wider mb-1 font-semibold flex items-center justify-between">
                  <span>Active Query Widget</span>
                  <span className="font-mono-data text-accent-sky">PINNED</span>
                </div>
                {pinnedData.type === "pipeline_card" && <PipelineCard data={pinnedData.data} />}
                {pinnedData.type === "work_orders_card" && <WorkOrdersCard data={pinnedData.data} />}
                {pinnedData.type === "join_inspector" && <JoinInspectorCard data={pinnedData.data} />}
                {pinnedData.type === "leadership_deck" && <LeadershipDeckCard data={pinnedData.data} />}
              </div>
            ) : (
              <div className="p-4 rounded-lg border border-dashed border-border text-center space-y-2">
                <BarChart2 className="w-6 h-6 text-text-muted mx-auto" />
                <div className="font-medium text-text-secondary text-[11px]">No Active Widget Pinned</div>
                <p className="text-[10px] text-text-muted">
                  Ask a founder query in chat (or click a suggestion chip below) to pin live data models here.
                </p>
                <div className="pt-2 space-y-1">
                  <button
                    onClick={() => onSelectPrompt("How is our pipeline looking for energy sector this quarter?")}
                    className="w-full text-left p-1.5 rounded bg-card hover:bg-card-hover border border-border text-[10px] text-text-secondary truncate flex items-center justify-between"
                  >
                    <span>⚡ Energy Pipeline</span>
                    <ChevronRight className="w-3 h-3 shrink-0" />
                  </button>
                  <button
                    onClick={() => onSelectPrompt("Draft a Q3 leadership update for executive review")}
                    className="w-full text-left p-1.5 rounded bg-card hover:bg-card-hover border border-border text-[10px] text-text-secondary truncate flex items-center justify-between"
                  >
                    <span>🚁 Leadership Brief</span>
                    <ChevronRight className="w-3 h-3 shrink-0" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "leadership" && (
          <div className="space-y-2">
            <div className="text-[10px] text-text-secondary uppercase tracking-wider font-semibold">
              Executive Briefing Mode
            </div>
            <p className="text-[10px] text-text-muted leading-relaxed">
              1-click synthesized leadership deck aggregating pipeline, unbilled execution, accounts receivable, and top operational blockers.
            </p>
            <button
              onClick={() => onSelectPrompt("Draft a Q3 leadership update for executive review")}
              className="w-full py-2 px-3 rounded bg-accent-sky/20 hover:bg-accent-sky/30 border border-accent-sky/40 text-accent-sky font-medium text-xs flex items-center justify-center space-x-1.5 transition-colors"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Generate Fresh Deck</span>
            </button>
          </div>
        )}

        {activeTab === "join" && (
          <div className="space-y-2">
            <div className="text-[10px] text-text-secondary uppercase tracking-wider font-semibold">
              Cross-Board Reconciliation
            </div>
            <div className="p-2.5 rounded bg-card border border-border space-y-1.5">
              <div className="flex justify-between">
                <span className="text-text-secondary">Clean Matches:</span>
                <span className="font-mono-data text-accent-emerald font-bold">52 deals</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Pipeline-only (Won without WO):</span>
                <span className="font-mono-data text-accent-amber font-bold">113 deals</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Orphaned WOs:</span>
                <span className="font-mono-data text-accent-rose font-bold">6 WOs</span>
              </div>
            </div>
            <button
              onClick={() => onSelectPrompt("Which deals are won in pipeline but have no corresponding work order logged?")}
              className="w-full py-1.5 px-2 rounded bg-card hover:bg-card-hover border border-border text-text-primary text-[10px] flex items-center justify-center space-x-1 transition-colors"
            >
              <Layers className="w-3 h-3 text-accent-sky" />
              <span>Inspect Unconverted Deals</span>
            </button>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-border bg-[#0f141a] text-[10px] text-text-muted space-y-1 font-mono-data">
        <div className="flex justify-between">
          <span>Deals Board ID:</span>
          <span>{process.env.DEALS_BOARD_ID || "live_board_A"}</span>
        </div>
        <div className="flex justify-between">
          <span>WO Board ID:</span>
          <span>{process.env.WORK_ORDERS_BOARD_ID || "live_board_B"}</span>
        </div>
      </div>
    </aside>
  );
};
