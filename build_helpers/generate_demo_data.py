import os
import random
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values
from faker import Faker
from dotenv import load_dotenv

load_dotenv()
fake = Faker()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "schemalens"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
)
cur = conn.cursor()

N_CUSTOMERS = 80
N_PRODUCTS = 60
N_CAMPAIGNS = 15
N_ORDERS = 100

CUSTOMER_SEGMENTS = ["high_value", "regular", "at_risk", "new"]
CUSTOMER_STATUSES = ["active", "inactive", "churned"]
PRODUCT_CATEGORIES = ["electronics", "apparel", "home_goods", "beauty", "sports", "toys"]
PRODUCT_STATUSES = ["active", "discontinued", "out_of_stock"]
ORDER_CHANNELS = ["web", "mobile_app", "marketplace", "in_store"]
CAMPAIGN_CHANNELS = ["email", "social_media", "paid_search", "affiliate"]
CAMPAIGN_STATUSES = ["active", "completed", "paused"]

# 1. Customers
customers = [
    (
        fake.unique.email(),
        fake.first_name(),
        fake.last_name(),
        fake.date_between(start_date="-3y", end_date="-1m"),
        fake.country(),
        random.choice(CUSTOMER_SEGMENTS),
        random.choice(CUSTOMER_STATUSES),
    )
    for _ in range(N_CUSTOMERS)
]
execute_values(cur, """
    INSERT INTO customers (email, first_name, last_name, signup_date, country, segment, status)
    VALUES %s
""", customers)
conn.commit()

cur.execute("SELECT customer_id, signup_date FROM customers")
customer_signup = {r[0]: r[1] for r in cur.fetchall()}
customer_ids = list(customer_signup.keys())

# 2. Products
products = [
    (
        fake.catch_phrase(),
        random.choice(PRODUCT_CATEGORIES),
        round(random.uniform(5, 500), 2),
        random.choice(PRODUCT_STATUSES),
    )
    for _ in range(N_PRODUCTS)
]
execute_values(cur, """
    INSERT INTO products (product_name, category, price, status)
    VALUES %s
""", products)
conn.commit()

cur.execute("SELECT product_id, price FROM products")
product_rows = cur.fetchall()
product_ids = [r[0] for r in product_rows]
product_prices = {r[0]: r[1] for r in product_rows}

# 3. Marketing campaigns (no FK to anything else — intentional ambiguity trap)
# FIX: only "completed" campaigns get a real end_date. active/paused = NULL (still running).
campaigns = []
for _ in range(N_CAMPAIGNS):
    start = fake.date_between(start_date="-2y", end_date="-2m")
    status = random.choice(CAMPAIGN_STATUSES)
    end = start + timedelta(days=random.randint(7, 60)) if status == "completed" else None
    campaigns.append((
        fake.bs().title(),
        random.choice(CAMPAIGN_CHANNELS),
        start,
        end,
        round(random.uniform(500, 20000), 2),
        status,
    ))
execute_values(cur, """
    INSERT INTO marketing_campaigns (campaign_name, channel, start_date, end_date, budget, status)
    VALUES %s
""", campaigns)
conn.commit()

# 4. Orders (total_amount placeholder, backfilled after order_items)
# FIX 1: order_date can't be before the customer's signup_date.
# FIX 2: status now derives from order age instead of being picked independently
#        (a "pending" order from 11 months ago is impossible).
orders = []
for _ in range(N_ORDERS):
    cid = random.choice(customer_ids)
    earliest = max(customer_signup[cid], (datetime.now() - timedelta(days=365)).date())
    order_date = fake.date_time_between(start_date=earliest, end_date="now")
    days_old = (datetime.now() - order_date).days

    if days_old < 1:
        status = random.choice(["pending", "processing"])
    elif days_old < 3:
        status = random.choice(["processing", "shipped"])
    elif days_old < 7:
        status = random.choice(["shipped", "delivered", "cancelled"])
    else:
        status = random.choice(["delivered", "cancelled", "refunded"])

    orders.append((cid, order_date, status, random.choice(ORDER_CHANNELS), 0.00))

execute_values(cur, """
    INSERT INTO orders (customer_id, order_date, status, channel, total_amount)
    VALUES %s
""", orders)
conn.commit()

cur.execute("SELECT order_id FROM orders")
order_ids = [r[0] for r in cur.fetchall()]

# 5. Order items (1-5 per order, references real product_ids, no duplicates per order)
order_items = []
order_totals = {oid: 0.0 for oid in order_ids}
for oid in order_ids:
    chosen_products = random.sample(product_ids, random.randint(1, 5))
    for pid in chosen_products:
        qty = random.randint(1, 4)
        unit_price = float(product_prices[pid])
        order_items.append((oid, pid, qty, unit_price))
        order_totals[oid] += qty * unit_price

execute_values(cur, """
    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
    VALUES %s
""", order_items)
conn.commit()

# 6. Backfill order totals so they match their order_items exactly
for oid, total in order_totals.items():
    cur.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (round(total, 2), oid))
conn.commit()

cur.close()
conn.close()
print(f"Done: {N_CUSTOMERS} customers, {N_PRODUCTS} products, {N_CAMPAIGNS} campaigns, "
      f"{N_ORDERS} orders, {len(order_items)} order_items")
