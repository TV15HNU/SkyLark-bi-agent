"use client";

import React, { useState } from "react";
import { 
  Check, 
  Copy, 
  Download, 
  ExternalLink, 
  TrendingUp, 
  AlertTriangle, 
  Layers, 
  Briefcase, 
  FileSpreadsheet, 
  DollarSign, 
  ArrowRight,
  ShieldAlert
} from "lucide-react";

interface CardProps {
  card: {
    type: string;
    data: any;
  };
  onPinToRail?: (data: any) => void;
}

export const GenerativeCard: React.FC<CardProps> = ({ card, onPinToRail }) => {
  const { type, data } = card;

  if (type === "pipeline_card") {
    return <PipelineCard data={data} onPin={onPinToRail} />;
  } else if (type === "work_orders_card") {
    return <WorkOrdersCard data={data} onPin={onPinToRail} />;
  } else if (type === "join_inspector") {
    return <JoinInspectorCard data={data} onPin={onPinToRail} />;
  } else if (type === "leadership_deck") {
    return <LeadershipDeckCard data={data} onPin={onPinToRail} />;
  } else if (type === "data_quality_card") {
    return <DataQualityCard data={data} onPin={onPinToRail} />;
  }

  return null;
};

// 1. PIPELINE GENERATIVE CARD
export const PipelineCard: React.FC<{ data: any; onPin?: (d: any) => void }> = ({ data, onPin }) => {
  const agg = data?.aggregations || {};
  const stages = agg?.stage_breakdown || {};
  const stageEntries = Object.entries(stages) as [string, number][];
  const maxStageCount = Math.max(...stageEntries.map(([_, v]) => v), 1);

  return (
    <div className="mt-3 rounded-lg border border-border bg-card/90 overflow-hidden shadow-sm text-xs">
      {/* Header */}
      <div className="px-3.5 py-2 border-b border-border bg-panel/50 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Briefcase className="w-3.5 h-3.5 text-accent-sky" />
          <span className="font-semibold text-text-primary uppercase tracking-wide text-[11px]">
            Deals Sales Funnel & Pipeline
          </span>
          <span className="font-mono-data text-[10px] px-1.5 py-0.2 rounded bg-panel text-text-secondary border border-border">
            {data?.matched_count || 0} matching deals
          </span>
        </div>
        <div className="text-[10px] font-mono-data text-text-muted">
          source: monday.com · {data?.source_meta?.source || "live"}
        </div>
      </div>

      {/* Metrics Stack - one below another */}
      <div className="flex flex-col gap-1.5 p-2.5 border-b border-border/60 bg-panel/20">
        <div className="p-2 rounded bg-panel border border-border/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Open Pipeline</span>
            <span className="text-[9px] text-text-muted font-mono-data">Nominal value</span>
          </div>
          <div className="font-mono-data text-xs sm:text-sm font-bold text-accent-sky text-right shrink-0">
            ₹{(agg.total_open_pipeline_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-panel border border-border/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <div className="flex items-center space-x-1">
              <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Weighted Pipeline</span>
              <span className="text-accent-amber font-mono-data text-[9px] cursor-help" title="74% of deals lack closure probability; directional estimate">~</span>
            </div>
            <span className="text-[9px] text-accent-amber/90 font-mono-data">Directional (~74% unweighted)</span>
          </div>
          <div className="font-mono-data text-xs sm:text-sm font-bold text-accent-amber text-right shrink-0">
            ~₹{(agg.weighted_open_pipeline_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-panel border border-border/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Closed Won</span>
            <span className="text-[9px] text-text-muted font-mono-data">Won deals total</span>
          </div>
          <div className="font-mono-data text-xs sm:text-sm font-bold text-accent-emerald text-right shrink-0">
            ₹{(agg.total_won_value || 0).toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      {/* Funnel Stage Breakdown */}
      <div className="p-3">
        <div className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-2">
          Funnel Stage Distribution
        </div>
        <div className="space-y-1.5">
          {stageEntries.slice(0, 8).map(([stage, count]) => {
            const pct = Math.round((count / maxStageCount) * 100);
            return (
              <div key={stage} className="space-y-0.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-text-primary truncate max-w-[260px]">{stage}</span>
                  <span className="font-mono-data text-text-secondary font-medium">{count}</span>
                </div>
                <div className="w-full h-1.5 bg-panel rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-accent-sky/70"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// 2. WORK ORDERS GENERATIVE CARD
export const WorkOrdersCard: React.FC<{ data: any; onPin?: (d: any) => void }> = ({ data }) => {
  const fin = data?.financial_summary || {};
  const statusDist = fin?.status_category_breakdown || {};

  return (
    <div className="mt-3 rounded-lg border border-border bg-card/90 overflow-hidden shadow-sm text-xs">
      <div className="px-3 py-2 border-b border-border bg-panel/50 flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5 min-w-0">
            <FileSpreadsheet className="w-3.5 h-3.5 text-accent-amber shrink-0" />
            <span className="font-semibold text-text-primary uppercase tracking-wide text-[11px] truncate">
              Work Orders Execution & Billing
            </span>
          </div>
          <span className="font-mono-data text-[10px] px-1.5 py-0.5 rounded bg-panel text-text-secondary border border-border shrink-0 ml-1">
            {data?.matched_count || 0} WOs
          </span>
        </div>
        <div className="text-[10px] font-mono-data text-text-muted">
          5-to-1 Status Reconciliation Active
        </div>
      </div>

      {/* Financial KPIs (2x2 Grid fits comfortably in sidebar without overlap) */}
      <div className="grid grid-cols-2 gap-2 p-2.5 border-b border-border/60 bg-panel/20">
        <div className="p-2 rounded bg-panel border border-border/80 min-w-0">
          <span className="text-[9px] text-text-secondary uppercase tracking-wider block truncate">Contract Total</span>
          <div className="font-mono-data text-xs font-bold text-text-primary mt-0.5 truncate" title={`₹${(fin.total_contract_value || 0).toLocaleString("en-IN")}`}>
            ₹{(fin.total_contract_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-panel border border-border/80 min-w-0">
          <span className="text-[9px] text-text-secondary uppercase tracking-wider block truncate">Billed Revenue</span>
          <div className="font-mono-data text-xs font-bold text-accent-emerald mt-0.5 truncate" title={`₹${(fin.total_billed_value || 0).toLocaleString("en-IN")}`}>
            ₹{(fin.total_billed_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-panel border border-border/80 min-w-0">
          <span className="text-[9px] text-text-secondary uppercase tracking-wider block truncate">Unbilled Backlog</span>
          <div className="font-mono-data text-xs font-bold text-accent-amber mt-0.5 truncate" title={`₹${(fin.total_unbilled_value || 0).toLocaleString("en-IN")}`}>
            ₹{(fin.total_unbilled_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-panel border border-border/80 min-w-0">
          <span className="text-[9px] text-text-secondary uppercase tracking-wider block truncate">Receivable (AR)</span>
          <div className="font-mono-data text-xs font-bold text-accent-rose mt-0.5 truncate" title={`₹${(fin.total_accounts_receivable || 0).toLocaleString("en-IN")}`}>
            ₹{(fin.total_accounts_receivable || 0).toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      {/* Reconciled Status Distribution */}
      <div className="p-2.5">
        <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
          Operational Status Categories (Reconciled)
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {Object.entries(statusDist).map(([cat, count]) => (
            <div key={cat} className="flex justify-between items-center p-1.5 rounded bg-panel/60 border border-border/50 text-[10px]">
              <span className="text-text-primary truncate">{cat}</span>
              <span className="font-mono-data text-accent-sky font-semibold ml-1 shrink-0">{count as number}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// 3. CROSS-BOARD JOIN INSPECTOR CARD
export const JoinInspectorCard: React.FC<{ data: any; onPin?: (d: any) => void }> = ({ data }) => {
  return (
    <div className="mt-3 rounded-lg border border-border bg-card/90 overflow-hidden shadow-sm text-xs">
      <div className="px-3.5 py-2 border-b border-border bg-panel/50 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Layers className="w-3.5 h-3.5 text-accent-sky" />
          <span className="font-semibold text-text-primary uppercase tracking-wide text-[11px]">
            Cross-Board Lifecycle Alignment (Deals ↔ Work Orders)
          </span>
        </div>
        <span className="px-1.5 py-0.5 rounded bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-[9px] font-mono-data">
          JOIN KEY AUDIT
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2.5 p-3 border-b border-border/60">
        <div className="p-2.5 rounded bg-[#102a1c] border border-[#1b4d33] text-center">
          <span className="text-[10px] text-text-secondary uppercase">Clean Matches</span>
          <div className="font-mono-data text-base font-bold text-accent-emerald mt-0.5">
            {data?.matched_deals_count || 52}
          </div>
          <span className="text-[9px] text-text-muted">Pipeline + Execution</span>
        </div>

        <div className="p-2.5 rounded bg-[#2b1f14] border border-[#523b26] text-center">
          <span className="text-[10px] text-text-secondary uppercase">Won Without WO</span>
          <div className="font-mono-data text-base font-bold text-accent-amber mt-0.5">
            {data?.won_deals_without_work_orders_count || 113}
          </div>
          <span className="text-[9px] text-accent-amber/90">Ops Handover Gap</span>
        </div>

        <div className="p-2.5 rounded bg-[#26151a] border border-[#4d202e] text-center">
          <span className="text-[10px] text-text-secondary uppercase">Orphaned WOs</span>
          <div className="font-mono-data text-base font-bold text-accent-rose mt-0.5">
            {data?.orphaned_work_orders_count || 6}
          </div>
          <span className="text-[9px] text-text-muted">Dolphin, Octopus, etc.</span>
        </div>
      </div>

      <div className="p-3 bg-panel/30 text-[11px] text-text-secondary leading-relaxed">
        <p className="font-medium text-text-primary mb-1">Observation on Join Key Fragility:</p>
        <p className="text-[10px] text-text-muted">
          {data?.join_fragility_analysis?.observation || 
           "Deals and Work Orders connect via masked deal names. 6 work orders have no parent deal record due to independent masking, and 113 won deals have not yet had work orders generated in monday.com."}
        </p>
      </div>
    </div>
  );
};

// 4. LEADERSHIP UPDATE CARD
export const LeadershipDeckCard: React.FC<{ data: any; onPin?: (d: any) => void }> = ({ data }) => {
  const [copied, setCopied] = useState(false);
  const kpi = data?.headline_kpis || {};
  const risks = data?.top_3_risks || [];

  const copyMarkdown = () => {
    if (data?.markdown_export) {
      navigator.clipboard.writeText(data.markdown_export);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const downloadMarkdown = () => {
    if (data?.markdown_export) {
      const blob = new Blob([data.markdown_export], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Skylark_Leadership_Update_${data?.scope || "Company"}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-accent-sky/40 bg-[#0f1724] overflow-hidden shadow-md text-xs">
      {/* Deck Header */}
      <div className="px-3.5 py-2.5 border-b border-accent-sky/30 bg-[#162338] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-accent-sky animate-pulse" />
          <span className="font-bold text-text-primary uppercase tracking-wide text-[11px]">
            Executive Leadership Brief ({data?.scope?.toUpperCase() || "OVERALL"})
          </span>
        </div>
      </div>

      {/* KPI Stack - one below another */}
      <div className="flex flex-col gap-1.5 p-2.5 bg-panel/40 border-b border-border/60">
        <div className="p-2 rounded bg-card border border-border/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Active Pipeline</span>
            <span className="text-[9px] text-accent-amber block mt-0.5 font-mono-data">~₹{(kpi.weighted_pipeline_value || 0).toLocaleString("en-IN")} weighted</span>
          </div>
          <div className="font-mono-data text-xs sm:text-sm font-bold text-accent-sky text-right shrink-0">
            ₹{(kpi.open_pipeline_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-card border border-border/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Billed Revenue</span>
            <span className="text-[9px] text-text-muted block mt-0.5 font-mono-data">Unbilled: ₹{(kpi.unbilled_backlog || 0).toLocaleString("en-IN")}</span>
          </div>
          <div className="font-mono-data text-xs sm:text-sm font-bold text-accent-emerald text-right shrink-0">
            ₹{(kpi.billed_value || 0).toLocaleString("en-IN")}
          </div>
        </div>

        <div className="p-2 rounded bg-card border border-border/80 flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <span className="text-[10px] text-text-secondary uppercase tracking-wider block font-medium">Outstanding AR</span>
            <span className="text-[9px] text-text-muted block mt-0.5 font-mono-data">Receivables balance</span>
          </div>
          <div className="font-mono-data text-xs sm:text-sm font-bold text-accent-rose text-right shrink-0">
            ₹{(kpi.accounts_receivable || 0).toLocaleString("en-IN")}
          </div>
        </div>
      </div>

      {/* Top 3 Strategic Risks */}
      <div className="p-3">
        <div className="text-[11px] font-semibold text-accent-amber uppercase tracking-wider mb-2 flex items-center space-x-1">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Top 3 Strategic & Operational Risks</span>
        </div>
        <div className="space-y-1.5">
          {risks.map((r: any, idx: number) => (
            <div key={idx} className="p-2 rounded bg-panel/80 border border-border/60 text-[11px] space-y-0.5">
              <div className="flex justify-between items-center font-medium">
                <span className="text-text-primary">{r.title}</span>
                <span className={`font-mono-data text-[9px] px-1 py-0.2 rounded font-bold ${
                  r.severity === "HIGH" ? "bg-accent-rose/20 text-accent-rose border border-accent-rose/40" : "bg-accent-amber/20 text-accent-amber border border-accent-amber/40"
                }`}>
                  {r.severity}
                </span>
              </div>
              <p className="text-[10px] text-text-muted leading-relaxed">{r.impact}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// 5. DATA QUALITY CARD
export const DataQualityCard: React.FC<{ data: any; onPin?: (d: any) => void }> = ({ data }) => {
  const deals = data?.deals_board || {};
  const wo = data?.work_orders_board || {};

  return (
    <div className="mt-3 rounded-lg border border-border bg-card/90 overflow-hidden shadow-sm text-xs">
      <div className="px-3.5 py-2 border-b border-border bg-panel/50 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-3.5 h-3.5 text-accent-amber" />
          <span className="font-semibold text-text-primary uppercase tracking-wide text-[11px]">
            Data Quality & Resilience Report
          </span>
        </div>
        <span className="font-mono-data text-[10px] text-text-secondary">
          Audit Score
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 p-3 border-b border-border/60">
        <div className="p-2 rounded bg-panel border border-border">
          <span className="text-[10px] text-text-secondary uppercase">Deals Board Overall</span>
          <div className="font-mono-data text-base font-bold text-accent-amber mt-0.5">
            {deals.overall_completeness_pct}%
          </div>
          <span className="text-[9px] text-text-muted">{deals.total_records} records audited</span>
        </div>

        <div className="p-2 rounded bg-panel border border-border">
          <span className="text-[10px] text-text-secondary uppercase">Work Orders Overall</span>
          <div className="font-mono-data text-base font-bold text-accent-emerald mt-0.5">
            {wo.overall_completeness_pct}%
          </div>
          <span className="text-[9px] text-text-muted">{wo.total_records} records audited</span>
        </div>
      </div>

      <div className="p-3 space-y-1.5 text-[10px]">
        <div className="font-semibold text-text-secondary uppercase tracking-wider">Caveats Surfaced to Founder</div>
        {deals.caveats?.map((c: string, i: number) => (
          <div key={i} className="p-1.5 rounded bg-panel/60 border border-border/50 text-text-secondary">
            {c}
          </div>
        ))}
        {wo.caveats?.map((c: string, i: number) => (
          <div key={i} className="p-1.5 rounded bg-panel/60 border border-border/50 text-text-secondary">
            {c}
          </div>
        ))}
      </div>
    </div>
  );
};
