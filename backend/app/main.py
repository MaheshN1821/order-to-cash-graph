"""
main.py — FastAPI backend for the O2C Graph system.
"""

from __future__ import annotations

import os
import re
import sqlite3
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env so GROQ_API_KEY / GEMINI_API_KEY are picked up automatically
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path)
    print(f"Loaded .env from {_env_path}")
except ImportError:
    print("python-dotenv not installed — set API keys in shell directly")

from app.graph import build_graph, graph_to_json, get_node_neighbourhood, get_flow_path, graph_stats

DB_PATH = Path(__file__).resolve().parent.parent / "o2c.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Building O2C graph...")
    app.state.graph = build_graph()
    stats = graph_stats(app.state.graph)
    print(f"Graph ready: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    if os.environ.get("GROQ_API_KEY"):
        print("LLM: Groq (llama-3.3-70b-versatile)")
    elif os.environ.get("GEMINI_API_KEY"):
        print("LLM: Google Gemini")
    else:
        print("WARNING: No LLM API key found. Set GROQ_API_KEY in backend/.env")
    yield
    print("Shutting down.")


app = FastAPI(title="O2C Graph API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://order-to-cash-graph-steel.vercel.app"],
    allow_credentials=False,   
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm": "groq" if os.environ.get("GROQ_API_KEY") else
               "gemini" if os.environ.get("GEMINI_API_KEY") else "none",
    }


@app.get("/api/graph")
def get_graph(request: Request):
    return graph_to_json(request.app.state.graph)


@app.get("/api/graph/stats")
def get_stats(request: Request):
    return graph_stats(request.app.state.graph)


@app.get("/api/graph/node/{node_id:path}")
def get_node(node_id: str, request: Request):
    G = request.app.state.graph
    if node_id not in G:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    attrs = dict(G.nodes[node_id])
    attrs["id"] = node_id
    attrs["in_degree"] = G.in_degree(node_id)
    attrs["out_degree"] = G.out_degree(node_id)
    attrs["predecessors"] = list(G.predecessors(node_id))
    attrs["successors"] = list(G.successors(node_id))
    return attrs


@app.get("/api/graph/neighbours/{node_id:path}")
def get_neighbours(node_id: str, request: Request, depth: int = 1):
    G = request.app.state.graph
    if node_id not in G:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return get_node_neighbourhood(G, node_id, max(1, min(depth, 3)))


@app.get("/api/graph/flow/{node_id:path}")
def get_flow(node_id: str, request: Request):
    G = request.app.state.graph
    if node_id not in G:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return get_flow_path(G, node_id)


class QueryRequest(BaseModel):
    message: str


SCHEMA_CONTEXT = """
You are an expert SQL assistant for an SAP Order-to-Cash (O2C) SQLite database.
You must ONLY use the exact table and column names listed below. Never invent column names.

TABLES AND THEIR EXACT COLUMNS:

business_partners(business_partner, customer, business_partner_name, city_name, country, region, is_blocked)

products(product, product_type, product_old_id, product_group, base_unit, gross_weight, net_weight, weight_unit, division, is_marked_for_deletion, creation_date)

product_descriptions(product, language, description)
  -- Always filter: language = 'EN'

plants(plant, plant_name, sales_organization, distribution_channel, division)

sales_order_headers(sales_order, sales_order_type, sales_organization, sold_to_party, creation_date, total_net_amount, transaction_currency, requested_delivery_date, overall_delivery_status, overall_billing_status, customer_payment_terms)
  -- sold_to_party is FK to business_partners.business_partner

sales_order_items(sales_order, sales_order_item, material, requested_quantity, requested_quantity_unit, net_amount, transaction_currency, material_group, production_plant, storage_location, rejection_reason)
  -- material is FK to products.product
  -- production_plant is FK to plants.plant

sales_order_schedule_lines(sales_order, sales_order_item, schedule_line, confirmed_delivery_date, order_quantity_unit, confirmed_order_qty)

outbound_delivery_headers(delivery_document, shipping_point, creation_date, actual_goods_movement_date, overall_goods_movement_status, overall_picking_status, last_change_date)

outbound_delivery_items(delivery_document, delivery_document_item, reference_sd_document, reference_sd_document_item, plant, storage_location, actual_delivery_quantity, delivery_quantity_unit, batch)
  -- reference_sd_document is FK to sales_order_headers.sales_order
  -- plant is FK to plants.plant

billing_document_headers(billing_document, billing_document_type, creation_date, billing_document_date, total_net_amount, transaction_currency, company_code, fiscal_year, accounting_document, sold_to_party, billing_document_is_cancelled, cancelled_billing_document)
  -- sold_to_party is FK to business_partners.business_partner
  -- billing_document_date is the invoice date (NOT in billing_document_items)

billing_document_items(billing_document, billing_document_item, material, billing_quantity, billing_quantity_unit, net_amount, transaction_currency, reference_sd_document, reference_sd_document_item)
  -- billing_document is FK to billing_document_headers.billing_document
  -- reference_sd_document is FK to outbound_delivery_headers.delivery_document
  -- NOTE: billing_document_items has NO date column — use billing_document_headers for dates

billing_document_cancellations(billing_document, billing_document_type, total_net_amount, billing_document_date, billing_document_is_cancelled, company_code, fiscal_year, accounting_document, sold_to_party)

journal_entry_items(company_code, fiscal_year, accounting_document, accounting_document_item, gl_account, reference_document, cost_center, profit_center, transaction_currency, amount_in_transaction_currency, company_code_currency, amount_in_company_code_currency, posting_date, document_date, accounting_document_type, customer, financial_account_type, clearing_date, clearing_accounting_document)
  -- reference_document is FK to billing_document_headers.billing_document
  -- customer is FK to business_partners.business_partner

payments_accounts_receivable(company_code, fiscal_year, accounting_document, accounting_document_item, clearing_date, clearing_accounting_document, amount_in_transaction_currency, transaction_currency, amount_in_company_code_currency, company_code_currency, customer, invoice_reference, sales_document, sales_document_item, posting_date, document_date, gl_account, financial_account_type, profit_center, cost_center)
  -- customer is FK to business_partners.business_partner

KEY JOIN CHAIN (always use these exact join conditions):
sales_order_headers
  JOIN outbound_delivery_items    ON outbound_delivery_items.reference_sd_document = sales_order_headers.sales_order
  JOIN outbound_delivery_headers  ON outbound_delivery_headers.delivery_document = outbound_delivery_items.delivery_document
  JOIN billing_document_items     ON billing_document_items.reference_sd_document = outbound_delivery_headers.delivery_document
  JOIN billing_document_headers   ON billing_document_headers.billing_document = billing_document_items.billing_document
  JOIN journal_entry_items        ON journal_entry_items.reference_document = billing_document_headers.billing_document
  JOIN payments_accounts_receivable ON payments_accounts_receivable.accounting_document = journal_entry_items.accounting_document

RULES — follow strictly:
1. Return ONLY a single valid SQLite SQL statement. No markdown, no backticks, no explanation.
2. Use LEFT JOIN when tracing the full O2C chain (orders may not have all downstream docs).
3. Use only column names exactly as listed above. NEVER guess or invent column names.
4. billing_document_items has NO date — join to billing_document_headers for any date filtering.
5. For product names: JOIN product_descriptions ON product_descriptions.product = <alias>.material AND product_descriptions.language = 'EN'
6. For customer names: JOIN business_partners ON business_partners.business_partner = <alias>.sold_to_party
7. LIMIT 50 unless user requests more.
8. If the question cannot be answered with this schema, return exactly: CANNOT_ANSWER

CRITICAL JOIN ORDER RULE (SQLite requires this):
Every table referenced in an ON clause MUST already appear in the FROM/JOIN list above it.
You MUST join tables in this exact dependency order:

  FROM billing_document_headers bdh
  LEFT JOIN billing_document_items bdi       ON bdi.billing_document = bdh.billing_document
  LEFT JOIN outbound_delivery_headers odh    ON odh.delivery_document = bdi.reference_sd_document
  LEFT JOIN outbound_delivery_items odi      ON odi.delivery_document = odh.delivery_document
  LEFT JOIN sales_order_headers soh          ON soh.sales_order = odi.reference_sd_document
  LEFT JOIN sales_order_items soi            ON soi.sales_order = soh.sales_order
  LEFT JOIN business_partners bp             ON bp.business_partner = bdh.sold_to_party
  LEFT JOIN product_descriptions pd          ON pd.product = bdi.material AND pd.language = 'EN'

NEVER join sales_order_headers before outbound_delivery_items has been joined.
NEVER reference a table alias in an ON clause before that table appears in the JOIN list.

For tracing a billing document flow, always use this template:
SELECT bdh.billing_document, soh.sales_order, odh.delivery_document,
       bp.business_partner_name, bdh.total_net_amount, bdh.billing_document_date,
       bdh.billing_document_is_cancelled, bdh.accounting_document
FROM billing_document_headers bdh
LEFT JOIN billing_document_items bdi    ON bdi.billing_document = bdh.billing_document
LEFT JOIN outbound_delivery_headers odh ON odh.delivery_document = bdi.reference_sd_document
LEFT JOIN outbound_delivery_items odi   ON odi.delivery_document = odh.delivery_document
LEFT JOIN sales_order_headers soh       ON soh.sales_order = odi.reference_sd_document
LEFT JOIN business_partners bp          ON bp.business_partner = bdh.sold_to_party
WHERE bdh.billing_document = '<id>'
LIMIT 50
"""

GUARDRAIL_PATTERNS = [
    r"\b(write|tell|story|poem|joke|recipe|weather|news|sport|movie|music|wikipedia)\b",
    r"\b(who is|what is [a-z]+ (the|a)|capital of|history of|meaning of)\b",
    r"\b(python|javascript|code|algorithm|sort|fibonacci|hello world)\b",
    r"\b(chatgpt|openai|gemini|claude|llm|ai model)\b",
]
O2C_KEYWORDS = [
    "order", "sales", "delivery", "billing", "invoice", "payment",
    "customer", "product", "material", "plant", "journal", "document",
    "amount", "quantity", "flow", "cancelled", "status", "trace",
    "fiscal", "account", "gl", "clearing", "shipped",
]


def is_off_topic(message: str) -> bool:
    msg = message.lower()
    for p in GUARDRAIL_PATTERNS:
        if re.search(p, msg):
            return True
    return not any(kw in msg for kw in O2C_KEYWORDS)


def _groq(payload: dict) -> str:
    # Uses requests instead of urllib — Cloudflare blocks urllib User-Agent on POST
    try:
        import requests as req_lib
    except ImportError:
        raise RuntimeError("requests not installed. Run: pip install requests")
    key = (os.environ.get("GROQ_API_KEY") or "").strip()
    resp = req_lib.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Groq {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"].strip()


def _gemini(prompt: str, temperature: float = 0) -> str:
    try:
        import requests as req_lib
    except ImportError:
        raise RuntimeError("requests not installed. Run: pip install requests")
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    # gemini-2.5-flash-lite: 15 RPM / 250K TPM on free tier
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={key}"
    resp = req_lib.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024},
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Gemini {resp.status_code}: {resp.text[:300]}")
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def call_llm_for_sql(msg: str) -> str:
    if os.environ.get("GROQ_API_KEY"):
        return _groq({
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SCHEMA_CONTEXT},
                {"role": "user", "content": f"Generate SQL for: {msg}"},
            ],
            "max_tokens": 500,
            "temperature": 0,
        })
    elif os.environ.get("GEMINI_API_KEY"):
        return _gemini(f"{SCHEMA_CONTEXT}\n\nUser question: {msg}\n\nSQL:", temperature=0)
    else:
        raise ValueError(
            "No LLM API key configured. Add GROQ_API_KEY=your_key to backend/.env and restart."
        )


def call_llm_for_answer(msg: str, sql: str, results: list[dict]) -> str:
    system = (
        "You are a helpful business analyst assistant for an SAP Order-to-Cash dataset. "
        "Summarize the SQL query results in clear, concise natural language. "
        "Be specific — mention actual values, document IDs, amounts where relevant. "
        "If results are empty, say so and suggest why. Keep the answer under 200 words."
    )
    user_content = (
        f"Question: {msg}\n\nSQL:\n{sql}\n\n"
        f"Results ({len(results)} rows):\n{json.dumps(results[:20], indent=2)}"
    )
    if os.environ.get("GROQ_API_KEY"):
        return _groq({
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 400,
            "temperature": 0.3,
        })
    elif os.environ.get("GEMINI_API_KEY"):
        return _gemini(f"{system}\n\n{user_content}", temperature=0.3)
    else:
        return f"Query returned {len(results)} result(s)." if results else "No results found."


@app.post("/api/query")
async def query(body: QueryRequest):
    msg = body.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if is_off_topic(msg):
        return {
            "answer": (
                "This system is designed to answer questions about the "
                "Order-to-Cash dataset only. Please ask about sales orders, "
                "deliveries, billing documents, payments, customers, or products."
            ),
            "sql": None, "results": [], "rejected": True,
        }

    try:
        raw_sql = call_llm_for_sql(msg)
    except ValueError as e:
        return {"answer": str(e), "sql": None, "results": [], "rejected": False}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM unavailable: {str(e)}")

    sql = re.sub(r"```(?:sql)?|```", "", raw_sql).strip()

    if sql.upper().startswith("CANNOT_ANSWER"):
        return {
            "answer": "I couldn't find a way to answer that from the available dataset.",
            "sql": None, "results": [], "rejected": False,
        }

    # Execute SQL with one automatic retry if LLM produced a bad join order
    rows = []
    sql_error = None
    for attempt in range(2):
        conn = None
        try:
            conn = get_db()
            cursor = conn.execute(sql)
            cols = [d[0] for d in cursor.description]
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
            conn.close()
            sql_error = None
            break
        except sqlite3.Error as e:
            sql_error = str(e)
            if conn:
                conn.close()
            if attempt == 0:
                # Send the error back to LLM to self-correct
                try:
                    fix_prompt = (
                        f"This SQLite query failed:\nError: {sql_error}\n\n"
                        f"Broken SQL:\n{sql}\n\n"
                        f"Fix the SQL. Key rule: every table in an ON clause must already "
                        f"appear earlier in the FROM/JOIN list. "
                        f"Return ONLY the corrected SQL, no markdown, no explanation."
                    )
                    fixed_raw = call_llm_for_sql(fix_prompt)
                    sql = re.sub(r'```(?:sql)?|```', '', fixed_raw).strip()
                except Exception:
                    pass

    if sql_error:
        return {
            "answer": f"The generated SQL had an error: {sql_error}. Please rephrase your question.",
            "sql": sql, "results": [], "rejected": False,
        }

    try:
        answer = call_llm_for_answer(msg, sql, rows)
    except Exception:
        answer = f"Query returned {len(rows)} result(s)." if rows else "No results found."

    return {"answer": answer, "sql": sql, "results": rows, "rejected": False}

