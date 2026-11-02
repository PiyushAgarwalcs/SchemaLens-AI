# test_pii_masker.py
# Standalone — no DB connection needed.

from pii_masker import is_pii_column, mask_sample_rows, pii_columns_in_table, MASK_VALUE

# ── is_pii_column ─────────────────────────────────────────────────────────────
def test_positive_matches():
    cases = [
        "email", "customer_email", "EMAIL",
        "first_name", "last_name", "full_name",
        "phone", "phone_number", "mobile",
        "password", "hashed_password",
        "ssn", "social_security_number",
        "ip_address", "ip_addr",
        "credit_card", "card_number",
        "address", "street_address", "billing_address",
        "date_of_birth", "dob", "birthdate",
        "api_key", "auth_token", "session_token",
    ]
    for col in cases:
        assert is_pii_column(col), f"Expected PII match for: {col}"
    print(f"✅ is_pii_column — {len(cases)} positive cases passed")


def test_negative_matches():
    safe = [
        "customer_id", "order_id", "product_id",
        "total_amount", "unit_price", "budget",
        "status", "channel", "segment", "category",
        "signup_date", "order_date", "start_date", "end_date",
        "country", "quantity",
    ]
    for col in safe:
        assert not is_pii_column(col), f"Unexpected PII match for: {col}"
    print(f"✅ is_pii_column — {len(safe)} negative cases passed")


# ── mask_sample_rows ──────────────────────────────────────────────────────────
def test_masking_replaces_pii_values():
    rows = [
        {"customer_id": 1, "email": "alice@example.com", "first_name": "Alice", "country": "Kenya"},
        {"customer_id": 2, "email": "bob@example.com",   "first_name": "Bob",   "country": "Brazil"},
    ]
    columns = ["customer_id", "email", "first_name", "country"]
    result = mask_sample_rows(rows, columns)

    assert result[0]["email"]      == MASK_VALUE, "email not masked"
    assert result[0]["first_name"] == MASK_VALUE, "first_name not masked"
    assert result[0]["customer_id"] == 1,         "customer_id should NOT be masked"
    assert result[0]["country"]    == "Kenya",    "country should NOT be masked"

    assert result[1]["email"]      == MASK_VALUE
    assert result[1]["first_name"] == MASK_VALUE
    assert result[1]["customer_id"] == 2
    print("✅ mask_sample_rows — PII values masked, safe values untouched")


def test_masking_does_not_mutate_original():
    rows = [{"email": "alice@example.com", "customer_id": 1}]
    columns = ["email", "customer_id"]
    _ = mask_sample_rows(rows, columns)
    assert rows[0]["email"] == "alice@example.com", "Original rows should not be mutated"
    print("✅ mask_sample_rows — original rows not mutated")


def test_no_pii_columns_returns_unchanged():
    rows = [{"order_id": 1, "total_amount": "99.99", "status": "delivered"}]
    columns = ["order_id", "total_amount", "status"]
    result = mask_sample_rows(rows, columns)
    assert result == rows, "No-PII table should return rows unchanged"
    print("✅ mask_sample_rows — no-PII table returned as-is")


def test_pii_columns_in_table():
    columns = ["customer_id", "email", "first_name", "country", "signup_date"]
    flagged = pii_columns_in_table(columns)
    assert set(flagged) == {"email", "first_name"}, f"Got: {flagged}"
    print(f"✅ pii_columns_in_table — correctly identified: {flagged}")


# ── Simulate customers table ──────────────────────────────────────────────────
def test_customers_table_simulation():
    """Simulate what would happen to the customers table in the demo DB."""
    sample = [
        {"customer_id": 1, "email": "jason03@example.net", "first_name": "Lisa",
         "last_name": "Diaz", "signup_date": "2024-10-11", "country": "Palestinian Territory",
         "segment": "at_risk", "status": "inactive"},
        {"customer_id": 2, "email": "april04@example.org", "first_name": "Joshua",
         "last_name": "Bailey", "signup_date": "2024-05-11", "country": "Kenya",
         "segment": "new", "status": "inactive"},
    ]
    columns = ["customer_id", "email", "first_name", "last_name",
               "signup_date", "country", "segment", "status"]

    result = mask_sample_rows(sample, columns)

    for row in result:
        assert row["email"]      == MASK_VALUE
        assert row["first_name"] == MASK_VALUE
        assert row["last_name"]  == MASK_VALUE
        assert row["customer_id"] not in (MASK_VALUE,)
        assert row["country"] not in (MASK_VALUE,)
        assert row["segment"] not in (MASK_VALUE,)
        assert row["status"]  not in (MASK_VALUE,)

    print("✅ customers table simulation — email/first_name/last_name masked, rest intact")


if __name__ == "__main__":
    test_positive_matches()
    test_negative_matches()
    test_masking_replaces_pii_values()
    test_masking_does_not_mutate_original()
    test_no_pii_columns_returns_unchanged()
    test_pii_columns_in_table()
    test_customers_table_simulation()
    print("\n✅ All PII masker tests passed.")