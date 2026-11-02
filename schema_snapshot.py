# schema_snapshot.py

import json
from pathlib import Path
from datetime import datetime, timezone
from connectors.postgres import get_engine, get_schema, sample_rows
from pii_masker import mask_sample_rows, pii_columns_in_table

OUTPUT_PATH = Path("data/schema_snapshot.json")


def collect_schema_and_samples(pii_masking: bool = True) -> list[dict]:
    """Plain, deterministic schema + sample collection. No LLM involved —
    nothing here needs reasoning, so nothing here gets one.

    Args:
        pii_masking: When True, sample row values in PII-flagged columns are
                     replaced with [MASKED] before being returned. Defaults to True.
    """
    engine = get_engine()
    schemas = get_schema(engine)

    output = []
    for table in schemas:
        column_names = [col.name for col in table.columns]
        samples = sample_rows(engine, table.table_name, limit=8, columns=table.columns)
        raw_rows = [s.row for s in samples]

        if pii_masking:
            masked_rows = mask_sample_rows(raw_rows, column_names)
            flagged = pii_columns_in_table(column_names)
        else:
            masked_rows = raw_rows
            flagged = []

        output.append({
            "table_name": table.table_name,
            "columns": [col.model_dump() for col in table.columns],
            "sample_rows": masked_rows,
            "pii_columns_masked": flagged,   # informational — logged to snapshot, not sent to LLM prompt
        })
    return output


def write_snapshot(
    data: list[dict],
    path: Path = OUTPUT_PATH,
    pii_masking: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pii_masking_enabled": pii_masking,
        "tables": data,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pii-masking", action="store_true", help="Disable PII masking")
    args = parser.parse_args()

    pii_masking = not args.no_pii_masking
    data = collect_schema_and_samples(pii_masking=pii_masking)
    write_snapshot(data, pii_masking=pii_masking)

    masked_summary = [
        f"  {t['table_name']}: {t['pii_columns_masked']}"
        for t in data if t["pii_columns_masked"]
    ]
    status = "ON" if pii_masking else "OFF"
    print(f"Wrote schema snapshot for {len(data)} tables (PII masking {status})")
    if masked_summary:
        print("Masked columns:")
        print("\n".join(masked_summary))
    else:
        print("No PII columns detected." if pii_masking else "")