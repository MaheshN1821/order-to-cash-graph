# Order-to-Cash Graph Query System

An interactive graph visualization and natural-language query interface built on SAP Order-to-Cash (O2C) ERP data. Users can explore the full business document flow — from Sales Orders through Deliveries, Billing, Journal Entries, and Payments — and ask questions in plain English backed by live SQL execution.

---

## Live Demo

> https://order-to-cash-graph-steel.vercel.app/

---

## Repository

> https://github.com/MaheshN1821/order-to-cash-graph/

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                   │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ GraphCanvas  │  │  ChatPanel  │  │   NodePanel    │  │
│  │  (Sigma.js)  │  │  (LLM Chat) │  │ (Inspect Node) │  │
│  └──────┬───────┘  └──────┬──────┘  └───────┬────────┘  │
│         └─────────────────┼─────────────────┘           │
│                     axios / REST API                    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI / Python)             │
│                                                         │
│   /api/graph          /api/query          /api/health   │
│        │                   │                            │
│   NetworkX DiGraph    Guardrail check                   │
│   built at startup    → LLM (SQL gen)                   │
│   from SQLite         → SQLite execute                  │
│                       → LLM (answer gen)                │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    SQLite (o2c.db)                      │
│  16 tables: sales_order_headers, outbound_delivery_*,   │
│  billing_document_*, journal_entry_items, products,     │
│  business_partners, plants, payments_ar ...             │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | React + Vite | Fast dev server, modern JSX tooling |
| Graph Rendering | Sigma.js + Graphology | WebGL-accelerated, handles large graphs; ForceAtlas2 layout for natural clustering |
| Backend | FastAPI (Python) | Async-ready, auto-generates OpenAPI docs, clean Pydantic validation |
| Graph Library | NetworkX DiGraph | Rich graph algorithms (BFS neighbourhood, path tracing) with a simple Python API |
| Database | SQLite | Zero-config, file-based, ships with the dataset. WAL mode for concurrent reads |
| LLM (primary) | Groq — `llama-3.3-70b-versatile` | Free tier, very fast inference (~200 tok/s), strong SQL generation |
| LLM (fallback) | Google Gemini 2.5 Flash Lite | Free tier fallback; also used for guardrail classification |

---

## Database Design

The raw dataset (JSONL files) is ingested via `scripts/ingest.py` into a normalised SQLite schema (`db/schema.sql`).

### Core O2C Join Chain

```
sales_order_headers
  └── outbound_delivery_items       (via reference_sd_document)
        └── outbound_delivery_headers (via delivery_document)
              └── billing_document_items (via reference_sd_document → delivery)
                    └── billing_document_headers (via billing_document)
                          └── journal_entry_items (via reference_document → billing)
                                └── payments_accounts_receivable (via accounting_document)
```

All foreign keys follow this chain. The schema enforces `PRAGMA foreign_keys = ON` and uses `PRAGMA journal_mode = WAL` for read performance. Indexes are created on every FK column and high-cardinality filter columns (e.g. `sold_to_party`, `reference_document`).

### Why SQLite over a Graph DB (e.g. Neo4j)?

The O2C dataset is fundamentally relational — every link is a well-defined FK, not an ad-hoc property. SQLite gives us:
- Zero infrastructure overhead (one `.db` file, ships with Python)
- Full SQL expressiveness for aggregations, GROUP BY, window functions
- Instant LLM-readable schema that maps to standard SQL training data

The graph layer (NetworkX) is built on top of SQLite at startup and lives in memory. It is used purely for visualization and neighbourhood traversal, not for the analytical queries.

---

## Graph Modeling

The in-memory graph (`app/graph.py`) is a directed `nx.DiGraph`. Every node follows the pattern `<type>:<id>` (e.g. `customer:320000083`) to prevent collisions across entity types.

### Node Types & Colors

| Entity | Color | Represents |
|---|---|---|
| `customer` | Purple | Business partners / sold-to parties |
| `product` | Teal | Materials / SKUs |
| `plant` | Gray | Production/shipping plants |
| `sales_order` | Blue | Sales order headers |
| `delivery` | Amber | Outbound delivery documents |
| `billing_doc` | Coral | Billing/invoice documents |
| `journal_entry` | Pink | FI accounting documents |
| `payment` | Green | AR payment clearing entries |

### Edge Relationships

```
customer ──PLACED──► sales_order
sales_order ──CONTAINS_ITEM──► product
sales_order ──FULFILLED_BY──► delivery
delivery ──SHIPPED_FROM──► plant
delivery ──BILLED_AS──► billing_doc
billing_doc ──POSTED_AS──► journal_entry
journal_entry ──CLEARED_BY──► payment
customer ──PAID──► payment
```

`product_storage_locations` and `product_plants` inventory tables are intentionally excluded — they add thousands of nodes that are irrelevant to the O2C document flow.

---

## LLM Integration & Prompting Strategy

The query flow has two LLM calls:

### Call 1 — SQL Generation

The system prompt embeds the full schema with exact column names, explicit join order rules, and examples. Key constraints baked into the prompt:

- **Join order rule**: every table in an `ON` clause must appear earlier in the `FROM/JOIN` list (SQLite is strict about this).
- **No column invention**: LLM is given every column for every table; hallucinated column names are a primary failure mode and the prompt explicitly prohibits them.
- **Template for common patterns**: the billing document trace query is given verbatim so the LLM doesn't have to reconstruct the 6-table join from scratch.
- **`CANNOT_ANSWER` escape hatch**: if the question is unanswerable from the schema, the LLM returns a sentinel string rather than fabricating SQL.

### Call 2 — Answer Summarization

A short system prompt instructs the model to behave as a business analyst, summarize actual values from the result rows, and keep responses under 200 words. The full SQL and up to 20 result rows are passed in context.

### Self-Healing SQL

If the generated SQL fails to execute, the error is sent back to the LLM with the broken SQL and a targeted repair prompt ("every table in an ON clause must already appear in the FROM/JOIN list"). This catches ~80% of join-order mistakes without user intervention.

---

## Guardrails

Off-topic queries are rejected before any LLM call, saving latency and tokens.

The guardrail is a two-layer filter in `is_off_topic()`:

**Layer 1 — Regex blocklist** (fast, zero-cost):
Matches patterns like `write a poem`, `tell me a joke`, `what is the capital of`, `write code for`, Python/JS tutorial keywords, and references to other AI models.

**Layer 2 — Keyword allowlist**:
If no blocklist match, the message must contain at least one O2C domain keyword (`order`, `billing`, `delivery`, `invoice`, `payment`, `customer`, `material`, `journal`, `fiscal`, `clearing`, ...) to pass. Bare numeric document IDs (SAP doc numbers like `91150187`) pass through because they contain digits but no blocklist terms and are then matched by the SQL generator context.

Rejected queries return a fixed response:
> "This system is designed to answer questions about the Order-to-Cash dataset only. Please ask about sales orders, deliveries, billing documents, payments, customers, or products."

`rejected: true` is included in the API response so the frontend can style the message differently.

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, query endpoint, guardrail, LLM calls
│   │   └── graph.py         # NetworkX graph builder + API helpers
│   ├── db/
│   │   └── schema.sql       # Full SQLite schema with indexes
│   ├── scripts/
│   │   └── ingest.py        # JSONL → SQLite loader
│   ├── o2c.db               # Pre-built SQLite database
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root layout, state, filter bar
│   │   ├── components/
│   │   │   ├── GraphCanvas.jsx  # Sigma.js + ForceAtlas2 graph
│   │   │   ├── ChatPanel.jsx    # Chat UI, query submission, result display
│   │   │   ├── NodePanel.jsx    # Node metadata inspector (slide-in)
│   │   │   └── Toolbar.jsx      # Entity-type filter controls
│   │   └── lib/
│   │       ├── api.js           # Axios wrappers for backend endpoints
│   │       └── graphUtils.js    # Graphology graph construction, color map
│   └── package.json
│
└── README.md
```

---

## Setup & Running Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- A free API key from [Groq](https://console.groq.com) (or [Google Gemini](https://ai.google.dev))

### Backend

```bash
cd backend
pip install -r requirements.txt

# Copy env file and add your key
cp .env.example .env
# Edit .env: GROQ_API_KEY=your_key_here

# Database is pre-built (o2c.db). To rebuild from raw data:
python scripts/ingest.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Example Queries

The system is designed to answer questions like:

---

### Query: Which products are associated with the highest number of billing documents?

**Result:**  
The top products associated with the highest number of billing documents are S8907367039280 and S8907367008620, both with 22 billing documents. The next highest is S8907367042006 with 16 billing documents, followed by S8907367013532 with 15 billing documents. The list continues with products having 9, 8, 7, 6, and 4 billing documents. The results show a total of 50 products with varying numbers of billing documents, with the lowest being 4 billing documents for several products, including S8907367041993, S8907367038108, and S8907367035992.

**Generated SQL:**
```sql
SELECT bdi.material, COUNT(DISTINCT bdh.billing_document) as num_billing_docs
FROM billing_document_headers bdh
LEFT JOIN billing_document_items bdi ON bdi.billing_document = bdh.billing_document
GROUP BY bdi.material
ORDER BY num_billing_docs DESC
LIMIT 50;
```

---

### Query: Trace the full flow for billing document 91150187

**Result:**  
The billing document 91150187 has a total net amount of $329.66 and was created on April 2, 2025. It is associated with sales order 740550 and delivery document 80738070. The sold-to party is Nelson, Fitzpatrick and Jordan. The billing document has not been cancelled, as indicated by the "billing_document_is_cancelled" flag being set to 0. The corresponding accounting document is 9400635958. This suggests a complete order-to-cash flow, from sales order to delivery and finally to billing.

**Generated SQL:**
```sql
SELECT bdh.billing_document, soh.sales_order, odh.delivery_document, 
       bp.business_partner_name, bdh.total_net_amount, bdh.billing_document_date, 
       bdh.billing_document_is_cancelled, bdh.accounting_document
FROM billing_document_headers bdh
LEFT JOIN billing_document_items bdi    ON bdi.billing_document = bdh.billing_document
LEFT JOIN outbound_delivery_headers odh ON odh.delivery_document = bdi.reference_sd_document
LEFT JOIN outbound_delivery_items odi   ON odi.delivery_document = odh.delivery_document
LEFT JOIN sales_order_headers soh       ON soh.sales_order = odi.reference_sd_document
LEFT JOIN business_partners bp          ON bp.business_partner = bdh.sold_to_party
WHERE bdh.billing_document = '91150187'
LIMIT 50;
```

---

### Query: Show sales orders that were delivered but never billed

**Result:**  
The query results show 3 sales orders that were delivered but never billed. The sales order numbers are 740506, 740507, and 740508. These orders have associated outbound deliveries, but no corresponding billing documents were found. This suggests that the delivery process was completed, but the billing process was not triggered or completed for these orders.

**Generated SQL:**
```sql
SELECT DISTINCT soh.sales_order
FROM sales_order_headers soh
LEFT JOIN outbound_delivery_items odi ON odi.reference_sd_document = soh.sales_order
LEFT JOIN billing_document_items bdi ON bdi.reference_sd_document = odi.delivery_document
WHERE odi.delivery_document IS NOT NULL AND bdi.billing_document IS NULL
LIMIT 50;
```

---

### Query: Which customers have the highest total billed amount?

**Result:**  
The top customers with the highest total billed amount are: 1. Nelson, Fitzpatrick and Jordan with $55,337.76, 2. Nguyen-Davis with $4,769.30, 3. Hawkins Ltd with $442.38, and 4. Flores-Simmons with $359.32. These four customers have the highest total billed amounts, with Nelson, Fitzpatrick and Jordan having the largest amount by a significant margin.

**Generated SQL:**
```sql
SELECT bp.business_partner_name, SUM(bdh.total_net_amount) AS total_billed_amount
FROM billing_document_headers bdh
LEFT JOIN business_partners bp ON bp.business_partner = bdh.sold_to_party
GROUP BY bp.business_partner_name
ORDER BY total_billed_amount DESC
LIMIT 50;
```

---

### Query: Find all cancelled billing documents and their linked sales orders

**Result:**  
The query results show 20 cancelled billing documents with their linked sales orders. The cancelled billing documents have IDs such as 90504274, 90504242, and 90678703, with total net amounts ranging from 151.69 to 589.95. The linked sales orders have IDs like 740571, 740548, and 740542. The business partners associated with these documents are primarily "Nelson, Fitzpatrick and Jordan" and "Nguyen-Davis". The billing document dates are mostly on April 2, 2025, and May 16, 2025. Note that there are duplicate entries for some billing documents, such as 90678703, which appears 8 times with the same details.

**Generated SQL:**
```sql
SELECT bdh.billing_document, soh.sales_order, odh.delivery_document, 
       bp.business_partner_name, bdh.total_net_amount, bdh.billing_document_date, 
       bdh.billing_document_is_cancelled, bdh.accounting_document
FROM billing_document_headers bdh
LEFT JOIN billing_document_items bdi    ON bdi.billing_document = bdh.billing_document
LEFT JOIN outbound_delivery_headers odh ON odh.delivery_document = bdi.reference_sd_document
LEFT JOIN outbound_delivery_items odi   ON odi.delivery_document = odh.delivery_document
LEFT JOIN sales_order_headers soh       ON soh.sales_order = odi.reference_sd_document
LEFT JOIN business_partners bp          ON bp.business_partner = bdh.sold_to_party
WHERE bdh.billing_document_is_cancelled = 1
LIMIT 50;
```

---

### Query: What is the total payment received for customer 320000083?

**Result:**  
The total payment received for customer 320000083 is $9,445.05. This amount is based on the sum of payments made by the customer, as recorded in the payments accounts receivable. The query only considered a limited number of records (up to 50) due to the LIMIT clause, but since only one row was returned, it appears that all relevant records were included in the calculation.

**Generated SQL:**
```sql
SELECT SUM(par.amount_in_transaction_currency) 
FROM payments_accounts_receivable par 
JOIN business_partners bp ON bp.business_partner = par.customer 
WHERE bp.business_partner = '320000083' 
LIMIT 50;
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | LLM status check |
| GET | `/api/graph` | Full graph (nodes + links) as JSON |
| GET | `/api/graph/stats` | Node/edge counts by type |
| GET | `/api/graph/node/{id}` | Single node with metadata |
| GET | `/api/graph/neighbours/{id}` | BFS neighbourhood (depth 1–3) |
| GET | `/api/graph/flow/{id}` | Full O2C flow path for a document |
| POST | `/api/query` | Natural language query → SQL → answer |

---

## AI Coding Session Logs

GitHub Copilot (VS Code) was used throughout development. Session transcripts are included in `session.md` at the repository root.

Key interactions covered:
- Initial full-stack scaffold generation (FastAPI + React + Vite)
- Guardrail prompt refinement — fixing over-blocking of valid SAP document ID queries
- Graph visualization tuning — ForceAtlas2 physics, degree-based node sizing, directional edge arrows, highlight-aware link opacity

---

## Tradeoffs & Design Decisions

**SQLite over Neo4j**: The O2C relationships are fixed FKs, not dynamic graph properties. SQLite gave us zero-config deployment, standard SQL for LLM generation, and the ability to ship the database as a single file alongside the code.

**NetworkX over a pure frontend graph**: Building the graph in Python lets us compute BFS paths, flow traces, and graph statistics server-side, keeping the frontend simple and the heavy computation close to the data.

**Groq over OpenAI**: Free tier with high rate limits and faster inference than comparable OpenAI endpoints at the time of development. The Gemini fallback ensures availability if Groq is down.

**In-memory graph rebuilt at startup**: At ~750 nodes the rebuild takes under 100ms. Caching to disk (GraphML/JSON) would add complexity without meaningful benefit at this scale.
