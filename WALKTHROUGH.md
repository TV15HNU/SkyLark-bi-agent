# Walkthrough — Skylark Drones: Monday.com Business Intelligence Agent

We have built, verified, and documented the complete **Skylark Drones Monday.com Business Intelligence Agent & Ops Analyst Cockpit** according to the master build prompt and assignment specifications.

---

## 1. What Was Built

### 1.1 Data Preparation & Clean CSVs
- Prepared clean CSV exports ready for direct monday.com board import:
  - [`backend/data/deals_for_monday_import.csv`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/data/deals_for_monday_import.csv) (342 cleaned deals)
  - [`backend/data/work_orders_for_monday_import.csv`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/data/work_orders_for_monday_import.csv) (175 cleaned work orders)

### 1.2 Backend (FastAPI, Python 3.13)
- **[`monday_client.py`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/app/monday_client.py)**: Async Monday.com GraphQL API v2 client with cursor-based `items_page` pagination, token authentication, `MondayAPIError` handling, and in-memory TTL caching (120s) with zero-setup local dataset fallback.
- **[`normalizer.py`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/app/normalizer.py)**: Defensive normalization layer:
  - Prunes mid-sheet duplicated header rows (`Deal Status == 'Deal Status'`).
  - Reconciles 5 overlapping status columns via strict hierarchy: `Collection status > Billing Status > WO Status > Invoice Status > Execution Status`.
  - Parses unit-embedded quantities (e.g. `"5360 HA"`, `"105 Towers"`, `"45days"`).
  - Normalizes multiple date formats defensively via `dateutil`.
  - Maps sector taxonomies (`"energy"` → `Mining`, `Renewables`, `Powerline`).
  - Automated field completeness scoring and data resilience caveat generation.
- **[`tools.py`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/app/tools.py)**: Typed BI tools:
  - `get_deals(sectors, statuses, stages, owners, date_range)`
  - `get_work_orders(sectors, execution_statuses, billing_statuses, date_range)`
  - `join_deals_and_work_orders(deal_names)`
  - `get_data_quality_summary(board)`
  - `draft_leadership_update(scope, period)`
- **[`agent.py`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/app/agent.py)**: Groq / OpenAI LLM tool-calling orchestrator with streaming SSE, multi-step reasoning traces (`⚡ Calling get_deals...`), grounding guardrails, and deterministic rule planner fallback.
- **[`main.py`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/backend/app/main.py)**: FastAPI endpoints (`/health`, `/api/chat`, `/api/data-quality`, `/api/tools/*`, `/api/cache/refresh`).

### 1.3 Frontend (Next.js 14 + React + TypeScript) — "Ops Analyst Cockpit"
- **[`LeftRail.tsx`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/frontend/app/components/LeftRail.tsx)**: Sector scope selector and live **Data Quality & Completeness Strip** (Deals: 75.2%, Work Orders: 74.5%) with active caveats.
- **[`ChatThread.tsx`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/frontend/app/components/ChatThread.tsx)**: Compact search-bar style queries, left-aligned analyst notes, collapsible tool execution reasoning pills, inline `~` caveat markers, and interactive founder query starters.
- **[`GenerativeCards.tsx`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/frontend/app/components/GenerativeCards.tsx)**: Inline interactive cards for Deal Funnel, Work Orders Execution, Cross-Board Join Inspector, and Leadership Deck.
- **[`RightRail.tsx`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/frontend/app/components/RightRail.tsx)**: Pinned Intelligence panel keeping the active visual in view, plus 1-click Markdown copy and export.
- **[`Header.tsx`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/frontend/app/components/Header.tsx)**: Live monday.com sync pulse badge, LLM inference status, and cache refresh button.

### 1.4 Deliverables & Documentation
- **[`DECISION_LOG.md`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/DECISION_LOG.md)**: 2-page executive document covering Assumptions, Trade-offs, Future Improvements, and Leadership Updates interpretation.
- **[`README.md`](file:///c:/Users/vishn/OneDrive/Desktop/SkyLark/README.md)**: Architecture diagram, monday.com setup & column type mapping guide, environment variables, test instructions, and AI disclosure.

---

## 2. Verification Results

### Automated Test Suite
Ran 22 comprehensive unit and integration tests across normalizer, tools, and FastAPI routes:
```bash
python -m pytest backend/tests/ -o pythonpath=backend
```
**Result:** `22 passed in 2.21s` (100% pass rate).

### Core Founder Query Scenarios Tested

| Scenario | Query Tested | Output & Validation |
| :--- | :--- | :--- |
| **1. Energy Pipeline** | *"How is our sales pipeline looking for energy sector this quarter?"* | Resolves `Mining`, `Renewables`, `Powerline`. Yields ₹60.9M open pipeline, ~₹30.5M directional weighted pipeline, stage funnel breakdown, and surfaces 74.9% missing probability caveat. |
| **2. Unbilled Execution** | *"What is our total unbilled amount across ongoing work orders?"* | 5-to-1 status reconciliation applied. Calculates ₹210.6M contract total, ₹107.4M billed revenue, ₹103.2M unbilled backlog, and ₹36.3M AR. |
| **3. Cross-Board Join** | *"Which deals are won but have no work order created?"* | Asymmetric join audit: 52 matched projects, 102 pipeline-only deals (46 marked 'Won'), and 6 orphaned work orders (`Dolphin`, `Octopus`, `Golden fish`, `Turtle`, `Whale`, `GG go`). |
| **4. Leadership Brief** | *"Draft a comprehensive Q3 leadership update"* | Generates structured briefing with headline KPIs, top 3 strategic risks, operational breakdown, and 1-click exportable Markdown card. |
| **5. Data Resilience Audit** | *"Show data completeness and quality audit"* | Deals Board: 75.2% complete; Work Orders Board: 74.5% complete. Surfaces all field missing rates. |

---

## 3. How to Run Locally

1. **Backend Server**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --port 8000
   ```
2. **Frontend Cockpit**:
   ```bash
   cd frontend
   npm run dev
   ```
   Access at `http://localhost:3000`.
