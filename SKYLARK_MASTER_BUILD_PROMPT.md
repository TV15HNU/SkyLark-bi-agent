# Master Build Prompt — Skylark Drones: Monday.com Business Intelligence Agent

> Paste this whole document into Claude Code / Cursor / Copilot Chat as the system/kickoff prompt. It is written so an AI coding agent can execute it with minimal back-and-forth. Sections are ordered in build priority.

---

## 0. What you are building (context for the AI agent)

Skylark Drones (drone-based industrial inspection/survey company — mining, powerline, renewables, railways) wants a conversational AI agent that answers founder-level business questions ("How's our pipeline looking for energy sector this quarter?") by querying **two live monday.com boards** — Deals (sales pipeline) and Work Orders (project execution) — and reasoning across both. The data is intentionally messy. The evaluator cares more about judgment, data-resilience, and a defensible architecture than about feature-completeness.

**Non-negotiable constraints from the brief:**
- Read-only monday.com integration via API or MCP — **never hardcode the CSVs into the agent**. Every answer must come from a live query at request time.
- Conversational interface, not a form/dashboard-only tool.
- Must gracefully surface data-quality issues to the user instead of silently guessing.
- Deliverables: hosted public link, GitHub repo, README (architecture + monday.com setup), and a 2-page Decision Log (assumptions, trade-offs, what you'd improve, how you interpreted "leadership updates").

---

## 1. The real data you're working with

Two boards, imported from these files (already inspected — use these exact observations in the Decision Log, don't re-derive them):

### Board A — Deal Tracker (347 rows, 12 cols)
`Deal Name | Owner code | Client Code | Deal Status | Close Date (A) | Closure Probability | Masked Deal value | Tentative Close Date | Deal Stage | Product deal | Sector/service | Created Date`

Observed messiness:
- **Duplicate header rows pasted mid-sheet** — the literal string `"Deal Status"`, `"Sector/service"`, `"Deal Stage"` etc. appear as *data values*, twice, not just in row 1. A naive importer will treat these as real deals. Must be filtered.
- `Closure Probability` is blank in 258/347 rows (74%).
- `Close Date (A)` is blank in 318/347 rows (92%) — most open deals don't have an actual close date yet, only `Tentative Close Date`.
- `Deal Status` values: `Open, Won, Dead, On Hold`, plus 1 blank row.
- `Sector/service` has 8 blank rows and free-text-ish values (`Others`, `DSP`, `Security and Surveillance` mixed in with core sectors `Mining, Powerline, Renewables, Railways, Construction, Aviation, Manufacturing, Tender`).
- `Deal Stage` is a **lettered funnel** (`A. Lead Generated` → `O. Not Relevant at all`) — useful for pipeline-stage ordering if you sort by the letter prefix, but two rows have Stage = "Project Completed" which breaks the lettered scheme (a status value leaking into the stage column).

### Board B — Work Order Tracker (178 rows, 38 cols)
Key columns: `Deal name masked, Customer Name Code, Serial #, Nature of Work, Execution Status, Data Delivery Date, Date of PO/LOI, Probable Start/End Date, BD/KAM Personnel code, Sector, Type of Work, invoice/billing amounts (Excl/Incl GST, masked), Quantity fields, Invoice Status, WO Status (billed), Collection status, Billing Status`.

Observed messiness:
- Row 1 of the raw sheet is entirely blank (an artifact of the export) before the real header row.
- Heavy use of empty string `''` vs `None` interchangeably across billing/collection columns — treat both as "missing," don't let `''` pass falsy checks inconsistently.
- Quantity fields stored as mixed types — some numeric, some strings like `"5360 HA"` (unit embedded in the value).
- Status sprawl across near-duplicate columns: `Execution Status`, `Invoice Status`, `WO Status (billed)`, `Collection status`, `Billing Status` — these overlap in meaning and must be reconciled, not treated as 5 independent truths.
- `Deal name masked` is the join key back to Board A's `Deal Name` — but nothing guarantees 1:1 (a deal can have multiple work orders; some work-order deal names may not match any deal record exactly, since they're separately masked datasets).

**This is your headline demo material.** An agent that visibly says *"heads up — 74% of open deals have no closure probability set, so this pipeline-value estimate is directional, not precise"* is exactly what the brief is asking for in "Data Resilience." Don't clean this silently — surface it.

---

## 2. Architecture (recommended, justify deviations in Decision Log)

Given a ~5 hour build window, optimize for **fewest moving parts that still look production-minded**, not maximum cleverness.

```
┌─────────────────────────┐      ┌──────────────────────────┐      ┌───────────────┐
│  Frontend (Next.js/TS)  │◄────►│  Backend (FastAPI/Python) │◄────►│ monday.com API│
│  Vercel                 │ SSE/ │  Render/Railway            │ GQL  │ (read-only)   │
│  Chat + live insight    │ REST │  - Agent orchestrator      │      └───────────────┘
│  panel, data-quality    │      │  - monday.com client       │
│  strip                  │      │  - Normalization layer     │      ┌───────────────┐
└─────────────────────────┘      │  - In-memory cache (TTL)   │◄────►│ Groq API      │
                                  └──────────────────────────┘      │ (free, tool   │
                                                                     │  use)         │
                                                                     └───────────────┘
```

**Backend: FastAPI (Python).** Chosen over Node because the normalization layer (dates, dedup, unit-embedded quantities, status reconciliation) is pandas-shaped work, and Python keeps the data-cleaning code short and testable. One process, one language for both agent orchestration and data munging.

**LLM: Groq API with tool use (function calling) — free, no card needed.** Groq's developer tier has no cost and no credit card requirement (14,400 requests/day, 30 req/min, all models included — verified June 2026), and it's OpenAI-SDK-compatible, so you point the standard OpenAI client at `https://api.groq.com/openai/v1` and everything (chat completions, tool calling, streaming) works unchanged. Use `llama-3.3-70b-versatile` or `openai/gpt-oss-120b` — both support tool use. Don't build a custom NLU layer — give the model typed tools and let it plan multi-step queries (e.g., "energy sector pipeline this quarter" → call `query_deals(sector=["Mining","Renewables"], stage_not_in=["Dead"])` then `query_work_orders(sector=...)` then synthesize). This is also the most defensible thing to explain in an interview: you're using the model as a planner over a small, typed tool surface, not asking it to hallucinate numbers. Mention in the Decision Log that you picked Groq specifically to keep the whole build reproducible by anyone without a paid API key — a nice, evaluator-visible signal of practical judgment, not just a cost hack.

**monday.com: GraphQL API v2 (read-only token), not MCP**, unless you already have a working monday MCP server handy. Justification for Decision Log: MCP adds a server-management layer you don't have time to debug in a 5-hour window; the GraphQL API achieves the same "dynamic query, no hardcoded CSV" requirement with less integration risk. (If you do use monday's official MCP server, mention it explicitly as the trade-off you took instead — either choice is defensible, just document *why*.)

**Caching:** a thin in-memory TTL cache (60–120s) in front of the monday.com client, keyed by board ID. This satisfies "query monday.com dynamically" while not hammering the API on every chat turn — call this out as a deliberate trade-off (freshness vs. rate limits) in the Decision Log.

---

## 3. Backend build plan

### 3.1 monday.com setup
1. Create two boards in a monday.com workspace: "Deals" and "Work Orders."
2. Import the CSVs (convert the provided .xlsx to .csv first). Map column types sensibly: Status columns → monday "Status" column type, dates → "Date" column type, masked value/amount fields → "Numbers," free text → "Text," Sector/Nature of Work → "Dropdown" or "Status" (a labeled column type lets you see monday.com surface the same messy label sprawl found above — good demo moment).
3. Generate a **read-only-scoped personal API token** (Admin → API). Store as `MONDAY_API_TOKEN` env var. Never commit it.
4. Note both board IDs — store as env vars `DEALS_BOARD_ID`, `WORK_ORDERS_BOARD_ID`.

### 3.2 monday.com client module
- Single GraphQL POST wrapper against `https://api.monday.com/v2` with the token in the `Authorization` header.
- One query function that pages through `items_page` (monday's cursor-based pagination) and flattens `column_values` (id/text/value) into a plain dict per item.
- Wrap every call in try/except → on failure, raise a typed `MondayAPIError` that the agent layer can catch and turn into a user-facing "I couldn't reach monday.com right now, here's what I can tell you from the last successful fetch" message (graceful degradation = a Core Feature requirement, don't skip it).

### 3.3 Normalization layer (this is the section to spend real engineering care on)
Build pure functions, unit-testable, applied right after fetch and before caching:
- `drop_embedded_header_rows(items)` — filter out rows where a known column's value equals that column's own header string (handles the duplicate-header-row bug found above).
- `normalize_status(value, column)` — lowercase/trim, map known synonyms to canonical enums per column; anything unmapped → `"unknown"` + logged for the data-quality report, never silently dropped.
- `normalize_date(value)` — parse multiple date formats defensively (dateutil), return `None` + a flag if unparseable, never crash the request.
- `normalize_sector(value)` — canonicalize casing/whitespace, map known aliases, bucket true unknowns into an explicit `"Unclassified"` sector rather than excluding them from totals.
- `parse_quantity(value)` — split unit-embedded strings like `"5360 HA"` into `(number, unit)`; if unparseable, keep raw string and flag.
- `reconcile_work_order_status(row)` — pick one authoritative "current status" from the 5 overlapping status columns using a documented priority order (e.g., Collection status > Billing Status > WO Status > Invoice Status > Execution Status), and keep the rest as supporting detail rather than presenting all 5 as equally true.
- Every normalization function should also emit a **data-quality note** (e.g., `"3 deals missing Sector, excluded from sector breakdown"`) that gets threaded into the agent's final answer, not buried in logs.

### 3.4 Agent tools (give these exact-ish shapes to Groq's tool-use API)
- `get_deals(filters: sector?, status?, stage?, owner?, date_range?) -> deals[] + data_quality_notes[]`
- `get_work_orders(filters: sector?, execution_status?, billing_status?, date_range?) -> work_orders[] + data_quality_notes[]`
- `join_deals_and_work_orders(deal_names?) -> merged rows + unmatched-on-either-side counts` (surfaces the join-key fragility called out above)
- `get_data_quality_summary(board) -> completeness % per column, known caveats`
- `draft_leadership_update(scope: sector|overall, period) -> structured summary` (see §5)

System prompt for the agent should instruct it to: (1) resolve vague scoping terms like "this quarter" itself using the current date before calling tools, not ask the user unless genuinely ambiguous; (2) ask one clarifying question only when the query is truly underspecified (e.g., "pipeline" could mean deal count or deal value — ask); (3) always state completeness caveats when relevant fields are >20% missing; (4) never fabricate a number — every figure in a response must trace to a tool result.

### 3.5 Error handling
- monday.com API errors (auth, rate limit, network) → caught, logged, converted to a plain-language message + suggestion to retry.
- LLM/tool errors → same pattern; the conversational surface should never show a raw stack trace.
- Add a `/health` endpoint that pings monday.com and reports token validity — cheap, looks deliberate in a demo.

---

## 4. Conversational flow (what a demo run should look like)

1. User: *"How's our pipeline looking for the energy sector this quarter?"*
2. Agent resolves "energy sector" → `Mining` + `Renewables` (document this mapping choice explicitly), resolves "this quarter" against current date.
3. Calls `get_deals(sector=[Mining,Renewables], date_range=Q_current)`.
4. Notices `Closure Probability` missing on most matching rows → includes that caveat.
5. Answers with: total open deal value, count by stage, a one-line trend read, and a visible caveat line — not just a number dump.
6. Frontend renders the structured tool result as a small inline chart/table next to the chat bubble (generative UI, not just prose).

---

## 5. "Leadership updates" — how to interpret the optional requirement

Interpret it as: a **one-click, structured, exportable summary** the agent produces on request — not a full slide generator (out of scope for 5 hours). Implementation: a `draft_leadership_update` tool that returns a fixed-shape object (headline metrics, top 3 risks/blockers pulled from stalled deals or overdue work orders, data-quality caveats section) which the frontend renders as a clean card the user can copy as Markdown. State this interpretation explicitly in the Decision Log — the brief says "document your interpretation," so don't leave it implicit.

---

## 6. Frontend — design brief (read this carefully, this is where most candidates blend into generic AI-template mush)

**The failure mode to avoid:** centered chat column, rounded gradient bubbles, a floating sparkle/robot avatar, "Chat with AI ✨" hero copy, Inter font at one weight everywhere, purple-to-pink gradient buttons, glowing card borders. That is the default output of every AI page-builder right now and it will read as templated to an evaluator who has seen 40 of these this week.

**What to build instead — "Ops Analyst Cockpit," not "Chatbot":**

- **Layout:** three-zone, not single-column. Left rail (narrow, ~220px): board/sector filters and a live "data quality" strip (small horizontal bars showing % completeness per key field — this doubles as a Data Resilience feature and a visual anchor that's unmistakably *not* a chat template). Center: conversation thread. Right rail (collapsible on mobile): the most recent structured result — a chart, a table, or a leadership-update card — pinned and updated as the conversation progresses, so the user isn't scrolling back through chat to find a number.
- **Typography:** two-font system with real hierarchy. UI/body: **IBM Plex Sans** or **Space Grotesk**. Numbers/data/monospace figures (deal values, dates, IDs): **JetBrains Mono** or **IBM Plex Mono** — using a mono face for numeric data reads as "analyst tool," not "chatbot," and it's a small touch evaluators notice.
- **Color:** dark slate/charcoal base (`#12161C`-ish), not pure black. One accent color drawn from Skylark's actual domain — aerial/sky — used sparingly: a muted sky-blue or amber for interactive states and chart highlights only, never as a full-bleed gradient background. Status colors (Open/Won/Dead/On Hold, data-quality bars) should be desaturated, not neon — this is a B2B ops tool, not a consumer app.
- **Chat bubbles:** skip the classic two-tone rounded bubble pattern entirely. Render the user's turn as a compact right-aligned query line (like a search-bar echo, not a bubble) and the agent's turn as a left-aligned analyst note — a subtle left border rule, generous line-height, no bubble background at all. Structured results (numbers/tables/charts) render as distinct cards *below* the agent's prose, with their own border and a small "source: monday.com · fetched Xs ago" footer — this single footer detail does a lot of work signaling "this is a live data tool," which is exactly what the brief is testing for.
- **Data-quality surfacing as a first-class UI element**, not a text caveat only: a persistent small strip/badge (e.g., "Board completeness: Deals 61% · Work Orders 74%") always visible, plus inline warning chips next to any number that's derived from incomplete data (e.g., a "~" prefix or a small dotted-underline with a tooltip: "23 of 111 Renewables deals missing close probability").
- **Micro-interactions to include, cheap to build, high perceived-craft payoff:** streaming text response (token-by-token, not a spinner-then-dump), a subtle skeleton loader shaped like the eventual chart/table (not a generic spinner), and a "thinking" state that shows the tool calls the agent is making in a slim collapsible trace line (e.g., `→ querying Deals board · filtering sector: Mining, Renewables`) — this alone visibly demonstrates the multi-step agent reasoning the brief wants evaluated, and most candidates will hide it.
- **Empty/first-load state:** don't show a blank chat box. Show 3–4 suggested founder-style queries as clickable chips drawn from your actual data ("Which sector has the most stalled deals?", "What's our collection risk this month?") — signals you understand the business problem, not just the plumbing.
- **What NOT to add:** no avatar icons for the AI, no "Powered by AI ✨" badge treatment, no gradient text, no confetti/celebration animations, no dark-mode toggle (ship one considered mode well instead of two mediocre ones) unless you have spare time at the very end.

If using the `frontend-design` skill/agent while building, feed it this section verbatim as the design brief — it already encodes the anti-generic-AI direction the skill pushes toward.

---

## 7. Deployment checklist
- Frontend → Vercel (Next.js zero-config).
- Backend → Render or Railway (FastAPI, set env vars: `MONDAY_API_TOKEN`, `DEALS_BOARD_ID`, `WORK_ORDERS_BOARD_ID`, `GROQ_API_KEY` — free key from console.groq.com, no card).
- Confirm the hosted app is testable **without local setup** — this is an explicit deliverable requirement, verify in an incognito window before submitting.
- Confirm all shared links (repo, hosted app, Decision Log doc) are set to public/anyone-with-link before submitting the form.

## 8. Decision Log skeleton (2-page max — fill in as you build, don't write it last-minute)
1. **Assumptions** — sector taxonomy mapping ("energy" → Mining+Renewables), join-key handling between boards, quarter/date resolution logic, MCP-vs-API choice.
2. **Trade-offs** — caching window vs. freshness; 5 status columns reconciled to 1 vs. exposing all 5; scope of "leadership update" feature.
3. **What you'd improve with more time** — real vector/semantic search over free-text fields, a proper monday.com webhook-based cache invalidation instead of TTL, automated tests on the normalization layer, multi-turn memory of prior clarifying answers.
4. **How you interpreted "leadership updates"** — paste §5 above, adapted to what you actually shipped.

## 9. README skeleton
- Architecture diagram (reuse §2) + one-paragraph summary.
- Setup: monday.com board creation + column mapping instructions, env vars needed, local run commands.
- What's implemented vs. deliberately out of scope.
- AI tools used and how (be specific — which parts you had Cursor/Copilot scaffold vs. what you hand-wrote/reviewed, and note Groq (free tier, no card) as the inference provider so anyone can reproduce your setup for $0; the brief explicitly asks you to be able to explain this in interview).

## 10. Time-boxed execution order (if truly ~5 hours from now)
1. (30m) monday.com boards created + imported + API token working, confirm a raw GraphQL query returns data.
2. (60m) Backend: monday client + normalization layer + the 2 core tools (`get_deals`, `get_work_orders`), tested via curl/Postman before touching the LLM.
3. (45m) Wire Groq tool-use loop end-to-end on a plain HTML/curl test, confirm it calls tools correctly and surfaces caveats.
4. (90m) Frontend: three-zone layout, chat thread, one chart component, data-quality strip. Skip polish on anything not core.
5. (30m) `join_deals_and_work_orders` + `draft_leadership_update` if time allows — these are the differentiators, do them only after the core loop is solid end-to-end.
6. (30m) Deploy both, smoke-test in incognito, write README + Decision Log (don't leave these for the last 5 minutes — they're graded deliverables, not an afterthought).
7. Remaining time: the frontend craft details in §6 (mono-font numbers, tool-call trace line, empty-state chips) — these are what separate a "works" submission from a "stands out" one.
