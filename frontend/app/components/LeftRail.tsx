"use client";

import React, { useEffect, useState } from "react";
import { 
  AlertTriangle, 
  BarChart2, 
  CheckCircle2, 
  Layers, 
  ShieldAlert, 
  TrendingUp, 
  Briefcase, 
  FileSpreadsheet,
  ChevronDown,
  ChevronRight,
  Info
} from "lucide-react";

interface LeftRailProps {
  selectedSector: string | null;
  onSelectSector: (sector: string | null) => void;
  onSelectPrompt: (prompt: string) => void;
  refreshTrigger: number;
}

export const LeftRail: React.FC<LeftRailProps> = ({
  selectedSector,
  onSelectSector,
  onSelectPrompt,
  refreshTrigger,
}) => {
  const [dataQuality, setDataQuality] = useState<any>(null);
  const [showCaveats, setShowCaveats] = useState(true);
  const [showFieldDetails, setShowFieldDetails] = useState(false);

  useEffect(() => {
    const fetchQuality = async () => {
      try {
        const res = await fetch("/api/data-quality");
        if (res.ok) {
          const data = await res.json();
          setDataQuality(data);
        }
      } catch (e) {
        console.warn("Could not fetch data quality metrics:", e);
      }
    };
    fetchQuality();
  }, [refreshTrigger]);

  const sectors = [
    { name: "All Sectors", value: null, count: "522 rows" },
    { name: "⚡ Energy Sector", value: "energy", count: "243 deals", highlight: true },
    { name: "Mining", value: "Mining", count: "106 deals · 100 WOs" },
    { name: "Renewables", value: "Renewables", count: "111 deals · 51 WOs" },
    { name: "Powerline", value: "Powerline", count: "26 deals · 6 WOs" },
    { name: "Railways", value: "Railways", count: "40 deals · 13 WOs" },
    { name: "Construction", value: "Construction", count: "9 deals · 2 WOs" },
    { name: "Tender / Others", value: "Others", count: "33 deals" },
  ];

  const dealsComp = dataQuality?.deals_board?.overall_completeness_pct || 61.2;
  const woComp = dataQuality?.work_orders_board?.overall_completeness_pct || 74.5;
  const dealsCols = dataQuality?.deals_board?.columns || {};
  const woCols = dataQuality?.work_orders_board?.columns || {};

  return (
    <aside className="w-64 border-r border-border bg-panel flex flex-col h-[calc(100vh-3.5rem)] overflow-y-auto select-none text-xs">
      
      {/* 1. SECTOR / SCOPE SELECTOR */}
      <div className="p-3.5 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-text-secondary text-[11px] uppercase tracking-wider flex items-center space-x-1.5">
            <Layers className="w-3.5 h-3.5 text-accent-sky" />
            <span>Sector Scope</span>
          </span>
          {selectedSector && (
            <button
              onClick={() => onSelectSector(null)}
              className="text-[10px] text-accent-sky hover:underline"
            >
              Reset
            </button>
          )}
        </div>

        <div className="space-y-1">
          {sectors.map((s) => {
            const isSelected = selectedSector === s.value;
            return (
              <button
                key={s.name}
                onClick={() => onSelectSector(s.value)}
                className={`w-full px-2.5 py-1.5 rounded flex items-center justify-between text-left transition-colors ${
                  isSelected
                    ? "bg-accent-sky/20 border border-accent-sky/40 text-accent-sky font-medium"
                    : s.highlight
                    ? "bg-card hover:bg-card-hover border border-accent-sky/20 text-text-primary"
                    : "hover:bg-card text-text-secondary hover:text-text-primary"
                }`}
              >
                <span className="truncate">{s.name}</span>
                <span className="font-mono-data text-[10px] text-text-muted shrink-0 ml-1">
                  {s.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. LIVE DATA QUALITY & COMPLETENESS STRIP (DATA RESILIENCE HERO) */}
      <div className="p-3.5 border-b border-border bg-[#0f141a]">
        <div className="flex items-center justify-between mb-2.5">
          <span className="font-semibold text-text-primary text-[11px] uppercase tracking-wider flex items-center space-x-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-accent-amber" />
            <span>Data Resilience</span>
          </span>
          <span className="px-1.5 py-0.5 rounded bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-[9px] font-mono-data font-medium">
            LIVE METRICS
          </span>
        </div>

        {/* Board Completeness Meters */}
        <div className="space-y-2.5 mb-3">
          {/* Deals Board */}
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-text-secondary flex items-center space-x-1">
                <Briefcase className="w-3 h-3 text-text-muted" />
                <span>Deals Board</span>
              </span>
              <span className="font-mono-data font-semibold text-text-primary">
                {dealsComp}%
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[#1c2128] overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  dealsComp > 70 ? "bg-accent-emerald" : "bg-accent-amber"
                }`}
                style={{ width: `${dealsComp}%` }}
              />
            </div>
          </div>

          {/* Work Orders Board */}
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-text-secondary flex items-center space-x-1">
                <FileSpreadsheet className="w-3 h-3 text-text-muted" />
                <span>Work Orders</span>
              </span>
              <span className="font-mono-data font-semibold text-text-primary">
                {woComp}%
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[#1c2128] overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  woComp > 70 ? "bg-accent-emerald" : "bg-accent-amber"
                }`}
                style={{ width: `${woComp}%` }}
              />
            </div>
          </div>
        </div>

        {/* Key Field Completeness Snapshot */}
        <button
          onClick={() => setShowFieldDetails(!showFieldDetails)}
          className="w-full flex items-center justify-between text-[10px] text-text-muted hover:text-text-secondary py-1 border-t border-border/50"
        >
          <span>Key Field Missing Rates</span>
          {showFieldDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>

        {showFieldDetails && (
          <div className="space-y-1.5 pt-1.5 font-mono-data text-[10px]">
            <div className="flex justify-between text-text-secondary">
              <span>Closure Probability:</span>
              <span className="text-accent-rose font-medium">74.6% blank</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Actual Close Date:</span>
              <span className="text-accent-rose font-medium">91.9% blank</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Deal Value:</span>
              <span className="text-accent-amber font-medium">52.3% blank</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>WO Collection Status:</span>
              <span className="text-accent-rose font-medium">100% blank</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>PO Quantities:</span>
              <span className="text-accent-emerald font-medium">90.9% populated</span>
            </div>
          </div>
        )}
      </div>

      {/* 3. ACTIVE DATA CAVEATS */}
      <div className="p-3.5 flex-1">
        <button
          onClick={() => setShowCaveats(!showCaveats)}
          className="w-full flex items-center justify-between font-semibold text-text-secondary text-[11px] uppercase tracking-wider mb-2"
        >
          <span className="flex items-center space-x-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-accent-amber" />
            <span>Active Caveats</span>
          </span>
          {showCaveats ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>

        {showCaveats && (
          <div className="space-y-2">
            <div className="p-2 rounded bg-card border border-border text-[11px] text-text-secondary space-y-1">
              <div className="flex items-center space-x-1 text-accent-amber font-medium text-[10px]">
                <Info className="w-3 h-3 shrink-0" />
                <span>Weighted Pipeline Caveat</span>
              </div>
              <p className="text-[10px] leading-relaxed text-text-muted">
                74.6% of deals lack closure probability. Weighted pipeline estimates are directional.
              </p>
            </div>

            <div className="p-2 rounded bg-card border border-border text-[11px] text-text-secondary space-y-1">
              <div className="flex items-center space-x-1 text-accent-sky font-medium text-[10px]">
                <CheckCircle2 className="w-3 h-3 shrink-0" />
                <span>5-to-1 Status Reconciliation</span>
              </div>
              <p className="text-[10px] leading-relaxed text-text-muted">
                Hierarchical resolution applied across Collection &gt; Billing &gt; WO &gt; Invoice &gt; Execution.
              </p>
            </div>

            <div className="p-2 rounded bg-card border border-border text-[11px] text-text-secondary space-y-1">
              <div className="flex items-center space-x-1 text-accent-amber font-medium text-[10px]">
                <AlertTriangle className="w-3 h-3 shrink-0" />
                <span>Join Key Asymmetry</span>
              </div>
              <p className="text-[10px] leading-relaxed text-text-muted">
                52 deals match cleanly; 102 pipeline deals have no work orders logged.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 4. QUICK PROMPT TRIGGER */}
      <div className="p-3 border-t border-border bg-card/40">
        <button
          onClick={() => onSelectPrompt("Audit data completeness and list all data resilience caveats across boards")}
          className="w-full px-2.5 py-1.5 rounded bg-card hover:bg-card-hover border border-border text-text-secondary hover:text-text-primary text-[10px] transition-colors flex items-center justify-center space-x-1"
        >
          <ShieldAlert className="w-3 h-3 text-accent-amber" />
          <span>Run Full Data Quality Audit</span>
        </button>
      </div>

    </aside>
  );
};
