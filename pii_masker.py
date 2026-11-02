# pii_masker.py
#
# Column-name-based PII detection and masking.
# Strategy: check each column name against a set of known-sensitive patterns.
# If matched, replace every sample value in that column with [MASKED].
#
# This is intentionally conservative — false positives (masking a non-PII column)
# are far safer than false negatives (sending real PII to an LLM).
#
# Limitation: content-based detection (e.g. finding an email in a column called "notes")
# is out of scope for the hackathon. Log as a known extension path in README.

import re

# Each pattern is matched as a substring of the lowercased column name.
# Order doesn't matter — all matches are checked.
_PII_PATTERNS: list[str] = [
    # Identity
    "email",
    "e_mail",
    "phone",
    "mobile",
    "cell",
    "ssn",
    "social_security",
    "national_id",
    "passport",
    "license",
    "tax_id",
    "nid",

    # Auth / secrets
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "private_key",
    "auth",
    "credential",
    "otp",

    # Financial
    "credit_card",
    "card_number",
    "card_no",
    "cvv",
    "iban",
    "account_number",
    "account_no",
    "bank",
    "routing",

    # Location
    "address",
    "addr",
    "street",
    "zip",
    "postal",
    "latitude",
    "longitude",
    "lat",
    "lng",
    "lon",
    "gps",

    # Bio / health
    "dob",
    "date_of_birth",
    "birthdate",
    "birthday",
    "age",
    "gender",
    "race",
    "ethnicity",
    "diagnosis",
    "medical",
    "health",

    # Network / device
    "ip_address",
    "ip_addr",
    "mac_address",
    "device_id",
    "imei",
    "cookie",
    "session",

    # Names (conservative: flag explicit name columns, not generic "name")
    "first_name",
    "last_name",
    "full_name",
    "fname",
    "lname",
    "surname",
    "maiden",
]

# Pre-compile once as a single alternation pattern for speed
_PATTERN_RE = re.compile(
    "|".join(re.escape(p) for p in _PII_PATTERNS),
    re.IGNORECASE,
)

MASK_VALUE = "[MASKED]"


def is_pii_column(column_name: str) -> bool:
    """Return True if the column name matches any known PII pattern."""
    return bool(_PATTERN_RE.search(column_name))


def mask_row(row: dict, pii_columns: set[str]) -> dict:
    """Return a copy of `row` with PII column values replaced by MASK_VALUE."""
    return {
        col: (MASK_VALUE if col in pii_columns else val)
        for col, val in row.items()
    }


def mask_sample_rows(
    rows: list[dict],
    column_names: list[str],
) -> list[dict]:
    """
    Mask PII values in a list of sample row dicts.

    Args:
        rows:         Raw sample rows (list of dicts from sample_rows()).
        column_names: All column names for this table (used to detect PII columns).

    Returns:
        New list of dicts with PII values replaced by MASK_VALUE.
    """
    pii_columns = {col for col in column_names if is_pii_column(col)}
    if not pii_columns:
        return rows
    return [mask_row(row, pii_columns) for row in rows]


def pii_columns_in_table(column_names: list[str]) -> list[str]:
    """Return only the column names that are flagged as PII — useful for logging/UI."""
    return [col for col in column_names if is_pii_column(col)]