"""
graph.py — Build and serve the O2C NetworkX graph from SQLite.

Design decisions:
- Nodes are typed business entities. Each node has an 'entity_type' attribute
  and a 'label' (human-readable) plus all relevant metadata as extra attrs.
- Edges are directed and typed via 'relationship' attribute.
- Node IDs follow the pattern  <type>:<id>  e.g. "customer:320000083"
  so collisions across types are impossible.
- The graph is built once at startup and cached in memory.
  For this dataset size (~750 nodes) rebuilding takes <100ms — no need for
  persistence. If the dataset grows, serialize to GraphML/JSON on disk.
- product_storage_locations and product_plants are intentionally excluded —
  they add thousands of inventory rows that don't belong in the O2C flow graph.
"""

import sqlite3
import json
from pathlib import Path
from typing import Any

import networkx as nx

DB_PATH = Path(__file__).resolve().parent.parent / "o2c.db"

# ── Node color/shape hints for the frontend ───────────────────────────────────
NODE_META = {
    "customer":       {"color": "#7F77DD", "shape": "diamond"},  # purple
    "product":        {"color": "#1D9E75", "shape": "ellipse"},  # teal
    "plant":          {"color": "#888780", "shape": "rectangle"},# gray
    "sales_order":    {"color": "#378ADD", "shape": "rectangle"},# blue
    "delivery":       {"color": "#EF9F27", "shape": "rectangle"},# amber
    "billing_doc":    {"color": "#D85A30", "shape": "rectangle"},# coral
    "journal_entry":  {"color": "#D4537E", "shape": "rectangle"},# pink
    "payment":        {"color": "#639922", "shape": "ellipse"},  # green
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _node_id(entity_type: str, key: str) -> str:
    return f"{entity_type}:{key}"


def _add_node(G: nx.DiGraph, entity_type: str, key: str, label: str, **attrs):
    nid = _node_id(entity_type, key)
    meta = NODE_META.get(entity_type, {})
    G.add_node(nid,
               entity_type=entity_type,
               entity_id=str(key),
               label=label,
               color=meta.get("color", "#888780"),
               shape=meta.get("shape", "rectangle"),
               **attrs)
    return nid


def _add_edge(G: nx.DiGraph, src: str, dst: str, relationship: str, **attrs):
    G.add_edge(src, dst, relationship=relationship, **attrs)


# ── Per-entity loaders ────────────────────────────────────────────────────────

def _load_customers(G: nx.DiGraph, conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT bp.business_partner, bp.business_partner_name,
               bp.business_partner_category, bp.is_blocked,
               a.city_name, a.country, a.region, a.street_name
        FROM business_partners bp
        LEFT JOIN business_partner_addresses a
            ON a.business_partner = bp.business_partner
    """).fetchall()
    for r in rows:
        _add_node(G, "customer", r["business_partner"],
                  label=r["business_partner_name"] or r["business_partner"],
                  customer_id=r["business_partner"],
                  category=r["business_partner_category"],
                  is_blocked=bool(r["is_blocked"]),
                  city=r["city_name"],
                  country=r["country"],
                  region=r["region"])


def _load_products(G: nx.DiGraph, conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT p.product, pd.description, p.product_type,
               p.product_group, p.base_unit, p.gross_weight, p.weight_unit
        FROM products p
        LEFT JOIN product_descriptions pd
            ON pd.product = p.product AND pd.language = 'EN'
    """).fetchall()
    for r in rows:
        _add_node(G, "product", r["product"],
                  label=r["description"] or r["product"],
                  product_id=r["product"],
                  product_type=r["product_type"],
                  product_group=r["product_group"],
                  base_unit=r["base_unit"],
                  gross_weight=r["gross_weight"],
                  weight_unit=r["weight_unit"])


def _load_plants(G: nx.DiGraph, conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT plant, plant_name, sales_organization, distribution_channel
        FROM plants
    """).fetchall()
    for r in rows:
        _add_node(G, "plant", r["plant"],
                  label=r["plant_name"] or r["plant"],
                  plant_id=r["plant"],
                  sales_organization=r["sales_organization"])


def _load_sales_orders(G: nx.DiGraph, conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT soh.sales_order, soh.sold_to_party, soh.total_net_amount,
               soh.transaction_currency, soh.creation_date,
               soh.overall_delivery_status, soh.overall_billing_status,
               soh.requested_delivery_date, soh.sales_order_type,
               soh.incoterms_classification
        FROM sales_order_headers soh
    """).fetchall()
    for r in rows:
        so_nid = _add_node(G, "sales_order", r["sales_order"],
                           label=f"SO {r['sales_order']}",
                           so_id=r["sales_order"],
                           total_net_amount=r["total_net_amount"],
                           currency=r["transaction_currency"],
                           creation_date=r["creation_date"],
                           delivery_status=r["overall_delivery_status"],
                           billing_status=r["overall_billing_status"],
                           requested_delivery_date=r["requested_delivery_date"],
                           so_type=r["sales_order_type"])

        # Edge: customer → sales_order
        cust_nid = _node_id("customer", r["sold_to_party"])
        if cust_nid in G:
            _add_edge(G, cust_nid, so_nid, "PLACED_ORDER",
                      amount=r["total_net_amount"],
                      currency=r["transaction_currency"])

    # SO → Product edges (via items)
    items = conn.execute("""
        SELECT sales_order, material, net_amount, requested_quantity,
               requested_quantity_unit, production_plant
        FROM sales_order_items
    """).fetchall()
    for item in items:
        so_nid = _node_id("sales_order", item["sales_order"])
        prod_nid = _node_id("product", item["material"])
        if so_nid in G and prod_nid in G:
            _add_edge(G, so_nid, prod_nid, "CONTAINS_PRODUCT",
                      net_amount=item["net_amount"],
                      quantity=item["requested_quantity"],
                      unit=item["requested_quantity_unit"])


def _load_deliveries(G: nx.DiGraph, conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT odh.delivery_document, odh.creation_date,
               odh.overall_goods_movement_status, odh.overall_picking_status,
               odh.shipping_point, odh.actual_goods_movement_date
        FROM outbound_delivery_headers odh
    """).fetchall()
    for r in rows:
        _add_node(G, "delivery", r["delivery_document"],
                  label=f"Delivery {r['delivery_document']}",
                  delivery_id=r["delivery_document"],
                  creation_date=r["creation_date"],
                  goods_movement_status=r["overall_goods_movement_status"],
                  picking_status=r["overall_picking_status"],
                  shipping_point=r["shipping_point"],
                  actual_goods_movement_date=r["actual_goods_movement_date"])

    # SO → Delivery edges (via delivery items)
    # Also: delivery → plant edges
    items = conn.execute("""
        SELECT DISTINCT odi.delivery_document, odi.reference_sd_document,
               odi.plant, SUM(odi.actual_delivery_quantity) as total_qty,
               odi.delivery_quantity_unit
        FROM outbound_delivery_items odi
        GROUP BY odi.delivery_document, odi.reference_sd_document, odi.plant
    """).fetchall()
    for item in items:
        so_nid = _node_id("sales_order", item["reference_sd_document"])
        del_nid = _node_id("delivery", item["delivery_document"])
        if so_nid in G and del_nid in G:
            _add_edge(G, so_nid, del_nid, "FULFILLED_BY",
                      total_quantity=item["total_qty"],
                      unit=item["delivery_quantity_unit"])

        # delivery → plant
        if item["plant"]:
            plant_nid = _node_id("plant", item["plant"])
            if plant_nid in G and del_nid in G:
                _add_edge(G, del_nid, plant_nid, "SHIPPED_FROM")


def _load_billing_docs(G: nx.DiGraph, conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT billing_document, billing_document_type, billing_document_date,
               total_net_amount, transaction_currency, company_code,
               fiscal_year, accounting_document, sold_to_party,
               billing_document_is_cancelled
        FROM billing_document_headers
    """).fetchall()
    for r in rows:
        _add_node(G, "billing_doc", r["billing_document"],
                  label=f"Billing {r['billing_document']}",
                  billing_id=r["billing_document"],
                  billing_type=r["billing_document_type"],
                  billing_date=r["billing_document_date"],
                  total_net_amount=r["total_net_amount"],
                  currency=r["transaction_currency"],
                  company_code=r["company_code"],
                  fiscal_year=r["fiscal_year"],
                  accounting_document=r["accounting_document"],
                  is_cancelled=bool(r["billing_document_is_cancelled"]))

    # Delivery → Billing edges (via billing items)
    items = conn.execute("""
        SELECT DISTINCT bdi.reference_sd_document as delivery_doc,
               bdi.billing_document,
               SUM(bdi.net_amount) as total_amount,
               bdi.transaction_currency
        FROM billing_document_items bdi
        GROUP BY bdi.reference_sd_document, bdi.billing_document
    """).fetchall()
    for item in items:
        del_nid = _node_id("delivery", item["delivery_doc"])
        bill_nid = _node_id("billing_doc", item["billing_document"])
        if del_nid in G and bill_nid in G:
            _add_edge(G, del_nid, bill_nid, "BILLED_AS",
                      amount=item["total_amount"],
                      currency=item["transaction_currency"])


def _load_journal_entries(G: nx.DiGraph, conn: sqlite3.Connection):
    # Group by accounting_document — each accounting doc is one JE node
    rows = conn.execute("""
        SELECT accounting_document, reference_document,
               SUM(amount_in_transaction_currency) as total_amount,
               transaction_currency, posting_date, company_code,
               fiscal_year, accounting_document_type, customer,
               clearing_date, clearing_accounting_document
        FROM journal_entry_items
        GROUP BY accounting_document
    """).fetchall()
    for r in rows:
        je_nid = _add_node(G, "journal_entry", r["accounting_document"],
                           label=f"JE {r['accounting_document']}",
                           je_id=r["accounting_document"],
                           posting_date=r["posting_date"],
                           total_amount=r["total_amount"],
                           currency=r["transaction_currency"],
                           company_code=r["company_code"],
                           fiscal_year=r["fiscal_year"],
                           doc_type=r["accounting_document_type"],
                           clearing_date=r["clearing_date"],
                           reference_document=r["reference_document"])

        # Billing → JournalEntry edge
        bill_nid = _node_id("billing_doc", r["reference_document"])
        if bill_nid in G:
            _add_edge(G, bill_nid, je_nid, "POSTED_TO_GL",
                      amount=r["total_amount"],
                      currency=r["transaction_currency"])


def _load_payments(G: nx.DiGraph, conn: sqlite3.Connection):
    # Each unique clearing_accounting_document is a payment node
    rows = conn.execute("""
        SELECT clearing_accounting_document,
               SUM(amount_in_transaction_currency) as total_amount,
               transaction_currency, MAX(clearing_date) as clearing_date,
               customer, company_code, fiscal_year,
               GROUP_CONCAT(DISTINCT accounting_document) as source_docs
        FROM payments_accounts_receivable
        WHERE clearing_accounting_document IS NOT NULL
        GROUP BY clearing_accounting_document
    """).fetchall()
    for r in rows:
        pay_nid = _add_node(G, "payment", r["clearing_accounting_document"],
                            label=f"Payment {r['clearing_accounting_document']}",
                            payment_id=r["clearing_accounting_document"],
                            total_amount=r["total_amount"],
                            currency=r["transaction_currency"],
                            clearing_date=r["clearing_date"],
                            company_code=r["company_code"])

    # JournalEntry → Payment edges
    links = conn.execute("""
        SELECT DISTINCT p.accounting_document, p.clearing_accounting_document,
               p.amount_in_transaction_currency, p.transaction_currency
        FROM payments_accounts_receivable p
        WHERE p.clearing_accounting_document IS NOT NULL
    """).fetchall()
    for lnk in links:
        je_nid = _node_id("journal_entry", lnk["accounting_document"])
        pay_nid = _node_id("payment", lnk["clearing_accounting_document"])
        if je_nid in G and pay_nid in G:
            _add_edge(G, je_nid, pay_nid, "CLEARED_BY",
                      amount=lnk["amount_in_transaction_currency"],
                      currency=lnk["transaction_currency"])


# ── Public API ────────────────────────────────────────────────────────────────

def build_graph() -> nx.DiGraph:
    """
    Build the full O2C graph from SQLite and return it.
    Called once at FastAPI startup; result is stored in app.state.graph.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    G = nx.DiGraph()

    # Load in dependency order so edges can find both endpoints
    _load_customers(G, conn)
    _load_products(G, conn)
    _load_plants(G, conn)
    _load_sales_orders(G, conn)
    _load_deliveries(G, conn)
    _load_billing_docs(G, conn)
    _load_journal_entries(G, conn)
    _load_payments(G, conn)

    conn.close()
    return G


def graph_to_json(G: nx.DiGraph) -> dict:
    """
    Serialise the full graph to a JSON-safe dict for the frontend.
    Format: { nodes: [...], edges: [...] }
    Each node: { id, label, entity_type, color, shape, ...metadata }
    Each edge: { source, target, relationship }
    """
    nodes = []
    for nid, attrs in G.nodes(data=True):
        node = {"id": nid}
        node.update({k: v for k, v in attrs.items() if v is not None})
        nodes.append(node)

    edges = []
    for src, dst, attrs in G.edges(data=True):
        edge = {"source": src, "target": dst}
        edge.update(attrs)
        edges.append(edge)

    return {"nodes": nodes, "edges": edges}


def get_node_neighbourhood(G: nx.DiGraph, node_id: str, depth: int = 1) -> dict:
    """
    Return a subgraph of all nodes reachable within `depth` hops from node_id
    (both in-edges and out-edges).
    """
    if node_id not in G:
        return {"nodes": [], "edges": []}

    # BFS in both directions
    visited = {node_id}
    frontier = {node_id}
    for _ in range(depth):
        next_frontier = set()
        for nid in frontier:
            next_frontier.update(G.predecessors(nid))
            next_frontier.update(G.successors(nid))
        next_frontier -= visited
        visited.update(next_frontier)
        frontier = next_frontier

    subgraph = G.subgraph(visited)
    return graph_to_json(subgraph)


def get_flow_path(G: nx.DiGraph, start_id: str) -> dict:
    """
    Given a node id, return the full downstream O2C chain
    (all nodes reachable following directed edges).
    """
    if start_id not in G:
        return {"nodes": [], "edges": []}
    reachable = nx.descendants(G, start_id) | {start_id}
    return graph_to_json(G.subgraph(reachable))


def graph_stats(G: nx.DiGraph) -> dict:
    from collections import Counter
    type_counts = Counter(d["entity_type"] for _, d in G.nodes(data=True))
    rel_counts = Counter(d["relationship"] for _, _, d in G.edges(data=True))
    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "nodes_by_type": dict(type_counts),
        "edges_by_relationship": dict(rel_counts),
    }