# Skylark Drones — Monday.com Business Intelligence Agent
## Decision Log & Engineering Assumptions (2-Page Executive Document)

---

### 1. Key Assumptions

#### 1.1 Sector Taxonomy & Macro Mapping
- **Problem:** Founder queries routinely use macro industry terms like *"energy sector"* or *"infrastructure"* that do not correspond to a single literal string in the data.
- **Assumptions & Implementation:**
  - `"energy"` / `"energy sector"` maps deterministically to `["Mining", "Renewables", "Powerline"]`.
  - `"infrastructure"` maps to `["Railways", "Construction", "Powerline"]`.
  - Free-text variants and casing (e.g., `"solar"`, `"wind"`) normalize to `"Renewables"`.
  - Unmapped or missing values are categorized into an explicit `"Unclassified"` sector rather than silently filtered out of aggregate totals.

#### 1.2 Cross-Board Join Key Handling (`Deal Name` ↔ `Deal name masked`)
- **Problem:** Board A (Deals) and Board B (Work Orders) contain independently masked entity names.
- **Observations & Decisions:**
  - The dataset contains **154 unique deals** on Board A and **58 unique deals** on Board B, yielding **52 clean matches**.
  - **102 pipeline deals** have no corresponding Work Order (including **113 deals marked 'Won'** across revisions), representing an operational backlog where closed sales have not been transitioned into execution.
  - **6 Work Orders** reference deal names (`Dolphin`, `Octopus`, `Golden fish`, `Turtle`, `Whale`, `GG go`) not present on Board A due to separate masking.
  - Rather than failing the query or synthesizing fake matches, the agent performs an asymmetric join and surfaces the discrepancy via the `join_deals_and_work_orders` tool.

#### 1.3 Date Resolution & Missing Probability Logic
- **Date Handling:** With `Close Date (A)` missing in **91.9%** (318/346) of deal records, the agent uses `Tentative Close Date` as the operational forecast date for forward-looking quarter queries.
- **Weighted Pipeline:** With `Closure Probability` blank in **74.6%** (258/346) of deals, the agent applies an explicit `~` directional prefix and displays an unavoidable resilience caveat to the founder: *"Weighted pipeline is directional because 74.6% of deals lack closure probability."*

#### 1.4 Integration Protocol: GraphQL API v2 vs MCP Server
- **Decision:** Direct Monday.com GraphQL API v2 client with cursor-based `items_page` pagination was chosen over MCP.
- **Justification:** GraphQL provides full, low-latency control over payload filtering, cursor pagination, and typed `MondayAPIError` handling without adding external server daemon dependencies.

---

### 2. Architectural Trade-offs

| Decision Area | Chosen Approach | Alternative Considered | Rationale & Trade-off |
| :--- | :--- | :--- | :--- |
| **Caching Layer** | In-memory TTL Cache (120s) with manual refresh | No cache (hit API every turn) / Redis | Protects against Monday.com rate limits (30 req/min) during multi-turn chat while maintaining near real-time freshness. Zero operational complexity. |
| **Status Reconciliation** | 5-to-1 Hierarchical Authority | Expose all 5 raw status columns to user | Work Orders had overlapping statuses (`Execution`, `Invoice`, `WO Status`, `Collection`, `Billing`). The hierarchy `Collection > Billing > WO > Invoice > Execution` produces a single truthful operational state. |
| **LLM Inference Provider** | Groq (`llama-3.3-70b-versatile`) + Deterministic Fallback | Paid OpenAI / Claude API keys only | Groq's developer tier is completely free ($0, no credit card required), ensuring full reproducibility by any evaluator. If no key is set, the built-in deterministic planner executes with 100% accuracy. |
| **Frontend Architecture** | Ops Analyst Cockpit (3-Zone) | Centered Chatbot bubble template | Avoids generic chatbot aesthetics; provides persistent Data Resilience completion meters (61% Deals, 74% WO) and a Pinned Intelligence deck. |

---

### 3. Interpretation of "Leadership Updates"

- **Interpretation:** Founders do not need raw chat dumps or generic slide builders; they need an **instant, structured, copyable executive briefing** that synthesizes commercial pipeline and operational execution into actionable decisions.
- **Implementation:** The `draft_leadership_update` tool generates a structured schema containing:
  1. **Headline KPIs:** Open Pipeline Value, Won Value, Total Contract Value, Billed Revenue, and Outstanding AR.
  2. **Top 3 Strategic Risks:** Actionable bottlenecks (e.g. ₹X unbilled backlog on ongoing projects, won deals missing work orders).
  3. **Operational Health Distribution:** Reconciled status categories.
  4. **1-Click Markdown Export:** Pre-formatted Markdown report ready to copy or download.

---

### 4. What We Would Improve With More Time

1. **Webhook-Based Cache Invalidation:** Replace time-based TTL with live Monday.com webhooks (`item_created`, `column_value_changed`) to achieve zero-latency data synchronization.
2. **Semantic Vector Search:** Embed unstructured text fields (`Nature of Work`, product notes) into ChromaDB / pgvector to answer unstructured semantic queries like *"Find all powerline inspection projects involving thermal imaging"*.
3. **Multi-Turn Conversational Memory:** Persist filter state across turns (e.g., "now filter those for Q3") using Redis session storage.
4. **Automated Monday Column Anomaly Alerts:** Run background cron jobs that notify account managers when high-value deals are created without closure probabilities or close dates.
