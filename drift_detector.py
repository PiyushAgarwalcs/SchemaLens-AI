# drift_detector.py
#
# How this works:
#   1. Load the last saved snapshot from disk (baseline).
#   2. Collect a fresh snapshot live from the DB.
#   3. Build a dict index for each: table_name -> {col_name -> col_info}.
#   4. Set-diff the table names to find additions/removals.
#   5. For shared tables, compare column-by-column: additions, removals,
#      type changes, nullability changes.
#   No LLM involved — this is pure structural comparison.

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_PATH = Path("data/schema_snapshot.json")


# Data model
@dataclass
class ColumnChange:
    table: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    type_changes: list[dict] = field(default_factory=list)       # [{column, old, new}]
    nullability_changes: list[dict] = field(default_factory=list) # [{column, old, new}]


@dataclass
class DriftReport:
    scanned_at: str
    baseline_at: str          # generated_at from the saved snapshot
    tables_added: list[str]
    tables_removed: list[str]
    column_changes: list[ColumnChange]
    has_drift: bool


# Internal helpers
def _load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(snapshot: dict) -> dict[str, dict[str, dict]]:
    """table_name -> {col_name -> col_dict}"""
    return {
        t["table_name"]: {c["name"]: c for c in t["columns"]}
        for t in snapshot["tables"]
    }


# Public API
def detect_drift(
    baseline_path: Path = SNAPSHOT_PATH,
    new_snapshot: dict | None = None,
) -> DriftReport:
    """
    Compare the saved snapshot (baseline) against the current DB state.

    Args:
        baseline_path: Path to the saved schema_snapshot.json.
        new_snapshot:  Pre-collected snapshot dict. If None, re-collects live from DB.

    Returns:
        DriftReport with all differences between baseline and current schema.
    """
    from schema_snapshot import collect_schema_and_samples

    baseline = _load_snapshot(baseline_path)

    if new_snapshot is None:
        new_tables = collect_schema_and_samples()
        new = {"tables": new_tables}
    else:
        new = new_snapshot

    old_idx = _index(baseline)
    new_idx = _index(new)

    old_table_set = set(old_idx)
    new_table_set = set(new_idx)

    tables_added = sorted(new_table_set - old_table_set)
    tables_removed = sorted(old_table_set - new_table_set)

    column_changes: list[ColumnChange] = []

    for table in sorted(old_table_set & new_table_set):
        old_cols = old_idx[table]
        new_cols = new_idx[table]

        added = sorted(set(new_cols) - set(old_cols))
        removed = sorted(set(old_cols) - set(new_cols))
        type_changes = []
        null_changes = []

        for col in sorted(set(old_cols) & set(new_cols)):
            if old_cols[col]["type"] != new_cols[col]["type"]:
                type_changes.append({
                    "column": col,
                    "old": old_cols[col]["type"],
                    "new": new_cols[col]["type"],
                })
            if old_cols[col]["nullable"] != new_cols[col]["nullable"]:
                null_changes.append({
                    "column": col,
                    "old": old_cols[col]["nullable"],
                    "new": new_cols[col]["nullable"],
                })

        if any([added, removed, type_changes, null_changes]):
            column_changes.append(ColumnChange(
                table=table,
                added=added,
                removed=removed,
                type_changes=type_changes,
                nullability_changes=null_changes,
            ))

    has_drift = bool(tables_added or tables_removed or column_changes)

    return DriftReport(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        baseline_at=baseline.get("generated_at", "unknown"),
        tables_added=tables_added,
        tables_removed=tables_removed,
        column_changes=column_changes,
        has_drift=has_drift,
    )


def format_drift_report(report: DriftReport) -> str:
    """Human-readable summary of the drift report."""
    if not report.has_drift:
        return (
            f"✅ No schema drift detected.\n"
            f"   Baseline: {report.baseline_at}\n"
            f"   Scanned:  {report.scanned_at}"
        )

    lines = [
        f"⚠️  Schema drift detected",
        f"   Baseline: {report.baseline_at}",
        f"   Scanned:  {report.scanned_at}",
        "",
    ]

    if report.tables_added:
        lines.append(f"Tables added:   {', '.join(report.tables_added)}")
    if report.tables_removed:
        lines.append(f"Tables removed: {', '.join(report.tables_removed)}")

    for cc in report.column_changes:
        lines.append(f"\n{cc.table}:")
        for col in cc.added:
            lines.append(f"  + {col}  (new column)")
        for col in cc.removed:
            lines.append(f"  - {col}  (dropped)")
        for tc in cc.type_changes:
            lines.append(f"  ~ {tc['column']}  type: {tc['old']} → {tc['new']}")
        for nc in cc.nullability_changes:
            lines.append(f"  ~ {nc['column']}  nullable: {nc['old']} → {nc['new']}")

    return "\n".join(lines)


if __name__ == "__main__":
    report = detect_drift()
    print(format_drift_report(report))