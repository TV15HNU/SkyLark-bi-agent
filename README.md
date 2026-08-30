# 🚁 Skylark Drones — Monday.com Business Intelligence Agent

> **Founder-Level Ops Analyst Cockpit & Business Intelligence Agent querying live monday.com Boards (Deals Pipeline & Work Orders Tracker)**

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│               Frontend: Next.js + React (Ops Analyst Cockpit)          │
│  - Three-zone layout (Left: Data Quality & Filters; Center: Chat &     │
│    Generative UI Cards; Right: Pinned Intelligence & Leadership Deck)  │
│  - JetBrains Mono numeric figures + Space Grotesk UI typography        │
│  - Multi-step tool execution pill traces & inline data caveats         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SSE / REST
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Backend: FastAPI (Python 3.13)                           │
│  ┌────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │ Agent Orchestrator     │  │ Normalization & Data Resilience Layer│  │
│  │ - Groq (llama-3.3-70b) │  │ - Drop embedded duplicate headers    │  │
│  │ - Multi-step Tool Loop │  │ - Dateutil multi-format parser       │  │
│  │ - Grounding Guardrails │  │ - Unit-embedded quantity parser      │  │
│  │ - Planner Fallback Mode│  │ - 5-to-1 Status Reconciliation       │  │
│  └───────────┬────────────┘  │ - Sector Taxonomy Resolver           │  │
│              │               │ - Automated Data Quality Scorer      │  │
│              ▼               └──────────────────┬───────────────────┘  │
│  ┌────────────────────────┐                     │                      │
│  │ Typed Tool Interface   │◄────────────────────┘                      │
│  │ - get_deals            │                                            │
│  │ - get_work_orders      │  ┌──────────────────────────────────────┐  │
│  │ - join_boards          │  │ In-Memory TTL Cache (120s)           │  │
│  │ - data_quality_summary │  └──────────────────┬───────────────────┘  │
│  │ - leadership_update    │                     │                      │
│  └───────────┬────────────┘                     ▼                      │
│              │               ┌──────────────────────────────────────┐  │
│              └──────────────►│ monday.com GraphQL API Client v2     │  │
│                              └──────────────────┬───────────────────┘  │
└─────────────────────────────────────────────────┼──────────────────────┘
                                                  │ GraphQL POST (v2)
                                                  ▼
                                     ┌─────────────────────────┐
                                     │   monday.com Boards     │
                                     │  - Board A: Deals       │
                                     │  - Board B: Work Orders │
                                     └─────────────────────────┘
```

---

## ⚡ Key Highlights & Core Features

1. **Read-Only Dynamic monday.com Integration**:
   - Live GraphQL API v2 client querying boards on request.
   - Paginates with cursor-based `items_page` and flattens column values.
   - Zero-setup local fallback dataset included for instant offline evaluation.
2. **Defensive Normalization & Data Resilience**:
   - Automatically prunes mid-sheet duplicated header rows.
   - Reconciles 5 overlapping status columns into one authoritative operational status:
     `Collection status > Billing Status > WO Status (billed) > Invoice Status > Execution Status`.
   - Parses unit-embedded quantities (e.g. `"5360 HA"`, `"105 Towers"`, `"45days"`).
   - Surfaces data-quality caveats explicitly (e.g. *74.6% deals missing closure probability*).
3. **Founder-Level Query Understanding & Tool Calling**:
   - Resolves macro industry groupings (e.g. `"energy sector"` → `Mining`, `Renewables`, `Powerline`).
   - Groq tool calling (`llama-3.3-70b-versatile`) with multi-step reasoning traces.
   - Built-in high-accuracy deterministic planner fallback for zero-configuration runs.
4. **"Ops Analyst Cockpit" Generative UI**:
   - 3-zone layout: Left Rail (Data Quality Meters), Center (Chat & Generative Cards), Right Rail (Pinned Intelligence & 1-Click Markdown Leadership Export).
   - JetBrains Mono data typography for numbers, currency, and dates.

---

## 📋 Monday.com Setup & Board Configuration

To import the datasets into monday.com:

1. **Board A — Deals Pipeline**:
   - Create a new blank board named **"Deals"**.
   - Import `backend/data/deals_for_monday_import.csv`.
   - Map column types:
     - `Deal Name`: **Item Name** / Text
     - `Deal Status`: **Status** (`Open`, `Won`, `Dead`, `On Hold`)
     - `Deal Stage`: **Status** / Dropdown (`A. Lead Generated` → `H. Work Order Received`, etc.)
     - `Sector/service`: **Dropdown** or **Status** (`Mining`, `Renewables`, `Powerline`, `Railways`, etc.)
     - `Masked Deal value`: **Numbers**
     - `Closure Probability`: **Numbers**
     - `Tentative Close Date` / `Close Date (A)` / `Created Date`: **Date**

2. **Board B — Work Orders Tracker**:
   - Create a new blank board named **"Work Orders"**.
   - Import `backend/data/work_orders_for_monday_import.csv`.
   - Map column types:
     - `Deal name masked`: **Item Name** / Text
     - `Customer Name Code`: **Text**
     - `Execution Status`: **Status** (`Completed`, `Ongoing`, `Not Started`, `Paused / Stuck`)
     - `Sector`: **Status** / Dropdown
     - `Amount in Rupees (Excl of GST) (Masked)`: **Numbers**
     - `Billed Value in Rupees (Excl of GST.) (Masked)`: **Numbers**
     - `Amount to be billed in Rs. (Exl. of GST) (Masked)`: **Numbers**
     - `Amount Receivable (Masked)`: **Numbers**
     - `Date of PO/LOI` / `Probable Start Date` / `Data Delivery Date`: **Date**

3. **Obtain API Token & Board IDs**:
   - In monday.com, go to **Admin → API** and generate a read-only Personal API Token.
   - Note the numeric Board IDs from the browser URL for both boards.

---

## 🚀 Quickstart & Local Setup

### 1. Backend Setup (FastAPI, Python 3.13)

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env` (optional, leave empty for local sandbox mode):
```env
MONDAY_API_TOKEN=your_monday_token_here
DEALS_BOARD_ID=1234567890
WORK_ORDERS_BOARD_ID=9876543210
GROQ_API_KEY=gsk_your_groq_key_here
CACHE_TTL_SECONDS=120
PORT=8000
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
Backend API will be available at: `http://localhost:8000` (Swagger docs at `http://localhost:8000/docs`).

### 2. Frontend Setup (Next.js 14)

```bash
cd frontend
npm install
npm run dev
```
Frontend Cockpit will be live at: `http://localhost:3000`.

---

## 🧪 Running Automated Tests

Run the full backend test suite (22 unit & integration tests):
```bash
cd backend
python -m pytest tests/ -v -o pythonpath=.
```

Test coverage includes:
- `test_normalizer.py`: Embedded header removal, status mapping, date parsing, quantity unit splitting, 5-to-1 status reconciliation, and quality scoring.
- `test_tools.py`: Filtering, pipeline aggregations, cross-board join calculations, and leadership briefing generation.
- `test_api.py`: FastAPI endpoints, health checks, chat endpoint, and serialization.

---

## 🤖 AI Tools & Reproducibility Disclosure

- **Inference Provider**: Powered by **Groq API** using `llama-3.3-70b-versatile` with tool calling. Groq's developer tier is completely free ($0, no credit card required), ensuring full reproducibility by any evaluator.
- **Agent Architecture**: Uses the LLM as a multi-step query planner over typed tools (`get_deals`, `get_work_orders`, `join_deals_and_work_orders`, `get_data_quality_summary`, `draft_leadership_update`), enforcing strict grounding so numbers are never hallucinated.
- **Deterministic Fallback**: Built-in rule planner executes with 100% test passing accuracy even without API keys.
