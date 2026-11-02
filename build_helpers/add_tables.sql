-- add_tables.sql
-- Run AFTER schema.sql and generate_demo_data.py have already populated the DB.

-- 1. Suppliers (standalone)
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id     SERIAL PRIMARY KEY,
    supplier_name   VARCHAR(200),
    country         VARCHAR(100),   -- cross-table trap: same name as customers.country, no FK
    contact_email   VARCHAR(255),
    status          VARCHAR(50)     -- active/inactive
);

-- 2. Add supplier_id FK to products
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS supplier_id INT REFERENCES suppliers(supplier_id);

-- 3. Inventory (1-to-1 with products)
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id        SERIAL PRIMARY KEY,
    product_id          INT REFERENCES products(product_id),
    quantity_on_hand    INT,
    reorder_threshold   INT,
    last_updated        TIMESTAMP
);

-- 4. Returns (joins orders + order_items)
CREATE TABLE IF NOT EXISTS returns (
    return_id       SERIAL PRIMARY KEY,
    order_id        INT REFERENCES orders(order_id),
    order_item_id   INT REFERENCES order_items(order_item_id),
    return_date     TIMESTAMP,
    reason          VARCHAR(100),   -- defective/wrong_item/changed_mind/not_as_described
    status          VARCHAR(50),    -- pending/approved/rejected/refunded
    refund_amount   NUMERIC(10,2)
);