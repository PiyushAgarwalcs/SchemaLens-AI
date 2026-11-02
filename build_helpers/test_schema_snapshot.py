# test_schema_snapshot.py

from schema_snapshot import collect_schema_and_samples

data = collect_schema_and_samples()
found = {t["table_name"] for t in data}
expected = {"customers", "orders", "products", "order_items", "marketing_campaigns"}

assert found == expected, f"Missing tables: {expected - found}"
for t in data:
    assert t["columns"], f"{t['table_name']} has no columns"
    assert t["sample_rows"], f"{t['table_name']} has no sample rows"
print("✅ Schema snapshot complete for all 5 tables.")