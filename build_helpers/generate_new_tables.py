# generate_new_tables.py
# Run AFTER the original generate_demo_data.py has populated the DB.
# Populates: suppliers, updates products.supplier_id, inventory, returns

import os, random
from datetime import timezone
from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine, text

load_dotenv()
fake = Faker()
random.seed(42)
Faker.seed(42)

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME')}"
)

with engine.begin() as conn:

    # ── 1. Suppliers ─────────────────────────────────────────────────────────
    supplier_countries = [
        "China", "Germany", "India", "Vietnam", "Bangladesh",
        "Turkey", "Mexico", "Italy", "South Korea", "Brazil"
    ]
    supplier_ids = []
    for i in range(10):
        result = conn.execute(text("""
            INSERT INTO suppliers (supplier_name, country, contact_email, status)
            VALUES (:name, :country, :email, :status)
            RETURNING supplier_id
        """), {
            "name":    fake.company(),
            "country": supplier_countries[i],
            "email":   fake.company_email(),
            "status":  random.choice(["active", "active", "active", "inactive"]),
        })
        supplier_ids.append(result.scalar())
    print(f"Inserted {len(supplier_ids)} suppliers")

    # ── 2. Assign supplier_id to existing products ────────────────────────────
    product_rows = conn.execute(text("SELECT product_id FROM products")).fetchall()
    for row in product_rows:
        conn.execute(text("""
            UPDATE products SET supplier_id = :sid WHERE product_id = :pid
        """), {"sid": random.choice(supplier_ids), "pid": row.product_id})
    print(f"Assigned supplier_id to {len(product_rows)} products")

    # ── 3. Inventory (one row per product) ───────────────────────────────────
    for row in product_rows:
        conn.execute(text("""
            INSERT INTO inventory (product_id, quantity_on_hand, reorder_threshold, last_updated)
            VALUES (:pid, :qty, :threshold, :updated)
        """), {
            "pid":       row.product_id,
            "qty":       random.randint(0, 500),
            "threshold": random.choice([10, 20, 25, 50]),
            "updated":   fake.date_time_between(start_date="-30d", end_date="now",
                             tzinfo=timezone.utc),
        })
    print(f"Inserted {len(product_rows)} inventory rows")

    # ── 4. Returns (only from cancelled/refunded orders) ─────────────────────
    # Fetch only order_items belonging to cancelled or refunded orders
    eligible = conn.execute(text("""
        SELECT oi.order_item_id, oi.order_id, oi.unit_price, oi.quantity
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        WHERE o.status IN ('cancelled', 'refunded')
    """)).fetchall()

    # Return ~60% of eligible items
    to_return = random.sample(eligible, k=int(len(eligible) * 0.6))
    reasons = ["defective", "wrong_item", "changed_mind", "not_as_described"]
    statuses = ["pending", "approved", "approved", "rejected", "refunded", "refunded"]

    for item in to_return:
        status = random.choice(statuses)
        # refund_amount only set when approved or refunded
        refund = (
            round(item.unit_price * random.randint(1, item.quantity), 2)
            if status in ("approved", "refunded") else None
        )
        conn.execute(text("""
            INSERT INTO returns (order_id, order_item_id, return_date, reason, status, refund_amount)
            VALUES (:oid, :oiid, :rdate, :reason, :status, :refund)
        """), {
            "oid":    item.order_id,
            "oiid":   item.order_item_id,
            "rdate":  fake.date_time_between(start_date="-60d", end_date="now",
                          tzinfo=timezone.utc),
            "reason": random.choice(reasons),
            "status": status,
            "refund": refund,
        })
    print(f"Inserted {len(to_return)} returns")

print("Done — 3 new tables populated and products.supplier_id assigned.")