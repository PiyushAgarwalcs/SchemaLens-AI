DROP TABLE IF EXISTS order_items, orders, marketing_campaigns, products, customers CASCADE;

CREATE TABLE customers (
    customer_id     SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    signup_date     DATE,
    country         VARCHAR(100),
    segment         VARCHAR(50),   -- ambiguous: customer tier? RFM segment? marketing segment?
    status          VARCHAR(50)    -- ambiguous: active/inactive/churned?
);

CREATE TABLE products (
    product_id      SERIAL PRIMARY KEY,
    product_name    VARCHAR(200),
    category        VARCHAR(100),
    price           NUMERIC(10,2),
    status          VARCHAR(50)    -- active/discontinued/out_of_stock
);

CREATE TABLE marketing_campaigns (
    campaign_id     SERIAL PRIMARY KEY,
    campaign_name   VARCHAR(200),
    channel         VARCHAR(50),   -- email/social_media/paid_search/affiliate
    start_date      DATE,
    end_date        DATE,
    budget          NUMERIC(10,2),
    status          VARCHAR(50)    -- active/completed/paused
);

CREATE TABLE orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INT REFERENCES customers(customer_id),
    order_date      TIMESTAMP,
    status          VARCHAR(50),   -- pending/processing/shipped/delivered/cancelled/refunded
    channel         VARCHAR(50),   -- web/mobile_app/marketplace/in_store
    total_amount    NUMERIC(10,2)
);

CREATE TABLE order_items (
    order_item_id   SERIAL PRIMARY KEY,
    order_id        INT REFERENCES orders(order_id),
    product_id      INT REFERENCES products(product_id),
    quantity        INT,
    unit_price      NUMERIC(10,2)
);
