"""
ingest.py — Phase 1 ingestion script
Reads all JSONL files from sap-o2c-data/, normalises them, and loads into SQLite.

Usage:
    python scripts/ingest.py

Outputs:
    backend/o2c.db  — the SQLite database used by all subsequent phases
"""

import json
import os
import re
import sqlite3
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
RAW_DIR  = BASE_DIR / "data" / "raw" / "sap-o2c-data"
DB_PATH  = BASE_DIR / "o2c.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def to_snake(name: str) -> str:
    """Convert camelCase / PascalCase to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


def load_jsonl(folder: str) -> list[dict]:
    """Read all part-*.jsonl files in a folder and return list of dicts."""
    records = []
    folder_path = RAW_DIR / folder
    for fpath in sorted(folder_path.glob("part-*.jsonl")):
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def snake_keys(record: dict) -> dict:
    """Return a new dict with all keys converted to snake_case."""
    return {to_snake(k): v for k, v in record.items()}


def safe_float(val) -> float | None:
    """Cast to float, return None on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def safe_int(val) -> int | None:
    """Cast to int from bool/int/str."""
    if val is None:
        return None
    if isinstance(val, bool):
        return int(val)
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def clean_str(val) -> str:
    """Strip whitespace and convert to string; None stays None."""
    if val is None:
        return None
    return str(val).strip()


def parse_date(val) -> str | None:
    """Return ISO date string (YYYY-MM-DD) or None."""
    if not val:
        return None
    s = str(val)
    # Already YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # ISO datetime → date only
    if "T" in s:
        return s.split("T")[0]
    return s


# ─── Per-table loaders ────────────────────────────────────────────────────────

def load_business_partners(conn):
    rows = []
    for r in load_jsonl("business_partners"):
        rows.append((
            clean_str(r.get("businessPartner")),
            clean_str(r.get("customer")),
            clean_str(r.get("businessPartnerCategory")),
            clean_str(r.get("businessPartnerFullName")),
            clean_str(r.get("businessPartnerName")),
            clean_str(r.get("businessPartnerGrouping")),
            clean_str(r.get("correspondenceLanguage")),
            clean_str(r.get("createdByUser")),
            parse_date(r.get("creationDate")),
            clean_str(r.get("firstName")),
            clean_str(r.get("lastName")),
            clean_str(r.get("formOfAddress")),
            clean_str(r.get("industry")),
            safe_int(r.get("businessPartnerIsBlocked")),
            safe_int(r.get("isMarkedForArchiving")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO business_partners VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  business_partners: {len(rows)} rows")


def load_business_partner_addresses(conn):
    rows = []
    for r in load_jsonl("business_partner_addresses"):
        rows.append((
            clean_str(r.get("businessPartner")),
            clean_str(r.get("addressId")),
            clean_str(r.get("cityName")),
            clean_str(r.get("country")),
            clean_str(r.get("postalCode")),
            clean_str(r.get("region")),
            clean_str(r.get("streetName")),
            clean_str(r.get("addressTimeZone")),
            parse_date(r.get("validityStartDate")),
            parse_date(r.get("validityEndDate")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO business_partner_addresses VALUES
        (?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  business_partner_addresses: {len(rows)} rows")


def load_customer_company_assignments(conn):
    rows = []
    for r in load_jsonl("customer_company_assignments"):
        rows.append((
            clean_str(r.get("customer")),
            clean_str(r.get("companyCode")),
            clean_str(r.get("reconciliationAccount")),
            clean_str(r.get("paymentTerms")),
            clean_str(r.get("customerAccountGroup")),
            safe_int(r.get("deletionIndicator")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO customer_company_assignments VALUES (?,?,?,?,?,?)
    """, rows)
    print(f"  customer_company_assignments: {len(rows)} rows")


def load_customer_sales_area_assignments(conn):
    rows = []
    for r in load_jsonl("customer_sales_area_assignments"):
        rows.append((
            clean_str(r.get("customer")),
            clean_str(r.get("salesOrganization")),
            clean_str(r.get("distributionChannel")),
            clean_str(r.get("division")),
            clean_str(r.get("currency")),
            clean_str(r.get("customerPaymentTerms")),
            clean_str(r.get("incotermsClassification")),
            clean_str(r.get("incotermsLocation1")),
            clean_str(r.get("shippingCondition")),
            clean_str(r.get("deliveryPriority")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO customer_sales_area_assignments VALUES
        (?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  customer_sales_area_assignments: {len(rows)} rows")


def load_products(conn):
    rows = []
    for r in load_jsonl("products"):
        rows.append((
            clean_str(r.get("product")),
            clean_str(r.get("productType")),
            clean_str(r.get("productOldId")),
            clean_str(r.get("productGroup")),
            clean_str(r.get("baseUnit")),
            safe_float(r.get("grossWeight")),
            safe_float(r.get("netWeight")),
            clean_str(r.get("weightUnit")),
            clean_str(r.get("division")),
            clean_str(r.get("industrySector")),
            safe_int(r.get("isMarkedForDeletion")),
            parse_date(r.get("creationDate")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  products: {len(rows)} rows")


def load_product_descriptions(conn):
    rows = []
    for r in load_jsonl("product_descriptions"):
        rows.append((
            clean_str(r.get("product")),
            clean_str(r.get("language")),
            clean_str(r.get("productDescription")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO product_descriptions VALUES (?,?,?)
    """, rows)
    print(f"  product_descriptions: {len(rows)} rows")


def load_plants(conn):
    rows = []
    for r in load_jsonl("plants"):
        rows.append((
            clean_str(r.get("plant")),
            clean_str(r.get("plantName")),
            clean_str(r.get("salesOrganization")),
            clean_str(r.get("distributionChannel")),
            clean_str(r.get("division")),
            clean_str(r.get("factoryCalendar")),
            clean_str(r.get("addressId")),
            safe_int(r.get("isMarkedForArchiving")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO plants VALUES (?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  plants: {len(rows)} rows")


def load_sales_order_headers(conn):
    rows = []
    for r in load_jsonl("sales_order_headers"):
        rows.append((
            clean_str(r.get("salesOrder")),
            clean_str(r.get("salesOrderType")),
            clean_str(r.get("salesOrganization")),
            clean_str(r.get("distributionChannel")),
            clean_str(r.get("organizationDivision")),
            clean_str(r.get("soldToParty")),
            parse_date(r.get("creationDate")),
            clean_str(r.get("createdByUser")),
            clean_str(r.get("lastChangeDateTime")),
            safe_float(r.get("totalNetAmount")),
            clean_str(r.get("transactionCurrency")),
            parse_date(r.get("pricingDate")),
            parse_date(r.get("requestedDeliveryDate")),
            clean_str(r.get("overallDeliveryStatus")),
            clean_str(r.get("overallOrdReltdBillgStatus")),
            clean_str(r.get("headerBillingBlockReason")),
            clean_str(r.get("deliveryBlockReason")),
            clean_str(r.get("incotermsClassification")),
            clean_str(r.get("incotermsLocation1")),
            clean_str(r.get("customerPaymentTerms")),
            clean_str(r.get("totalCreditCheckStatus")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO sales_order_headers VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  sales_order_headers: {len(rows)} rows")


def load_sales_order_items(conn):
    rows = []
    for r in load_jsonl("sales_order_items"):
        rows.append((
            clean_str(r.get("salesOrder")),
            clean_str(r.get("salesOrderItem")),
            clean_str(r.get("salesOrderItemCategory")),
            clean_str(r.get("material")),
            safe_float(r.get("requestedQuantity")),
            clean_str(r.get("requestedQuantityUnit")),
            clean_str(r.get("transactionCurrency")),
            safe_float(r.get("netAmount")),
            clean_str(r.get("materialGroup")),
            clean_str(r.get("productionPlant")),
            clean_str(r.get("storageLocation")),
            clean_str(r.get("salesDocumentRjcnReason")),
            clean_str(r.get("itemBillingBlockReason")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO sales_order_items VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  sales_order_items: {len(rows)} rows")


def load_sales_order_schedule_lines(conn):
    rows = []
    for r in load_jsonl("sales_order_schedule_lines"):
        rows.append((
            clean_str(r.get("salesOrder")),
            clean_str(r.get("salesOrderItem")),
            clean_str(r.get("scheduleLine")),
            parse_date(r.get("confirmedDeliveryDate")),
            clean_str(r.get("orderQuantityUnit")),
            safe_float(r.get("confdOrderQtyByMatlAvailCheck")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO sales_order_schedule_lines VALUES (?,?,?,?,?,?)
    """, rows)
    print(f"  sales_order_schedule_lines: {len(rows)} rows")


def load_outbound_delivery_headers(conn):
    rows = []
    for r in load_jsonl("outbound_delivery_headers"):
        rows.append((
            clean_str(r.get("deliveryDocument")),
            clean_str(r.get("shippingPoint")),
            parse_date(r.get("creationDate")),
            parse_date(r.get("actualGoodsMovementDate")),
            clean_str(r.get("overallGoodsMovementStatus")),
            clean_str(r.get("overallPickingStatus")),
            clean_str(r.get("overallProofOfDeliveryStatus")),
            clean_str(r.get("headerBillingBlockReason")),
            clean_str(r.get("deliveryBlockReason")),
            clean_str(r.get("hdrGeneralIncompletionStatus")),
            parse_date(r.get("lastChangeDate")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO outbound_delivery_headers VALUES
        (?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  outbound_delivery_headers: {len(rows)} rows")


def load_outbound_delivery_items(conn):
    rows = []
    for r in load_jsonl("outbound_delivery_items"):
        rows.append((
            clean_str(r.get("deliveryDocument")),
            clean_str(r.get("deliveryDocumentItem")),
            clean_str(r.get("referenceSdDocument")),
            clean_str(r.get("referenceSdDocumentItem")),
            clean_str(r.get("plant")),
            clean_str(r.get("storageLocation")),
            safe_float(r.get("actualDeliveryQuantity")),
            clean_str(r.get("deliveryQuantityUnit")),
            clean_str(r.get("itemBillingBlockReason")),
            clean_str(r.get("batch")),
            parse_date(r.get("lastChangeDate")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO outbound_delivery_items VALUES
        (?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  outbound_delivery_items: {len(rows)} rows")


def _billing_header_row(r):
    return (
        clean_str(r.get("billingDocument")),
        clean_str(r.get("billingDocumentType")),
        parse_date(r.get("creationDate")),
        parse_date(r.get("billingDocumentDate")),
        clean_str(r.get("lastChangeDateTime")),
        safe_int(r.get("billingDocumentIsCancelled")),
        clean_str(r.get("cancelledBillingDocument")),
        safe_float(r.get("totalNetAmount")),
        clean_str(r.get("transactionCurrency")),
        clean_str(r.get("companyCode")),
        clean_str(r.get("fiscalYear")),
        clean_str(r.get("accountingDocument")),
        clean_str(r.get("soldToParty")),
    )


def load_billing_document_headers(conn):
    rows = [_billing_header_row(r) for r in load_jsonl("billing_document_headers")]
    conn.executemany("""
        INSERT OR REPLACE INTO billing_document_headers VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  billing_document_headers: {len(rows)} rows")


def load_billing_document_cancellations(conn):
    rows = [_billing_header_row(r) for r in load_jsonl("billing_document_cancellations")]
    conn.executemany("""
        INSERT OR REPLACE INTO billing_document_cancellations VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  billing_document_cancellations: {len(rows)} rows")


def load_billing_document_items(conn):
    rows = []
    for r in load_jsonl("billing_document_items"):
        rows.append((
            clean_str(r.get("billingDocument")),
            clean_str(r.get("billingDocumentItem")),
            clean_str(r.get("material")),
            safe_float(r.get("billingQuantity")),
            clean_str(r.get("billingQuantityUnit")),
            safe_float(r.get("netAmount")),
            clean_str(r.get("transactionCurrency")),
            clean_str(r.get("referenceSdDocument")),
            clean_str(r.get("referenceSdDocumentItem")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO billing_document_items VALUES
        (?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  billing_document_items: {len(rows)} rows")


def load_journal_entry_items(conn):
    rows = []
    for r in load_jsonl("journal_entry_items_accounts_receivable"):
        rows.append((
            clean_str(r.get("companyCode")),
            clean_str(r.get("fiscalYear")),
            clean_str(r.get("accountingDocument")),
            clean_str(r.get("accountingDocumentItem")),
            clean_str(r.get("glAccount")),
            clean_str(r.get("referenceDocument")),
            clean_str(r.get("costCenter")),
            clean_str(r.get("profitCenter")),
            clean_str(r.get("transactionCurrency")),
            safe_float(r.get("amountInTransactionCurrency")),
            clean_str(r.get("companyCodeCurrency")),
            safe_float(r.get("amountInCompanyCodeCurrency")),
            parse_date(r.get("postingDate")),
            parse_date(r.get("documentDate")),
            clean_str(r.get("accountingDocumentType")),
            clean_str(r.get("assignmentReference")),
            clean_str(r.get("lastChangeDateTime")),
            clean_str(r.get("customer")),
            clean_str(r.get("financialAccountType")),
            parse_date(r.get("clearingDate")),
            clean_str(r.get("clearingAccountingDocument")),
            clean_str(r.get("clearingDocFiscalYear")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO journal_entry_items VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  journal_entry_items: {len(rows)} rows")


def load_payments(conn):
    rows = []
    for r in load_jsonl("payments_accounts_receivable"):
        rows.append((
            clean_str(r.get("companyCode")),
            clean_str(r.get("fiscalYear")),
            clean_str(r.get("accountingDocument")),
            clean_str(r.get("accountingDocumentItem")),
            parse_date(r.get("clearingDate")),
            clean_str(r.get("clearingAccountingDocument")),
            clean_str(r.get("clearingDocFiscalYear")),
            safe_float(r.get("amountInTransactionCurrency")),
            clean_str(r.get("transactionCurrency")),
            safe_float(r.get("amountInCompanyCodeCurrency")),
            clean_str(r.get("companyCodeCurrency")),
            clean_str(r.get("customer")),
            clean_str(r.get("invoiceReference")),
            clean_str(r.get("salesDocument")),
            clean_str(r.get("salesDocumentItem")),
            parse_date(r.get("postingDate")),
            parse_date(r.get("documentDate")),
            clean_str(r.get("assignmentReference")),
            clean_str(r.get("glAccount")),
            clean_str(r.get("financialAccountType")),
            clean_str(r.get("profitCenter")),
            clean_str(r.get("costCenter")),
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO payments_accounts_receivable VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    print(f"  payments_accounts_receivable: {len(rows)} rows")


# ─── Validation ───────────────────────────────────────────────────────────────

def validate(conn):
    """
    Sanity-check the joins that the query layer will rely on.
    Orphan counts ideally = 0. Some orphans are OK if the dataset
    is a filtered extract; we just want to know up front.
    """
    checks = [
        ("SO headers → business_partners (sold_to_party)",
         """SELECT COUNT(*) FROM sales_order_headers h
            LEFT JOIN business_partners bp ON h.sold_to_party = bp.business_partner
            WHERE bp.business_partner IS NULL"""),

        ("SO items → SO headers",
         """SELECT COUNT(*) FROM sales_order_items i
            LEFT JOIN sales_order_headers h ON i.sales_order = h.sales_order
            WHERE h.sales_order IS NULL"""),

        ("Delivery items → SO headers (reference_sd_document)",
         """SELECT COUNT(*) FROM outbound_delivery_items di
            LEFT JOIN sales_order_headers h ON di.reference_sd_document = h.sales_order
            WHERE h.sales_order IS NULL"""),

        ("Billing items → delivery headers (reference_sd_document)",
         """SELECT COUNT(*) FROM billing_document_items bi
            LEFT JOIN outbound_delivery_headers dh ON bi.reference_sd_document = dh.delivery_document
            WHERE dh.delivery_document IS NULL"""),

        ("Journal entries → billing headers (reference_document)",
         """SELECT COUNT(*) FROM journal_entry_items j
            LEFT JOIN billing_document_headers b ON j.reference_document = b.billing_document
            WHERE b.billing_document IS NULL"""),

        ("Payments → business_partners",
         """SELECT COUNT(*) FROM payments_accounts_receivable p
            LEFT JOIN business_partners bp ON p.customer = bp.business_partner
            WHERE bp.business_partner IS NULL"""),
    ]

    print("\nValidation (orphan checks):")
    all_ok = True
    for name, sql in checks:
        count = conn.execute(sql).fetchone()[0]
        status = "OK" if count == 0 else f"WARN — {count} orphan(s)"
        if count > 0:
            all_ok = False
        print(f"  {'✓' if count == 0 else '!'} {name}: {status}")

    if all_ok:
        print("\n  All joins are clean.")
    else:
        print("\n  Some orphans found — this is normal for filtered extracts.")
        print("  The LLM query layer uses LEFT JOINs so these won't break queries.")


def print_summary(conn):
    tables = [
        "business_partners", "business_partner_addresses",
        "customer_company_assignments", "customer_sales_area_assignments",
        "products", "product_descriptions", "plants",
        "sales_order_headers", "sales_order_items", "sales_order_schedule_lines",
        "outbound_delivery_headers", "outbound_delivery_items",
        "billing_document_headers", "billing_document_items", "billing_document_cancellations",
        "journal_entry_items", "payments_accounts_receivable",
    ]
    print("\nFinal row counts:")
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<45} {n:>6} rows")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Apply schema
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    print("Schema applied.\n")

    # Ingest in dependency order (parents before children)
    print("Ingesting...")
    load_business_partners(conn)
    load_business_partner_addresses(conn)
    load_customer_company_assignments(conn)
    load_customer_sales_area_assignments(conn)
    load_products(conn)
    load_product_descriptions(conn)
    load_plants(conn)
    load_sales_order_headers(conn)
    load_sales_order_items(conn)
    load_sales_order_schedule_lines(conn)
    load_outbound_delivery_headers(conn)
    load_outbound_delivery_items(conn)
    load_billing_document_headers(conn)
    load_billing_document_cancellations(conn)
    load_billing_document_items(conn)
    load_journal_entry_items(conn)
    load_payments(conn)

    conn.commit()
    validate(conn)
    print_summary(conn)
    conn.close()

    print(f"\nDone. Database written to: {DB_PATH}")
    print(f"Size: {DB_PATH.stat().st_size / 1024:.1f} KB")