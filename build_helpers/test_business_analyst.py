# test_business_analyst.py
import json
from agents.business_analyst import run_analysis, write_analysis

analysis = run_analysis()
write_analysis(analysis)

by_table = {t.table_name: t for t in analysis.tables}
expected = {"customers", "orders", "products", "order_items", "marketing_campaigns"}
assert set(by_table) == expected, f"Missing: {expected - set(by_table)}"

# --- Trap 1: channel (orders vs marketing_campaigns, no FK, no overlap) ---
for tbl in ("orders", "marketing_campaigns"):
    flagged = any(f.column == "channel" for f in by_table[tbl].ambiguity_flags)
    relationship_text = by_table[tbl].relationships.lower()
    falsely_linked = "channel" in relationship_text and "marketing_campaigns" in relationship_text \
        if tbl == "orders" else "channel" in relationship_text and "orders" in relationship_text
    print(f"[{tbl}] channel flagged ambiguous: {flagged} | falsely linked: {falsely_linked}")

# --- Trap 2: status (4 tables, must be table-specific, not generic) ---
status_meanings = {}
for tbl in ("customers", "products", "orders", "marketing_campaigns"):
    meaning = next((c.meaning for c in by_table[tbl].column_meanings if c.column == "status"), None)
    status_meanings[tbl] = meaning
    print(f"[{tbl}] status meaning: {meaning}")
# eyeball check: are these 4 meaningfully different, or near-identical generic text?

# --- Trap 3: segment (customers only — simple, no cross-table risk) ---
seg = next((c.meaning for c in by_table["customers"].column_meanings if c.column == "segment"), None)
print(f"[customers] segment meaning: {seg}")

print("✅ Ran full pipeline; review printed output above for trap correctness.")