PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─────────────────────────────────────────────
-- SUPPORTING / REFERENCE ENTITIES
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business_partners (
    business_partner            TEXT PRIMARY KEY,
    customer                    TEXT,
    business_partner_category   TEXT,
    business_partner_full_name  TEXT,
    business_partner_name       TEXT,
    business_partner_grouping   TEXT,
    correspondence_language     TEXT,
    created_by_user             TEXT,
    creation_date               TEXT,
    first_name                  TEXT,
    last_name                   TEXT,
    form_of_address             TEXT,
    industry                    TEXT,
    is_blocked                  INTEGER DEFAULT 0,
    is_marked_for_archiving     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS business_partner_addresses (
    business_partner    TEXT REFERENCES business_partners(business_partner),
    address_id          TEXT,
    city_name           TEXT,
    country             TEXT,
    postal_code         TEXT,
    region              TEXT,
    street_name         TEXT,
    address_time_zone   TEXT,
    validity_start_date TEXT,
    validity_end_date   TEXT,
    PRIMARY KEY (business_partner, address_id)
);

CREATE TABLE IF NOT EXISTS customer_company_assignments (
    customer                TEXT REFERENCES business_partners(business_partner),
    company_code            TEXT,
    reconciliation_account  TEXT,
    payment_terms           TEXT,
    customer_account_group  TEXT,
    deletion_indicator      INTEGER DEFAULT 0,
    PRIMARY KEY (customer, company_code)
);

CREATE TABLE IF NOT EXISTS customer_sales_area_assignments (
    customer                TEXT REFERENCES business_partners(business_partner),
    sales_organization      TEXT,
    distribution_channel    TEXT,
    division                TEXT,
    currency                TEXT,
    customer_payment_terms  TEXT,
    incoterms_classification TEXT,
    incoterms_location1     TEXT,
    shipping_condition      TEXT,
    delivery_priority       TEXT,
    PRIMARY KEY (customer, sales_organization, distribution_channel, division)
);

CREATE TABLE IF NOT EXISTS products (
    product             TEXT PRIMARY KEY,
    product_type        TEXT,
    product_old_id      TEXT,
    product_group       TEXT,
    base_unit           TEXT,
    gross_weight        REAL,
    net_weight          REAL,
    weight_unit         TEXT,
    division            TEXT,
    industry_sector     TEXT,
    is_marked_for_deletion INTEGER DEFAULT 0,
    creation_date       TEXT
);

CREATE TABLE IF NOT EXISTS product_descriptions (
    product         TEXT REFERENCES products(product),
    language        TEXT,
    description     TEXT,
    PRIMARY KEY (product, language)
);

CREATE TABLE IF NOT EXISTS plants (
    plant               TEXT PRIMARY KEY,
    plant_name          TEXT,
    sales_organization  TEXT,
    distribution_channel TEXT,
    division            TEXT,
    factory_calendar    TEXT,
    address_id          TEXT,
    is_marked_for_archiving INTEGER DEFAULT 0
);

-- ─────────────────────────────────────────────
-- CORE O2C FLOW
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_order_headers (
    sales_order                     TEXT PRIMARY KEY,
    sales_order_type                TEXT,
    sales_organization              TEXT,
    distribution_channel            TEXT,
    organization_division           TEXT,
    sold_to_party                   TEXT REFERENCES business_partners(business_partner),
    creation_date                   TEXT,
    created_by_user                 TEXT,
    last_change_datetime            TEXT,
    total_net_amount                REAL,
    transaction_currency            TEXT,
    pricing_date                    TEXT,
    requested_delivery_date         TEXT,
    overall_delivery_status         TEXT,
    overall_billing_status          TEXT,
    header_billing_block_reason     TEXT,
    delivery_block_reason           TEXT,
    incoterms_classification        TEXT,
    incoterms_location1             TEXT,
    customer_payment_terms          TEXT,
    total_credit_check_status       TEXT
);

CREATE TABLE IF NOT EXISTS sales_order_items (
    sales_order             TEXT REFERENCES sales_order_headers(sales_order),
    sales_order_item        TEXT,
    sales_order_item_category TEXT,
    material                TEXT REFERENCES products(product),
    requested_quantity      REAL,
    requested_quantity_unit TEXT,
    transaction_currency    TEXT,
    net_amount              REAL,
    material_group          TEXT,
    production_plant        TEXT REFERENCES plants(plant),
    storage_location        TEXT,
    rejection_reason        TEXT,
    item_billing_block      TEXT,
    PRIMARY KEY (sales_order, sales_order_item)
);

CREATE TABLE IF NOT EXISTS sales_order_schedule_lines (
    sales_order                 TEXT REFERENCES sales_order_headers(sales_order),
    sales_order_item            TEXT,
    schedule_line               TEXT,
    confirmed_delivery_date     TEXT,
    order_quantity_unit         TEXT,
    confirmed_order_qty         REAL,
    PRIMARY KEY (sales_order, sales_order_item, schedule_line)
);

CREATE TABLE IF NOT EXISTS outbound_delivery_headers (
    delivery_document               TEXT PRIMARY KEY,
    shipping_point                  TEXT,
    creation_date                   TEXT,
    actual_goods_movement_date      TEXT,
    overall_goods_movement_status   TEXT,
    overall_picking_status          TEXT,
    overall_proof_of_delivery_status TEXT,
    header_billing_block_reason     TEXT,
    delivery_block_reason           TEXT,
    hdr_general_incompletion_status TEXT,
    last_change_date                TEXT
);

CREATE TABLE IF NOT EXISTS outbound_delivery_items (
    delivery_document       TEXT REFERENCES outbound_delivery_headers(delivery_document),
    delivery_document_item  TEXT,
    reference_sd_document   TEXT REFERENCES sales_order_headers(sales_order),
    reference_sd_document_item TEXT,
    plant                   TEXT REFERENCES plants(plant),
    storage_location        TEXT,
    actual_delivery_quantity REAL,
    delivery_quantity_unit  TEXT,
    item_billing_block      TEXT,
    batch                   TEXT,
    last_change_date        TEXT,
    PRIMARY KEY (delivery_document, delivery_document_item)
);

CREATE TABLE IF NOT EXISTS billing_document_headers (
    billing_document            TEXT PRIMARY KEY,
    billing_document_type       TEXT,
    creation_date               TEXT,
    billing_document_date       TEXT,
    last_change_datetime        TEXT,
    billing_document_is_cancelled INTEGER DEFAULT 0,
    cancelled_billing_document  TEXT,
    total_net_amount            REAL,
    transaction_currency        TEXT,
    company_code                TEXT,
    fiscal_year                 TEXT,
    accounting_document         TEXT,
    sold_to_party               TEXT REFERENCES business_partners(business_partner)
);

CREATE TABLE IF NOT EXISTS billing_document_items (
    billing_document            TEXT REFERENCES billing_document_headers(billing_document),
    billing_document_item       TEXT,
    material                    TEXT REFERENCES products(product),
    billing_quantity            REAL,
    billing_quantity_unit       TEXT,
    net_amount                  REAL,
    transaction_currency        TEXT,
    reference_sd_document       TEXT,   -- delivery document
    reference_sd_document_item  TEXT,
    PRIMARY KEY (billing_document, billing_document_item)
);

CREATE TABLE IF NOT EXISTS billing_document_cancellations (
    billing_document            TEXT PRIMARY KEY,
    billing_document_type       TEXT,
    creation_date               TEXT,
    billing_document_date       TEXT,
    last_change_datetime        TEXT,
    billing_document_is_cancelled INTEGER DEFAULT 0,
    cancelled_billing_document  TEXT,
    total_net_amount            REAL,
    transaction_currency        TEXT,
    company_code                TEXT,
    fiscal_year                 TEXT,
    accounting_document         TEXT,
    sold_to_party               TEXT
);

CREATE TABLE IF NOT EXISTS journal_entry_items (
    company_code                TEXT,
    fiscal_year                 TEXT,
    accounting_document         TEXT,
    accounting_document_item    TEXT,
    gl_account                  TEXT,
    reference_document          TEXT,   -- links back to billing_document
    cost_center                 TEXT,
    profit_center               TEXT,
    transaction_currency        TEXT,
    amount_in_transaction_currency REAL,
    company_code_currency       TEXT,
    amount_in_company_code_currency REAL,
    posting_date                TEXT,
    document_date               TEXT,
    accounting_document_type    TEXT,
    assignment_reference        TEXT,
    last_change_datetime        TEXT,
    customer                    TEXT REFERENCES business_partners(business_partner),
    financial_account_type      TEXT,
    clearing_date               TEXT,
    clearing_accounting_document TEXT,
    clearing_doc_fiscal_year    TEXT,
    PRIMARY KEY (company_code, fiscal_year, accounting_document, accounting_document_item)
);

CREATE TABLE IF NOT EXISTS payments_accounts_receivable (
    company_code                TEXT,
    fiscal_year                 TEXT,
    accounting_document         TEXT,
    accounting_document_item    TEXT,
    clearing_date               TEXT,
    clearing_accounting_document TEXT,
    clearing_doc_fiscal_year    TEXT,
    amount_in_transaction_currency REAL,
    transaction_currency        TEXT,
    amount_in_company_code_currency REAL,
    company_code_currency       TEXT,
    customer                    TEXT REFERENCES business_partners(business_partner),
    invoice_reference           TEXT,
    sales_document              TEXT,
    sales_document_item         TEXT,
    posting_date                TEXT,
    document_date               TEXT,
    assignment_reference        TEXT,
    gl_account                  TEXT,
    financial_account_type      TEXT,
    profit_center               TEXT,
    cost_center                 TEXT,
    PRIMARY KEY (company_code, fiscal_year, accounting_document, accounting_document_item)
);

-- ─────────────────────────────────────────────
-- USEFUL INDEXES FOR QUERY PERFORMANCE
-- ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_so_items_so ON sales_order_items(sales_order);
CREATE INDEX IF NOT EXISTS idx_so_items_material ON sales_order_items(material);
CREATE INDEX IF NOT EXISTS idx_delivery_items_so ON outbound_delivery_items(reference_sd_document);
CREATE INDEX IF NOT EXISTS idx_delivery_items_delivery ON outbound_delivery_items(delivery_document);
CREATE INDEX IF NOT EXISTS idx_billing_hdr_sold_to ON billing_document_headers(sold_to_party);
CREATE INDEX IF NOT EXISTS idx_billing_hdr_acct_doc ON billing_document_headers(accounting_document);
CREATE INDEX IF NOT EXISTS idx_billing_items_billing ON billing_document_items(billing_document);
CREATE INDEX IF NOT EXISTS idx_billing_items_ref_doc ON billing_document_items(reference_sd_document);
CREATE INDEX IF NOT EXISTS idx_je_ref_doc ON journal_entry_items(reference_document);
CREATE INDEX IF NOT EXISTS idx_je_customer ON journal_entry_items(customer);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments_accounts_receivable(customer);
CREATE INDEX IF NOT EXISTS idx_payments_clearing ON payments_accounts_receivable(clearing_accounting_document);