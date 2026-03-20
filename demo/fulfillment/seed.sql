-- Order fulfillment demo: multi-warehouse routing, returns, exchanges,
-- payments, notifications, and risk/compliance.

CREATE TABLE IF NOT EXISTS products (
    product_id         TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    price              REAL NOT NULL,
    weight_kg          REAL NOT NULL,
    return_window_days INTEGER NOT NULL DEFAULT 30
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id  TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    region       TEXT NOT NULL,
    loyalty_tier TEXT NOT NULL  -- standard | gold | vip
);

CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    region       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    warehouse_id TEXT NOT NULL,
    product_id   TEXT NOT NULL,
    quantity_available INTEGER NOT NULL,
    PRIMARY KEY (warehouse_id, product_id)
);

CREATE TABLE IF NOT EXISTS shipping_rates (
    from_region   TEXT NOT NULL,
    to_region     TEXT NOT NULL,
    rate_per_kg   REAL NOT NULL,
    base_fee      REAL NOT NULL,
    delivery_days INTEGER NOT NULL,
    PRIMARY KEY (from_region, to_region)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    product_id    TEXT NOT NULL,
    quantity      INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    total         REAL,
    delivery_days INTEGER,
    order_date    TEXT  -- ISO date, NULL for new pending orders
);

CREATE TABLE IF NOT EXISTS returns (
    return_id     TEXT PRIMARY KEY,
    order_id      TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    refund_amount REAL,
    reason        TEXT
);

CREATE TABLE IF NOT EXISTS payment_methods (
    payment_id   TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL,
    method_type  TEXT NOT NULL,  -- credit_card | debit_card | wallet
    last_four    TEXT NOT NULL,
    is_default   INTEGER NOT NULL DEFAULT 1,
    balance      REAL            -- only for wallet type
);

CREATE TABLE IF NOT EXISTS payments (
    transaction_id TEXT PRIMARY KEY,
    order_id       TEXT NOT NULL,
    payment_id     TEXT NOT NULL,
    amount         REAL NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',  -- pending | completed | failed | refunded
    created_at     TEXT
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    customer_id TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    phone       TEXT,
    preferred   TEXT NOT NULL DEFAULT 'email',  -- email | sms | both
    opted_out   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    order_id        TEXT NOT NULL,
    channel         TEXT NOT NULL,  -- email | sms
    template        TEXT NOT NULL,  -- order_confirmed | shipped | return_approved | payment_failed
    status          TEXT NOT NULL DEFAULT 'sent'
);

CREATE TABLE IF NOT EXISTS risk_rules (
    rule_id     TEXT PRIMARY KEY,
    rule_type   TEXT NOT NULL,  -- high_value | flagged_customer | region_mismatch
    threshold   REAL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    assessment_id TEXT PRIMARY KEY,
    order_id      TEXT NOT NULL,
    risk_score    REAL NOT NULL,  -- 0.0 to 1.0
    flags         TEXT,           -- JSON array of triggered rules
    decision      TEXT NOT NULL   -- approve | review | block
);

-- Warehouses
INSERT INTO warehouses VALUES ('WH-1', 'East Coast Hub',    'east');
INSERT INTO warehouses VALUES ('WH-2', 'West Coast Hub',    'west');
INSERT INTO warehouses VALUES ('WH-3', 'Central Warehouse', 'central');
INSERT INTO warehouses VALUES ('WH-4', 'Southern Hub',      'south');

-- Products (no warehouse_id — use list_warehouses to find stock locations)
INSERT INTO products VALUES ('P-101', 'Laptop Stand',        45.00,  1.2, 30);
INSERT INTO products VALUES ('P-102', 'USB Hub',             29.00,  0.3, 30);
INSERT INTO products VALUES ('P-103', 'Monitor Arm',         89.00,  3.5, 30);
INSERT INTO products VALUES ('P-104', 'Desk Lamp',           35.00,  0.8, 14);
INSERT INTO products VALUES ('P-105', 'Standing Desk',      299.00, 25.0, 30);
INSERT INTO products VALUES ('P-106', 'Wireless Mouse',      25.00,  0.2, 30);
INSERT INTO products VALUES ('P-107', 'Mechanical Keyboard', 149.00, 1.0, 30);
INSERT INTO products VALUES ('P-108', '4K Webcam',          199.00,  0.4, 14);

-- Customers
INSERT INTO customers VALUES ('C-301', 'Jordan Blake',  'east',    'standard');
INSERT INTO customers VALUES ('C-302', 'Morgan Chen',   'west',    'vip');
INSERT INTO customers VALUES ('C-303', 'Alex Rivera',   'central', 'gold');
INSERT INTO customers VALUES ('C-304', 'Sam Patel',     'west',    'vip');
INSERT INTO customers VALUES ('C-305', 'Taylor Kim',    'east',    'standard');
INSERT INTO customers VALUES ('C-306', 'Jamie Fox',     'east',    'gold');
INSERT INTO customers VALUES ('C-307', 'Riley Quinn',   'central', 'standard');
INSERT INTO customers VALUES ('C-308', 'Casey Brooks',  'west',    'vip');

-- Multi-warehouse inventory (each product at 2 warehouses)
INSERT INTO inventory VALUES ('WH-1', 'P-101', 50);
INSERT INTO inventory VALUES ('WH-2', 'P-101', 10);

INSERT INTO inventory VALUES ('WH-2', 'P-102', 30);
INSERT INTO inventory VALUES ('WH-3', 'P-102', 15);

INSERT INTO inventory VALUES ('WH-3', 'P-103',  0);   -- out of stock
INSERT INTO inventory VALUES ('WH-1', 'P-103',  0);   -- out of stock everywhere

INSERT INTO inventory VALUES ('WH-1', 'P-104', 25);
INSERT INTO inventory VALUES ('WH-3', 'P-104',  5);

INSERT INTO inventory VALUES ('WH-2', 'P-105', 10);
INSERT INTO inventory VALUES ('WH-1', 'P-105',  3);

INSERT INTO inventory VALUES ('WH-4', 'P-106', 100);
INSERT INTO inventory VALUES ('WH-1', 'P-106',  40);

INSERT INTO inventory VALUES ('WH-2', 'P-107',  5);
INSERT INTO inventory VALUES ('WH-4', 'P-107', 15);
INSERT INTO inventory VALUES ('WH-1', 'P-107',  0);   -- out of stock at WH-1

INSERT INTO inventory VALUES ('WH-3', 'P-108', 12);
INSERT INTO inventory VALUES ('WH-4', 'P-108',  8);
INSERT INTO inventory VALUES ('WH-2', 'P-108',  0);   -- out of stock at WH-2

-- Shipping rates (region-to-region)
INSERT INTO shipping_rates VALUES ('east',    'east',     2.00,  5.00, 2);
INSERT INTO shipping_rates VALUES ('east',    'west',     4.50, 10.00, 5);
INSERT INTO shipping_rates VALUES ('east',    'central',  3.00,  7.00, 3);
INSERT INTO shipping_rates VALUES ('west',    'east',     4.50, 10.00, 5);
INSERT INTO shipping_rates VALUES ('west',    'west',     2.00,  5.00, 2);
INSERT INTO shipping_rates VALUES ('west',    'central',  3.00,  7.00, 3);
INSERT INTO shipping_rates VALUES ('central', 'east',     3.00,  7.00, 3);
INSERT INTO shipping_rates VALUES ('central', 'west',     3.00,  7.00, 3);
INSERT INTO shipping_rates VALUES ('central', 'central',  1.50,  4.00, 1);
INSERT INTO shipping_rates VALUES ('south',   'south',    1.50,  4.00, 1);
INSERT INTO shipping_rates VALUES ('south',   'east',     3.50,  8.00, 3);
INSERT INTO shipping_rates VALUES ('south',   'west',     5.00, 12.00, 6);
INSERT INTO shipping_rates VALUES ('south',   'central',  2.50,  6.00, 2);
INSERT INTO shipping_rates VALUES ('east',    'south',    3.50,  8.00, 3);
INSERT INTO shipping_rates VALUES ('west',    'south',    5.00, 12.00, 6);
INSERT INTO shipping_rates VALUES ('central', 'south',    2.50,  6.00, 2);

-- Fulfillment orders (pending, no order_date)
-- ORD-201: P-101 to C-301(east,std)   — optimal WH-1(east) $52.40 / 2d
-- ORD-202: P-102 to C-302(west,vip)   — optimal WH-2(west) $31.70 / 2d
-- ORD-203: P-103 to C-303(central,gold) — all out of stock → backordered
-- ORD-204: P-104×3 to C-304(west,vip) — optimal WH-3(central) $108.70 / 3d
-- ORD-205: P-105 to C-305(east,std)   — optimal WH-1(east) $354.00 / 2d
INSERT INTO orders VALUES ('ORD-201', 'C-301', 'P-101', 1, 'pending', NULL, NULL, NULL);
INSERT INTO orders VALUES ('ORD-202', 'C-302', 'P-102', 1, 'pending', NULL, NULL, NULL);
INSERT INTO orders VALUES ('ORD-203', 'C-303', 'P-103', 1, 'pending', NULL, NULL, NULL);
INSERT INTO orders VALUES ('ORD-204', 'C-304', 'P-104', 3, 'pending', NULL, NULL, NULL);
INSERT INTO orders VALUES ('ORD-205', 'C-305', 'P-105', 1, 'pending', NULL, NULL, NULL);

-- Return orders (pre-fulfilled/backordered, with relative order_date)
-- ORD-301: within 30d window → eligible → refund $52.40
-- ORD-302: 45 days ago, past 30d window → NOT eligible
-- ORD-303: backordered → auto-eligible → refund $0
INSERT INTO orders VALUES ('ORD-301', 'C-301', 'P-101', 1, 'fulfilled', 52.40, 2, date('now', '-5 days'));
INSERT INTO orders VALUES ('ORD-302', 'C-302', 'P-102', 1, 'fulfilled', 31.70, 2, date('now', '-45 days'));
INSERT INTO orders VALUES ('ORD-303', 'C-303', 'P-103', 1, 'backordered', NULL, NULL, date('now', '-10 days'));

-- Exchange orders (original fulfilled + replacement pending)
-- ORD-401 original: C-304 bought P-101 from WH-2 → $47.90 / 2d, within 30d window
-- ORD-501 replacement: C-304 wants P-102 → optimal WH-2 $31.70 / 2d
-- ORD-402 original: C-305 bought P-104 from WH-1 → $41.60 / 2d, within 14d window
-- ORD-502 replacement: C-305 wants P-103 → all out of stock → backordered
INSERT INTO orders VALUES ('ORD-401', 'C-304', 'P-101', 1, 'fulfilled', 47.90, 2, date('now', '-8 days'));
INSERT INTO orders VALUES ('ORD-501', 'C-304', 'P-102', 1, 'pending', NULL, NULL, NULL);
INSERT INTO orders VALUES ('ORD-402', 'C-305', 'P-104', 1, 'fulfilled', 41.60, 2, date('now', '-5 days'));
INSERT INTO orders VALUES ('ORD-502', 'C-305', 'P-103', 1, 'pending', NULL, NULL, NULL);

-- Additional orders for expanded scenarios
--
-- ORD-206: P-105 $299 for C-303 (central, gold, FLAGGED)
--   risk: high_value(0.4) + flagged(0.5) = 0.9 → BLOCKED
INSERT INTO orders VALUES ('ORD-206', 'C-303', 'P-105', 1, 'pending', NULL, NULL, NULL);
-- ORD-207: P-105 $299 for C-302 (west, vip 10%)
--   risk: high_value(0.4) → review → override → approve
--   WH-2(west→west): 5+2*25=$55 2d → total: 299*0.90+55 = $324.10 / 2d
INSERT INTO orders VALUES ('ORD-207', 'C-302', 'P-105', 1, 'pending', NULL, NULL, NULL);
-- ORD-208: P-101 $45 for C-303 (central, gold 5%, FLAGGED)
--   risk: flagged(0.5) → review → override
--   WH-1(east→central): 7+3*1.2=$10.60 3d → total: 45*0.95+10.60 = $53.35 / 3d
--   wallet PM-301 has $0 → charge fails → retry PM-302 debit card
INSERT INTO orders VALUES ('ORD-208', 'C-303', 'P-101', 1, 'pending', NULL, NULL, NULL);
-- ORD-209: P-104 $35 for C-301 (east, standard)
--   WH-1(east→east): 5+2*0.8=$6.60 2d → total: $41.60 / 2d
--   customer wants SMS notification instead of default email
INSERT INTO orders VALUES ('ORD-209', 'C-301', 'P-104', 1, 'pending', NULL, NULL, NULL);
--
-- ORD-304: P-104 $35 for C-301 (east, standard), fulfilled recently
--   14d return window, 3 days ago → eligible → refund $41.60
INSERT INTO orders VALUES ('ORD-304', 'C-301', 'P-104', 1, 'fulfilled', 41.60, 2, date('now', '-3 days'));
-- ORD-305: P-102 $29 for C-305 (east, standard), fulfilled recently
--   30d return window, 8 days ago → eligible → refund $36.90
--   WH-3(central→east): 7+3*0.3=$7.90 3d was cheapest
INSERT INTO orders VALUES ('ORD-305', 'C-305', 'P-102', 1, 'fulfilled', 36.90, 3, date('now', '-8 days'));
--
-- ORD-403: C-303 bought P-102, return + replacement ORD-503 (P-104)
--   WH-3(central→central): 4+1.5*0.3=$4.45 1d → 29*0.95+4.45 = $32.00 / 1d
INSERT INTO orders VALUES ('ORD-403', 'C-303', 'P-102', 1, 'fulfilled', 32.00, 1, date('now', '-5 days'));
-- ORD-503: replacement P-104 for C-303 (central, gold 5%)
--   WH-3(central→central): 4+1.5*0.8=$5.20 1d → 35*0.95+5.20 = $38.45 / 1d
INSERT INTO orders VALUES ('ORD-503', 'C-303', 'P-104', 1, 'pending', NULL, NULL, NULL);
-- ORD-404: C-302 bought P-104, return + replacement ORD-504 (P-105)
--   WH-3(central→west): 7+3*0.8=$9.40 3d → 35*0.90+9.40 = $40.90 / 3d
INSERT INTO orders VALUES ('ORD-404', 'C-302', 'P-104', 1, 'fulfilled', 40.90, 3, date('now', '-5 days'));
-- ORD-504: replacement P-105 $299 for C-302 (west, vip 10%)
--   WH-2(west→west): 5+2*25=$55 2d → 299*0.90+55 = $324.10 / 2d
--   HIGH VALUE → risk review → override needed
INSERT INTO orders VALUES ('ORD-504', 'C-302', 'P-105', 1, 'pending', NULL, NULL, NULL);
--
-- Additional fulfillment orders for clustering density
-- ORD-210: P-102 $29 for C-301 (east, standard)
--   WH-3(central→east): 7+3*0.3=$7.90 3d → total: $29+7.90 = $36.90 / 3d
INSERT INTO orders VALUES ('ORD-210', 'C-301', 'P-102', 1, 'pending', NULL, NULL, NULL);
-- ORD-211: P-104 $35×2 for C-302 (west, vip 10%)
--   WH-3(central→west): 7+3*1.6=$11.80 3d → total: 70*0.90+11.80 = $74.80 / 3d
INSERT INTO orders VALUES ('ORD-211', 'C-302', 'P-104', 2, 'pending', NULL, NULL, NULL);
-- ORD-212: P-101 $45 for C-304 (west, vip 10%)
--   WH-2(west→west): 5+2*1.2=$7.40 2d → total: 45*0.90+7.40 = $47.90 / 2d
INSERT INTO orders VALUES ('ORD-212', 'C-304', 'P-101', 1, 'pending', NULL, NULL, NULL);
--
-- Additional return orders for clustering density
-- ORD-306: C-302 bought P-101, 30d window, 10 days ago → eligible
INSERT INTO orders VALUES ('ORD-306', 'C-302', 'P-101', 1, 'fulfilled', 47.90, 2, date('now', '-10 days'));
-- ORD-307: C-304 bought P-102, 30d window, 5 days ago → eligible
INSERT INTO orders VALUES ('ORD-307', 'C-304', 'P-102', 1, 'fulfilled', 31.70, 2, date('now', '-5 days'));
-- ORD-308: C-301 bought P-102, 30d window, 15 days ago → eligible
INSERT INTO orders VALUES ('ORD-308', 'C-301', 'P-102', 1, 'fulfilled', 36.90, 3, date('now', '-15 days'));
--
-- Additional exchange orders for clustering density
-- ORD-405: C-301 bought P-102, 30d window, 7 days ago → eligible
INSERT INTO orders VALUES ('ORD-405', 'C-301', 'P-102', 1, 'fulfilled', 36.90, 3, date('now', '-7 days'));
-- ORD-505: replacement P-104 for C-301 (east, std)
--   WH-1(east→east): 5+2*0.8=$6.60 2d → total: $35+6.60 = $41.60 / 2d
INSERT INTO orders VALUES ('ORD-505', 'C-301', 'P-104', 1, 'pending', NULL, NULL, NULL);
-- ORD-406: C-302 bought P-101, 30d window, 7 days ago → eligible
INSERT INTO orders VALUES ('ORD-406', 'C-302', 'P-101', 1, 'fulfilled', 47.90, 2, date('now', '-7 days'));
-- ORD-506: replacement P-102 for C-302 (west, vip 10%)
--   WH-2(west→west): 5+2*0.3=$5.60 2d → total: 29*0.90+5.60 = $31.70 / 2d
INSERT INTO orders VALUES ('ORD-506', 'C-302', 'P-102', 1, 'pending', NULL, NULL, NULL);
-- ORD-407: C-304 bought P-104, 14d window, 5 days ago → eligible
INSERT INTO orders VALUES ('ORD-407', 'C-304', 'P-104', 1, 'fulfilled', 40.90, 3, date('now', '-5 days'));
-- ORD-507: replacement P-101 for C-304 (west, vip 10%)
--   WH-2(west→west): 5+2*1.2=$7.40 2d → total: 45*0.90+7.40 = $47.90 / 2d
INSERT INTO orders VALUES ('ORD-507', 'C-304', 'P-101', 1, 'pending', NULL, NULL, NULL);

-- ============================================================
-- Expanded scenarios: new fulfillment, return, exchange orders
-- ============================================================
--
-- NEW FULFILLMENT (10)
--
-- ORD-213: P-101 $45 → C-302(west,vip) → WH-2(west→west) $7.40 2d → $47.90/2d
INSERT INTO orders VALUES ('ORD-213', 'C-302', 'P-101', 1, 'pending', NULL, NULL, NULL);
-- ORD-214: P-104 $35×3 → C-306(east,gold) → WH-1(east→east) $9.80 2d → $109.55/2d
INSERT INTO orders VALUES ('ORD-214', 'C-306', 'P-104', 3, 'pending', NULL, NULL, NULL);
-- ORD-215: P-105 $299 → C-308(west,vip) → WH-2(west→west) $55 2d → $324.10/2d + risk
INSERT INTO orders VALUES ('ORD-215', 'C-308', 'P-105', 1, 'pending', NULL, NULL, NULL);
-- ORD-216: P-102 $29 → C-301(east,std) → WH-3(central→east) $7.90 3d → $36.90/3d
INSERT INTO orders VALUES ('ORD-216', 'C-301', 'P-102', 1, 'pending', NULL, NULL, NULL);
-- ORD-217: P-106 $25×2 → C-307(central,std) → WH-4(south→central) $7.00 2d → $57.00/2d
INSERT INTO orders VALUES ('ORD-217', 'C-307', 'P-106', 2, 'pending', NULL, NULL, NULL);
-- ORD-218: P-107 $149 → C-306(east,gold) → WH-4(south→east) $11.50 3d → $153.05/3d
INSERT INTO orders VALUES ('ORD-218', 'C-306', 'P-107', 1, 'pending', NULL, NULL, NULL);
-- ORD-219: P-103 $89 → C-301(east,std) → all stock 0 → BACKORDERED
INSERT INTO orders VALUES ('ORD-219', 'C-301', 'P-103', 1, 'pending', NULL, NULL, NULL);
-- ORD-220: P-108 $199×2 → C-308(west,vip) → WH-3(central→west) $9.40 3d → $367.60/3d + risk
INSERT INTO orders VALUES ('ORD-220', 'C-308', 'P-108', 2, 'pending', NULL, NULL, NULL);
-- ORD-221: P-106 $25×5 → C-304(west,vip) → WH-1(east→west) $14.50 5d → $127.00/5d
INSERT INTO orders VALUES ('ORD-221', 'C-304', 'P-106', 5, 'pending', NULL, NULL, NULL);
-- ORD-222: P-107 $149 → C-303(central,gold,FLAGGED) → WH-4(south→central) $8.50 2d
--   → $150.05/2d, risk review→override, wallet $0→fail→debit
INSERT INTO orders VALUES ('ORD-222', 'C-303', 'P-107', 1, 'pending', NULL, NULL, NULL);
--
-- NEW RETURNS (3)
--
-- ORD-309: C-306 bought P-106, 30d window, 7 days ago → eligible → returned
--   WH-1(east→east): 5+2*0.2=$5.40 2d → total: 25*0.95+5.40=$29.15/2d
INSERT INTO orders VALUES ('ORD-309', 'C-306', 'P-106', 1, 'fulfilled', 29.15, 2, date('now', '-7 days'));
-- ORD-310: C-308 bought P-108, 14d window, 5 days ago → eligible → returned
--   WH-3(central→west): 7+3*0.4=$8.20 3d → total: 199*0.90+8.20=$187.30/3d
INSERT INTO orders VALUES ('ORD-310', 'C-308', 'P-108', 1, 'fulfilled', 187.30, 3, date('now', '-5 days'));
-- ORD-311: C-307 bought P-106, 30d window, 20 days ago → eligible → returned
--   WH-4(south→central): 6+2.5*0.2=$6.50 2d → total: 25+6.50=$31.50/2d
INSERT INTO orders VALUES ('ORD-311', 'C-307', 'P-106', 1, 'fulfilled', 31.50, 2, date('now', '-20 days'));
--
-- NEW EXCHANGES (3)
--
-- ORD-410: C-308(vip,west) bought P-107, 30d window, 7 days ago → eligible
--   total: 149*0.90 + WH-2(west→west) 5+2*1.0=$7.00 = $141.10/2d
INSERT INTO orders VALUES ('ORD-410', 'C-308', 'P-107', 1, 'fulfilled', 141.10, 2, date('now', '-7 days'));
-- ORD-510: replacement P-106 for C-308(west,vip)
--   WH-1(east→west): 10+4.5*0.2=$10.90 5d → total: 25*0.90+10.90=$33.40/5d
INSERT INTO orders VALUES ('ORD-510', 'C-308', 'P-106', 1, 'pending', NULL, NULL, NULL);
-- ORD-411: C-306(gold,east) bought P-108, 14d window, 5 days ago → eligible
--   total: 199*0.95 + WH-3(central→east) 7+3*0.4=$8.20 = $197.25/3d
INSERT INTO orders VALUES ('ORD-411', 'C-306', 'P-108', 1, 'fulfilled', 197.25, 3, date('now', '-5 days'));
-- ORD-511: replacement P-107 for C-306(east,gold)
--   WH-4(south→east): 8+3.5*1.0=$11.50 3d → total: 149*0.95+11.50=$153.05/3d
INSERT INTO orders VALUES ('ORD-511', 'C-306', 'P-107', 1, 'pending', NULL, NULL, NULL);
-- ORD-412: C-303(gold,flagged,central) bought P-106, 30d window, 7 days ago → eligible
--   total: 25*0.95 + WH-4(south→central) 6+2.5*0.2=$6.50 = $30.25/2d
INSERT INTO orders VALUES ('ORD-412', 'C-303', 'P-106', 1, 'fulfilled', 30.25, 2, date('now', '-7 days'));
-- ORD-512: replacement P-108 for C-303(central,gold,FLAGGED)
--   WH-3(central→central): 4+1.5*0.4=$4.60 1d → total: 199*0.95+4.60=$193.65/1d
--   risk: flagged→0.3→review→override; wallet $0→fail→debit
INSERT INTO orders VALUES ('ORD-512', 'C-303', 'P-108', 1, 'pending', NULL, NULL, NULL);

-- Payment methods
-- C-301: one credit card (default)
INSERT INTO payment_methods VALUES ('PM-101', 'C-301', 'credit_card', '4242', 1, NULL);
-- C-302: credit card (default) + wallet with $500
INSERT INTO payment_methods VALUES ('PM-201', 'C-302', 'credit_card', '5555', 1, NULL);
INSERT INTO payment_methods VALUES ('PM-202', 'C-302', 'wallet', '0001', 0, 500.00);
-- C-303: wallet with $0 (insufficient) + backup debit card
INSERT INTO payment_methods VALUES ('PM-301', 'C-303', 'wallet', '0002', 1, 0.00);
INSERT INTO payment_methods VALUES ('PM-302', 'C-303', 'debit_card', '8888', 0, NULL);
-- C-304: credit card (default)
INSERT INTO payment_methods VALUES ('PM-401', 'C-304', 'credit_card', '1234', 1, NULL);
-- C-305: debit card (default)
INSERT INTO payment_methods VALUES ('PM-501', 'C-305', 'debit_card', '9999', 1, NULL);
-- C-306: credit card (default) + wallet with $200
INSERT INTO payment_methods VALUES ('PM-601', 'C-306', 'credit_card', '7777', 1, NULL);
INSERT INTO payment_methods VALUES ('PM-602', 'C-306', 'wallet', '0003', 0, 200.00);
-- C-307: credit card (default)
INSERT INTO payment_methods VALUES ('PM-701', 'C-307', 'credit_card', '6666', 1, NULL);
-- C-308: credit card (default) + wallet with $1000 + debit card
INSERT INTO payment_methods VALUES ('PM-801', 'C-308', 'credit_card', '3333', 1, NULL);
INSERT INTO payment_methods VALUES ('PM-802', 'C-308', 'wallet', '0004', 0, 1000.00);
INSERT INTO payment_methods VALUES ('PM-803', 'C-308', 'debit_card', '4444', 0, NULL);

-- Notification preferences
INSERT INTO notification_preferences VALUES ('C-301', 'jordan@example.com', '+1-555-0101',   'email', 0);
INSERT INTO notification_preferences VALUES ('C-302', 'morgan@example.com', '+1-555-0102',   'both',  0);
INSERT INTO notification_preferences VALUES ('C-303', 'alex@example.com',   '+1-555-0103',   'sms',   0);
INSERT INTO notification_preferences VALUES ('C-304', 'sam@example.com',    '+1-555-0104',   'email', 0);
INSERT INTO notification_preferences VALUES ('C-305', 'taylor@example.com', '+1-555-0105',   'email', 1);  -- opted out
INSERT INTO notification_preferences VALUES ('C-306', 'jamie@example.com',  '+1-555-0106',   'both',  0);
INSERT INTO notification_preferences VALUES ('C-307', 'riley@example.com',   NULL,           'email', 0);  -- no phone
INSERT INTO notification_preferences VALUES ('C-308', 'casey@example.com',  '+1-555-0108',   'sms',   0);

-- Promotions
CREATE TABLE IF NOT EXISTS promotions (
    promotion_id TEXT PRIMARY KEY,
    product_id   TEXT NOT NULL,
    promo_type   TEXT NOT NULL,  -- percentage | fixed | bundle
    discount_value REAL NOT NULL,
    min_quantity INTEGER NOT NULL DEFAULT 1,
    required_tier TEXT,           -- NULL = any tier, or 'gold', 'vip'
    max_uses_per_customer INTEGER,  -- NULL = unlimited
    active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS promotion_usage (
    usage_id     TEXT PRIMARY KEY,
    promotion_id TEXT NOT NULL,
    customer_id  TEXT NOT NULL,
    order_id     TEXT NOT NULL
);

-- Inventory reservations
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id TEXT PRIMARY KEY,
    warehouse_id   TEXT NOT NULL,
    product_id     TEXT NOT NULL,
    quantity       INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active',  -- active | cancelled | fulfilled
    created_at     TEXT
);

CREATE TABLE IF NOT EXISTS restock_schedule (
    warehouse_id TEXT NOT NULL,
    product_id   TEXT NOT NULL,
    expected_date TEXT,
    quantity      INTEGER,
    PRIMARY KEY (warehouse_id, product_id)
);

-- Customer flags (data-driven risk flagging)
CREATE TABLE IF NOT EXISTS customer_flags (
    customer_id TEXT PRIMARY KEY,
    reason      TEXT NOT NULL,
    flagged_at  TEXT
);

-- Risk rules
INSERT INTO risk_rules VALUES ('RULE-1', 'high_value',       200.0,  'Orders over $200 require risk review');
INSERT INTO risk_rules VALUES ('RULE-2', 'flagged_customer',  NULL,  'Customer C-303 is flagged for suspicious activity');
INSERT INTO risk_rules VALUES ('RULE-3', 'region_mismatch',   NULL,  'Shipping to a different region than customer address');

-- Customer flags (replaces hardcoded C-303 check)
INSERT INTO customer_flags VALUES ('C-303', 'suspicious activity pattern', date('now', '-60 days'));

-- Promotions (agents may check these — they add exploration complexity)
-- PROMO-1: VIP-only, one-time use, 15% off P-101
INSERT INTO promotions VALUES ('PROMO-1', 'P-101', 'percentage', 15.0, 1, 'vip', 1, 1);
-- PROMO-2: $5 off P-102, requires qty ≥ 2
INSERT INTO promotions VALUES ('PROMO-2', 'P-102', 'fixed', 5.0, 2, NULL, NULL, 1);
-- PROMO-3: 10% off P-105, one-time use, any tier
INSERT INTO promotions VALUES ('PROMO-3', 'P-105', 'percentage', 10.0, 1, NULL, 1, 1);
-- PROMO-4: $10 off P-104 bundle, gold+ only, qty ≥ 3
INSERT INTO promotions VALUES ('PROMO-4', 'P-104', 'bundle', 10.0, 3, 'gold', NULL, 1);
-- PROMO-5: 20% off P-103, always active (but product is OOS)
INSERT INTO promotions VALUES ('PROMO-5', 'P-103', 'percentage', 20.0, 1, NULL, NULL, 1);
-- PROMO-6: $3 off P-101, anyone, unlimited
INSERT INTO promotions VALUES ('PROMO-6', 'P-101', 'fixed', 3.0, 1, NULL, NULL, 1);
-- PROMO-7: 5% off P-105, VIP only
INSERT INTO promotions VALUES ('PROMO-7', 'P-105', 'percentage', 5.0, 1, 'vip', NULL, 1);

-- Pre-seed: PROMO-1 already used by C-302 (cannot use again)
INSERT INTO promotion_usage VALUES ('USAGE-001', 'PROMO-1', 'C-302', 'ORD-HIST-001');

-- Restock schedule (for out-of-stock P-103)
INSERT INTO restock_schedule VALUES ('WH-3', 'P-103', date('now', '+14 days'), 20);
INSERT INTO restock_schedule VALUES ('WH-1', 'P-103', NULL, NULL);  -- no ETA
