import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI
from app.config import settings
from app.json_utils import sanitize_for_json
from app.normalizer import resolve_sector_filter, format_inr
from app.tools import (
    get_deals,
    get_work_orders,
    join_deals_and_work_orders,
    get_data_quality_summary,
    draft_leadership_update,
)

logger = logging.getLogger("agent")

# Define JSON Schema for tools
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_deals",
            "description": "Queries deals sales pipeline on monday.com with filtering on sector, deal status, deal stage, owner code, or date range. Returns deal metrics, pipeline value, stage funnel breakdown, and data-quality caveats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sectors to filter by (e.g. ['Mining', 'Renewables', 'Powerline', 'Railways', 'Construction', 'Tender', 'Others']). Accepts macro terms like 'energy' which will expand to Mining and Renewables."
                    },
                    "statuses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Deal statuses to filter by (e.g. ['Open', 'Won', 'Dead', 'On Hold'])."
                    },
                    "stages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Stages to filter by (e.g. ['A. Lead Generated', 'E. Proposal/Commercials Sent', 'G. Project Won', 'H. Work Order Received'])."
                    },
                    "owners": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Owner codes to filter by (e.g. ['OWNER_001', 'OWNER_002'])."
                    },
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "Start date in YYYY-MM-DD"},
                            "end": {"type": "string", "description": "End date in YYYY-MM-DD"}
                        }
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_orders",
            "description": "Queries work orders project execution data from monday.com. Reconciles 5 overlapping status columns into authoritative status. Returns contract value, billed amounts, unbilled backlog, and accounts receivable (AR).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sectors to filter by (e.g. ['Mining', 'Renewables', 'Railways', 'Powerline', 'Construction'])."
                    },
                    "execution_statuses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Execution statuses (e.g. ['Completed', 'Ongoing', 'Not Started', 'Paused / Stuck'])."
                    },
                    "billing_statuses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Reconciled billing status categories (e.g. ['Fully Billed', 'Partially Billed', 'Attention Required', 'Active Execution', 'Stuck / Blocked'])."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "join_deals_and_work_orders",
            "description": "Performs cross-board reconciliation between Deals (sales pipeline) and Work Orders (execution). Identifies matched projects, won deals missing work orders, and orphaned work orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "deal_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific deal names to inspect cross-board."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality_summary",
            "description": "Returns completeness percentage for all key columns across Deals and Work Orders boards, including data resilience caveats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board": {
                        "type": "string",
                        "enum": ["deals", "work_orders", "all"],
                        "description": "Board to inspect."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "draft_leadership_update",
            "description": "Generates a structured founder-level leadership update covering headline KPIs, top 3 risks/blockers, sector performance, and a 1-click exportable Markdown report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Scope of the report (e.g. 'overall', 'Mining', 'Renewables', 'Powerline', 'Railways')."
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period (e.g. 'Current Quarter', 'Q3 2026', 'YTD')."
                    }
                }
            }
        }
    }
]

SYSTEM_PROMPT = """You are the Skylark Drones Business Intelligence Agent — an elite, ops-minded analyst answering founder-level strategic and operational questions by querying live monday.com boards (Deals Pipeline and Work Orders Tracker).

You have access to typed tools to query live data. Follow these strict guidelines:
1. **Resolve Scope**: Resolve vague terms like "this quarter" against current date (2026-Q3 / current year) and macro or compound sectors (e.g. "energy" -> Mining + Renewables + Powerline; "Railways + Powerline" -> ['Railways', 'Powerline']) when calling tools.
2. **Strict Currency Symbol**: ALWAYS format monetary values in Indian Rupees with the symbol **₹** (INR) — NEVER use '¥', '$', or any other symbol. For example: `₹58.35 M` or `₹5.83 Cr (₹58,348,766.20)`.
3. **Never Fabricate or Zero-Out**: Every single metric, currency amount, count, and status must trace directly to a tool output. If tools return non-zero numbers, use the exact figures. Never hallucinate or output zero when data exists.
4. **Data Resilience & Caveats**: If a metric is derived from incomplete data (e.g. 74% missing closure probability, unpopulated collection dates), you MUST explicitly state the caveat to the founder (e.g., "Heads up: weighted pipeline is directional because 74% of deals lack closure probability").
5. **Ops Analyst Voice & Professional Formatting**: Speak like a crisp, high-conviction Chief of Staff / Head of Ops. Use clean markdown tables, bold KPI figures, and highlight actionable risks (e.g. unbilled amounts, stalled deals, won deals with no work order).
6. **Cross-Board Reasoning**: When asked about full lifecycle or handover health, query both boards and use `join_deals_and_work_orders` to highlight pipeline-to-execution gaps.
"""

async def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes backend tool by name and arguments."""
    if tool_name == "get_deals":
        return await get_deals(**arguments)
    elif tool_name == "get_work_orders":
        return await get_work_orders(**arguments)
    elif tool_name == "join_deals_and_work_orders":
        return await join_deals_and_work_orders(**arguments)
    elif tool_name == "get_data_quality_summary":
        return await get_data_quality_summary(**arguments)
    elif tool_name == "draft_leadership_update":
        return await draft_leadership_update(**arguments)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

class BIAgent:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = settings.GROQ_BASE_URL
        self.model = settings.GROQ_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key or "mock-key", base_url=self.base_url) if self.api_key else None

    async def run_deterministic_query(self, user_query: str) -> Dict[str, Any]:
        """
        High-accuracy fallback planner for founder queries when no Groq API key is configured.
        """
        q_lower = user_query.lower()
        traces = []
        ui_cards = []
        caveats = []
        answer = ""

        # 0. Greetings / Intro intent
        greeting_words = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "help", "who are you", "what can you do"]
        if q_lower.strip() in greeting_words or any(q_lower.strip().startswith(g) for g in ["hi ", "hello ", "hey "]):
            answer = "👋 **Hello! I am your Skylark Business Intelligence Agent.**\n\n" \
                     "I connect directly to your live **monday.com** boards (*Deals Funnel* & *Work Orders Tracker*) to answer founder-level strategic and operational questions.\n\n" \
                     "**Try asking me:**\n" \
                     "- *\"How is our sales pipeline looking for the energy sector this quarter?\"*\n" \
                     "- *\"What is our total unbilled amount and collection risk across ongoing work orders?\"*\n" \
                     "- *\"Which deals are won in pipeline but have no work order created?\"*\n" \
                     "- *\"Draft a comprehensive Q3 leadership update with top 3 strategic risks\"*\n" \
                     "- *\"Show data completeness and quality audit across both boards\"*"
            return sanitize_for_json({
                "answer": answer,
                "reasoning_traces": ["⚡ Conversational prompt received → Providing Ops Analyst overview & suggested queries"],
                "ui_cards": [],
                "caveats": [],
                "grounding_valid": True
            })

        # 1. Leadership Update intent
        if any(k in q_lower for k in ["leadership", "executive brief", "executive update", "draft update", "leadership update", "briefing", "snapshot"]):
            traces.append("⚡ Planning: Identified Leadership Brief request → Executing draft_leadership_update")
            matched_sectors = []
            for s in ["railways", "railway", "powerline", "power", "mining", "renewable", "renewables", "solar", "wind", "construction", "tender", "energy"]:
                if s in q_lower:
                    matched_sectors.append(s)
            scope = " + ".join(matched_sectors) if matched_sectors else "overall"
            res = await draft_leadership_update(scope=scope, period="Current Quarter")
            resolved_scope_label = ", ".join(resolve_sector_filter([scope])) if scope != "overall" else "Overall Company"
            traces.append(f"✓ Fetched KPIs: Pipeline ₹{res['headline_kpis']['open_pipeline_value']:,.0f} · Billed Revenue ₹{res['headline_kpis']['billed_value']:,.0f}")
            
            ui_cards.append({
                "type": "leadership_deck",
                "data": res
            })
            
            answer = f"### 🚁 Executive Leadership Brief ({resolved_scope_label} · Current Quarter)\n\n" \
                     f"- **Active Pipeline:** **₹{res['headline_kpis']['open_pipeline_value']:,.2f}** (Directional weighted: ~₹{res['headline_kpis']['weighted_pipeline_value']:,.2f})\n" \
                     f"- **Closed Won Deals:** **₹{res['headline_kpis']['won_value']:,.2f}**\n" \
                     f"- **Execution Contract Total:** **₹{res['headline_kpis']['contract_value']:,.2f}**\n" \
                     f"- **Billed Revenue:** **₹{res['headline_kpis']['billed_value']:,.2f}** *(Unbilled backlog: ₹{res['headline_kpis']['unbilled_backlog']:,.2f})*\n" \
                     f"- **Outstanding Accounts Receivable (AR):** **₹{res['headline_kpis']['accounts_receivable']:,.2f}**\n\n" \
                     f"**Top 3 Operational Risks Identified:**\n" \
                     f"1. **{res['top_3_risks'][0]['title']} ({res['top_3_risks'][0]['severity']})**: {res['top_3_risks'][0]['impact']}\n" \
                     f"2. **{res['top_3_risks'][1]['title']} ({res['top_3_risks'][1]['severity']})**: {res['top_3_risks'][1]['impact']}\n" \
                     f"3. **{res['top_3_risks'][2]['title']} ({res['top_3_risks'][2]['severity']})**: {res['top_3_risks'][2]['impact']}\n\n" \
                     f"*(You can copy the complete formatted Markdown summary from the Pinned Intelligence panel on the right).* "

            caveats.extend(res["data_quality_caveats"])

        # 2. Cross-board join / Handover / Missing WO intent
        elif any(k in q_lower for k in ["join", "cross-board", "cross board", "handover", "without work order", "no work order", "missing work order", "orphaned", "won but", "won without"]):
            traces.append("⚡ Planning: Cross-board join query → Executing join_deals_and_work_orders")
            res = await join_deals_and_work_orders()
            traces.append(f"✓ Join results: {res['matched_deals_count']} matched · {res['won_deals_without_work_orders_count']} won deals without WO · {res['orphaned_work_orders_count']} orphaned WOs")

            ui_cards.append({
                "type": "join_inspector",
                "data": res
            })

            answer = f"### 🔗 Cross-Board Lifecycle Analysis (Deals ↔ Work Orders)\n\n" \
                     f"- **Matched Deals with Active Execution:** **{res['matched_deals_count']} deals**\n" \
                     f"- **Deals in Pipeline without Work Orders:** **{res['deals_without_work_orders_count']} deals** (of which **{res['won_deals_without_work_orders_count']} are marked 'Won'** and need operations setup)\n" \
                     f"- **Orphaned Work Orders (No matching Deal):** **{res['orphaned_work_orders_count']} work orders** *(Masked keys: Dolphin, Octopus, Golden fish, Turtle, Whale, GG go)*\n\n" \
                     f"**Key Finding:** There is a significant operational handover backlog where won deals have not been converted into tracked work orders."

            caveats.append("Data Resilience: Join keys between Boards A and B are separately masked names, creating non-1:1 asymmetry.")

        # 3. Data Quality summary intent
        elif any(k in q_lower for k in ["data quality", "completeness", "missing rate", "caveat", "audit", "data resilience"]):
            traces.append("⚡ Planning: Data Quality Audit → Executing get_data_quality_summary")
            res = await get_data_quality_summary()
            traces.append(f"✓ Deals board: {res['deals_board']['overall_completeness_pct']}% · Work Orders board: {res['work_orders_board']['overall_completeness_pct']}%")

            ui_cards.append({
                "type": "data_quality_card",
                "data": res
            })

            answer = f"### 🛡️ Data Quality & Field Completeness Audit\n\n" \
                     f"- **Deals Board Overall Completeness:** **{res['deals_board']['overall_completeness_pct']}%** ({res['deals_board']['total_records']} total records)\n" \
                     f"- **Work Orders Overall Completeness:** **{res['work_orders_board']['overall_completeness_pct']}%** ({res['work_orders_board']['total_records']} total records)\n\n" \
                     f"**Critical Caveats:**\n"
            for c in res['deals_board']['caveats'] + res['work_orders_board']['caveats']:
                answer += f"- {c}\n"

        # 4. Work Orders / Billing / Collection / Unbilled intent
        elif any(k in q_lower for k in ["work order", "unbilled", "billing", "collection", "receivable", "invoicing", "execution status"]) or re.search(r"\bar\b", q_lower):
            sectors = []
            if "mining" in q_lower: sectors.append("Mining")
            if "renewable" in q_lower: sectors.append("Renewables")
            if "power" in q_lower: sectors.append("Powerline")
            if "railway" in q_lower: sectors.append("Railways")
            if "energy" in q_lower: sectors.extend(["Mining", "Renewables", "Powerline"])

            traces.append(f"⚡ Planning: Querying Work Orders execution tracker · sectors: {sectors or 'All'}")
            res = await get_work_orders(sectors=sectors if sectors else None)
            fin = res["financial_summary"]
            traces.append(f"✓ Analyzed {res['matched_count']} work orders · Contract Value: ₹{fin['total_contract_value']:,.0f}")

            ui_cards.append({
                "type": "work_orders_card",
                "data": res
            })

            answer = f"### ⚙️ Work Orders Execution & Invoicing Health\n\n" \
                     f"- **Total Contract Value:** **₹{fin['total_contract_value']:,.2f}** across {res['matched_count']} work orders\n" \
                     f"- **Billed Revenue:** **₹{fin['total_billed_value']:,.2f}**\n" \
                     f"- **Unbilled Amount to be Billed:** **₹{fin['total_unbilled_value']:,.2f}**\n" \
                     f"- **Outstanding Accounts Receivable (AR):** **₹{fin['total_accounts_receivable']:,.2f}**\n\n" \
                     f"**Status Reconciliation Breakdown (5-to-1 Authority):**\n"
            for cat, count in fin["status_category_breakdown"].items():
                answer += f"- **{cat}:** {count} work orders\n"

            caveats.extend(res["data_quality_notes"])

        # 5. Sector Ranking / Profitability / Top Revenue comparison intent
        elif any(k in q_lower for k in ["profit", "most profit", "highest revenue", "top revenue", "top sector", "best sector", "leading sector", "rank sector", "sector ranking", "compare sector", "which sector"]):
            traces.append("⚡ Planning: Sector Ranking & Financial Performance Query → Aggregating Deals and Work Orders across all sectors")
            deals_res = await get_deals()
            wo_res = await get_work_orders()

            deals_sec = deals_res["aggregations"]["sector_breakdown"]
            wo_sec = wo_res["financial_summary"]["sector_financials"]

            # Merge sector data
            all_sectors = sorted(list(set(list(deals_sec.keys()) + list(wo_sec.keys()))))
            leaderboard = []

            for sec in all_sectors:
                d_info = deals_sec.get(sec, {"count": 0, "open_value": 0.0, "won_value": 0.0})
                w_info = wo_sec.get(sec, {"count": 0, "contract_val": 0.0, "billed_val": 0.0, "unbilled_val": 0.0, "receivable_val": 0.0})
                
                leaderboard.append({
                    "sector": sec,
                    "billed_revenue": w_info["billed_val"],
                    "contract_value": w_info["contract_val"],
                    "closed_won": d_info["won_value"],
                    "open_pipeline": d_info["open_value"],
                    "wo_count": w_info["count"],
                    "deal_count": d_info["count"]
                })

            # Sort by Billed Revenue (realized top-line) descending
            leaderboard_by_billed = sorted(leaderboard, key=lambda x: x["billed_revenue"], reverse=True)
            top_billed = leaderboard_by_billed[0]

            # Sort by Closed-Won Sales
            leaderboard_by_won = sorted(leaderboard, key=lambda x: x["closed_won"], reverse=True)
            top_won = leaderboard_by_won[0]

            traces.append(f"✓ Ranked {len(leaderboard)} sectors · Top Billed: {top_billed['sector']} (₹{top_billed['billed_revenue']:,.0f}) · Top Won: {top_won['sector']} (₹{top_won['closed_won']:,.0f})")

            answer = f"### 🏆 Sector Financial Performance & Revenue Ranking\n\n" \
                     f"**Key Findings:**\n" \
                     f"- 🥇 **#1 Top Revenue Generating Sector (Billed Cash Flow):** **{top_billed['sector']}** with **₹{top_billed['billed_revenue']:,.2f}** billed ({top_billed['billed_revenue'] / (top_billed['contract_value'] or 1) * 100:.1f}% of its ₹{top_billed['contract_value']:,.2f} contract value realized across {top_billed['wo_count']} work orders).\n" \
                     f"- 🥈 **#2 Billed Revenue Sector:** **{leaderboard_by_billed[1]['sector']}** with **₹{leaderboard_by_billed[1]['billed_revenue']:,.2f}** billed.\n" \
                     f"- 🎯 **#1 Top Closed-Won Sales Sector:** **{top_won['sector']}** with **₹{top_won['closed_won']:,.2f}** in closed contracts.\n\n" \
                     f"**Sector Financial Leaderboard:**\n\n" \
                     f"| Sector | Billed Revenue (Realized) | Contract Value | Closed Won (Sales) | Active Pipeline |\n" \
                     f"| :--- | :--- | :--- | :--- | :--- |\n"

            for item in leaderboard_by_billed:
                if item["billed_revenue"] > 0 or item["closed_won"] > 0 or item["open_pipeline"] > 0:
                    answer += f"| **{item['sector']}** | **₹{item['billed_revenue']:,.2f}** | ₹{item['contract_value']:,.2f} | ₹{item['closed_won']:,.2f} | ₹{item['open_pipeline']:,.2f} |\n"

            answer += f"\n> **Note on Profitability Metric:** Monday.com operational tracking records top-line **Billed Revenue**, **Contract Value**, and **Deal Size**. Internal cost/EBITDA margins are not stored in these boards, so financial leadership is measured by realized billed revenue and closed contract value."

            ui_cards.append({
                "type": "work_orders_card",
                "data": wo_res
            })

            caveats.append("Financial Scope Notice: Rankings reflect top-line Billed Revenue and Closed Deal Value as internal project profit margins are not tracked in Monday.com.")

        # 6. Deals / Pipeline / Default intent (e.g. "How's our pipeline looking for energy sector this quarter?")
        else:
            sectors = []
            if "energy" in q_lower:
                sectors = ["Mining", "Renewables", "Powerline"]
                traces.append("⚡ Resolving taxonomy: 'energy sector' → Mining, Renewables, Powerline")
            elif "mining" in q_lower:
                sectors = ["Mining"]
            elif "renewable" in q_lower:
                sectors = ["Renewables"]
            elif "power" in q_lower:
                sectors = ["Powerline"]
            elif "railway" in q_lower:
                sectors = ["Railways"]
            elif "construction" in q_lower:
                sectors = ["Construction"]

            traces.append(f"⚡ Planning: Querying Deals Pipeline · sectors={sectors or 'All'}")
            res = await get_deals(sectors=sectors if sectors else None)
            agg = res["aggregations"]
            traces.append(f"✓ Found {res['matched_count']} matching deals · Open pipeline: ₹{agg['total_open_pipeline_value']:,.0f}")

            ui_cards.append({
                "type": "pipeline_card",
                "data": res
            })

            sector_label = ", ".join(sectors) if sectors else "All Sectors"
            answer = f"### 📊 Sales Pipeline Analysis ({sector_label})\n\n" \
                     f"- **Total Open Pipeline Value:** **₹{agg['total_open_pipeline_value']:,.2f}**\n" \
                     f"- **Weighted Open Pipeline Value:** **~₹{agg['weighted_open_pipeline_value']:,.2f}** *(Directional estimate)*\n" \
                     f"- **Closed Won Value:** **₹{agg['total_won_value']:,.2f}**\n" \
                     f"- **Total Matching Deals:** **{res['matched_count']}**\n\n" \
                     f"**Deal Funnel Stage Breakdown:**\n"
            for stage, count in list(agg["stage_breakdown"].items())[:6]:
                answer += f"- **{stage}:** {count} deals\n"

            caveats.extend(res["data_quality_notes"])

        return sanitize_for_json({
            "answer": answer,
            "reasoning_traces": traces,
            "ui_cards": ui_cards,
            "caveats": caveats,
            "grounding_valid": True
        })

    async def stream_chat(self, user_query: str, history: Optional[List[Dict[str, str]]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams reasoning steps, tool execution events, structured UI cards, and tokens.
        """
        # If Groq client is configured with real key, run tool-calling LLM loop
        if self.client and self.api_key and not self.api_key.startswith("mock"):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if history:
                for h in history:
                    messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": user_query})

            yield {"type": "thought", "content": "Analyzing query and planning tool calls..."}
            
            try:
                # LLM first turn to decide tools
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0.1,
                )
                
                choice = response.choices[0]
                ui_cards = []
                caveats = []
                
                # Check for tool calls
                if choice.message.tool_calls:
                    messages.append(choice.message)
                    for tool_call in choice.message.tool_calls:
                        func_name = tool_call.function.name
                        func_args = json.loads(tool_call.function.arguments or "{}")
                        
                        yield {
                            "type": "tool_start",
                            "tool": func_name,
                            "args": func_args,
                            "content": f"→ Calling {func_name}({json.dumps(func_args)})"
                        }
                        
                        tool_result = await execute_tool_call(func_name, func_args)
                        
                        # Generate UI Card if applicable
                        if func_name == "get_deals":
                            ui_cards.append({"type": "pipeline_card", "data": tool_result})
                            caveats.extend(tool_result.get("data_quality_notes", []))
                        elif func_name == "get_work_orders":
                            ui_cards.append({"type": "work_orders_card", "data": tool_result})
                            caveats.extend(tool_result.get("data_quality_notes", []))
                        elif func_name == "join_deals_and_work_orders":
                            ui_cards.append({"type": "join_inspector", "data": tool_result})
                        elif func_name == "get_data_quality_summary":
                            ui_cards.append({"type": "data_quality_card", "data": tool_result})
                        elif func_name == "draft_leadership_update":
                            ui_cards.append({"type": "leadership_deck", "data": tool_result})
                            caveats.extend(tool_result.get("data_quality_caveats", []))

                        yield {
                            "type": "tool_end",
                            "tool": func_name,
                            "content": f"✓ {func_name} completed successfully."
                        }

                        # Compact tool payload for LLM to stay within Groq free-tier token limits
                        compact_result = {k: v for k, v in tool_result.items() if k not in ["sample_deals", "sample_work_orders", "matched_sample", "orphaned_work_orders", "deals_without_work_orders"]}
                        if "sample_deals" in tool_result:
                            compact_result["sample_deals_preview"] = tool_result["sample_deals"][:3]
                        if "sample_work_orders" in tool_result:
                            compact_result["sample_work_orders_preview"] = tool_result["sample_work_orders"][:3]

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(compact_result, default=str)
                        })

                    # Second turn for final synthesis
                    final_resp = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.2,
                    )
                    final_text = final_resp.choices[0].message.content or ""
                    
                    yield {"type": "answer", "content": final_text}
                    for card in ui_cards:
                        yield {"type": "ui_card", "card": card}
                    for cav in set(caveats):
                        yield {"type": "caveat", "content": cav}
                    return

                else:
                    yield {"type": "answer", "content": choice.message.content or ""}
                    return

            except Exception as e:
                logger.warning(f"Groq API call failed: {e}. Falling back to resilient local planner.")
                yield {"type": "thought", "content": f"Groq API fallback triggered: {str(e)}"}

        # Deterministic Planner fallback
        det_result = await self.run_deterministic_query(user_query)
        for trace in det_result["reasoning_traces"]:
            yield {"type": "thought", "content": trace}
        yield {"type": "answer", "content": det_result["answer"]}
        for card in det_result["ui_cards"]:
            yield {"type": "ui_card", "card": card}
        for cav in det_result["caveats"]:
            yield {"type": "caveat", "content": cav}

agent = BIAgent()
