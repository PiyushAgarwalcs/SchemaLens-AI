import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from mcp.server.fastmcp import FastMCP

CONTEXT_PACK_PATH = REPO_ROOT / "data" / "context_pack.json"
SNAPSHOT_PATH     = REPO_ROOT / "data" / "schema_snapshot.json"

mcp = FastMCP("SchemaLens AI")


# Tool 1 get_context_pack
@mcp.tool()
def get_context_pack() -> str:
    """
    Returns the full SchemaLens AI Context Pack as a JSON string.

    The Context Pack is the machine-readable semantic layer produced by
    SchemaLens AI's Business Analyst agent. It contains:
    - Business-language purpose for every table
    - Per-column meanings (what the column actually represents, not just its
      name and SQL type)
    - FK-backed relationships between tables
    - Ambiguity flags for columns that share a name across tables but mean
      completely different things (e.g. 'channel' in orders means sales
      channel; 'channel' in marketing_campaigns means marketing medium —
      no relationship between them)
    - Business value description per table

    Call this first before writing SQL or answering questions about the schema.
    Do not infer column meaning from names alone — the Context Pack has the
    correct interpretation already computed.
    """
    if not CONTEXT_PACK_PATH.exists():
        return json.dumps({
            "error": (
                "Context Pack not found. Run a scan first: "
                "python schema_snapshot.py && python agents/business_analyst.py"
            )
        })
    return CONTEXT_PACK_PATH.read_text(encoding="utf-8")


#Tool 2 query_documentation
@mcp.tool()
def query_documentation(table_name: str) -> str:
    """
    Returns the Context Pack entry for a single named table.

    More token-efficient than get_context_pack() when you only need one
    table's documentation. Returns the full entry: purpose, column meanings,
    relationships, ambiguity flags, and business value.

    Args:
        table_name: Exact table name as it appears in the database
                    (case-sensitive, e.g. "orders", "marketing_campaigns").
                    Call get_context_pack() first to see all available names.
    """
    if not CONTEXT_PACK_PATH.exists():
        return json.dumps({"error": "Context Pack not found."})

    data = json.loads(CONTEXT_PACK_PATH.read_text(encoding="utf-8"))

    for table in data.get("tables", []):
        if table["table_name"] == table_name:
            return json.dumps(table, indent=2)

    available = [t["table_name"] for t in data.get("tables", [])]
    return json.dumps({
        "error": f"Table '{table_name}' not found in Context Pack.",
        "available_tables": available,
    })


#Tool 3 check_drift
@mcp.tool()
def check_drift() -> str:
    """
    Checks whether the live database schema matches the saved Context Pack.

    Compares the current DB structure against the schema snapshot that was
    captured when the Context Pack was last generated. Reports:
    - Tables added or removed since last scan
    - Column-level changes: new columns, dropped columns, type changes,
      nullability changes

    No LLM involved — this is a pure structural diff (set operations on table
    and column names). Returns "No schema drift detected" if nothing changed.

    Requires DB credentials to be present in the .env file in the repo root.
    Call this to verify the Context Pack is still current before trusting it.
    """
    if not SNAPSHOT_PATH.exists():
        return "No baseline snapshot found. Run a scan first (python schema_snapshot.py)."

    try:
        from drift_detector import detect_drift, format_drift_report

        report = detect_drift(baseline_path=SNAPSHOT_PATH)
        return format_drift_report(report)
    except Exception as e:
        return f"Drift check failed: {e}"
    
#Tool 4 get_raw_schema (use for comparison)
@mcp.tool()
def get_raw_schema() -> str:
    """Returns raw column names and types only — no business context."""
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    lines = []
    for t in data["tables"]:
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        lines.append(f"[{t['table_name']}] {cols}")
    return "\n".join(lines)
    

if __name__ == "__main__":
    mcp.run(transport="stdio")