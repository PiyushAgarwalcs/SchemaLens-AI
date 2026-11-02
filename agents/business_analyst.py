import json
from datetime import datetime, timezone
from pathlib import Path

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
from dotenv import load_dotenv

from models.analysis_models import SchemaAnalysisDraft, SchemaAnalysis

from collections import defaultdict

load_dotenv()

SNAPSHOT_PATH = Path("data/schema_snapshot.json")
OUTPUT_PATH = Path("data/schema_analysis.json")
DOCS_PATH = Path("data/documentation.md")

PROMPT_TEMPLATE = """You are a business analyst documenting an entire database schema for a non-technical audience.
 
You are given ALL tables in the schema at once, specifically so you can reason across tables —
not just within one.
 
<tables>
{tables_block}
</tables>
 
<cross_table_column_collisions>
Precomputed from the schema: every column name that appears in 2+ tables with no FK between
them, with their sampled values in each table and how many overlap. This is your checklist —
every line here must produce a matching ambiguity_flags entry in every table named on that
line. Don't report a collision that isn't listed here, and don't skip one that is. If this
says "(no cross-table column-name collisions found)", skip cross-table ambiguity entirely —
don't invent one.
 
{cross_table_index_block}
</cross_table_column_collisions>
 
<process>
Work in two passes, in order.
1. Table by table: for each table, read its columns and sample rows on their own terms and
   draft purpose, column_meanings, business_value, relationships, and any single-table
   ambiguity. Do this before comparing tables to each other, so per-table detail doesn't get
   diluted by cross-table comparison.
2. Cross-table audit: go through <cross_table_column_collisions> line by line and add the
   corresponding ambiguity_flags entries to the tables involved.
3. Component-total audit: for each table with 3+ numeric columns, check the sample rows.
   If any column's values equal the sum of two or more other columns across ALL sample rows
   (within floating-point rounding), state this explicitly in the relevant column_meanings.
   Example: if wallet_total = available + frozen in every row, then:
     wallet_total meaning → "Total wallet value; equals available + frozen."
     available meaning    → "Available sub-component of walletsum."
     frozen meaning       → "Frozen sub-component of walletsum."
   This prevents downstream tools from double-counting by summing sub-components and totals
   together.   
</process>
 
<rules>
- Base every claim ONLY on the columns and samples given. Never invent business context. 10
  sample rows is a small set — phrase overlap or meaning claims as observations about the
  sample ("in the sampled rows...") rather than as universal claims about the column.
- Write every output field in plain, non-technical language. Terms like FK, NULL, or enum are
  fine in your own reasoning but must not appear in purpose, column_meanings, business_value,
  or ambiguity_flags — describe what's actually going on instead (e.g. "no linked table
  confirms this" rather than "FK=None").
 
- purpose: 2 sentences. Sentence 1 names the real-world entity or event this table records —
  or, if it's a reference/lookup table rather than a transactional record, says so plainly
  (e.g. "This table is a lookup of valid order statuses."). Sentence 2 names the specific
  states, attributes, or lifecycle this table tracks — be concrete (e.g. "tracks whether a
  campaign is active, paused, or completed"), not vague ("tracks details and outcomes").
 
- column_meanings: short, table-specific. No generic definitions. State units or currency
  when they're evident from the data; if they're not evident, that's a single-table ambiguity
  flag, not a column_meanings note.
 
- business_value: 1-2 sentences naming the actual business questions this table's specific
  columns can answer (e.g. "which channels drive the most revenue", not "supports analysis").
  If a table is a simple lookup/reference table with little standalone business value, say
  that in one sentence rather than manufacturing value the data doesn't support — that would
  break the "never invent" rule above.
 
- ambiguity_flags: check BOTH categories below for every table, not just one — a table can
  have flags from both at once, so don't stop after finding one. For every flag, state the
  competing interpretations; do not pick one and present it as settled.
  (a) Single-table: undefined units/currency, unclear meaning of NULL, undocumented value
      sets, anything in the sample data that looks inconsistent or unexplained.
  (b) Cross-table: every line in <cross_table_column_collisions> involving this table.
      - No overlap in sampled values: the columns likely mean different things despite the
        shared name. Name the other table and its values (e.g. "channel here means
        web/app/in-store; the same-named column in marketing_campaigns refers to
        email/social/paid_search instead — no confirmed relationship between them").
      - Some or full overlap in sampled values: don't describe them as unrelated. Say the
        columns might be the same underlying concept without a declared link, and flag it as
        a possible undeclared relationship rather than a naming coincidence.
    Write exactly ONE ambiguity_flags entry per colliding column name
    per table,summarizing its relationship to all other tables sharing
    that name together — not one entry per other table.
    
- relationships: only describe links backed by an actual FK in the column list above. Never
  infer one from a shared column name alone.
 
- Return exactly one TableAnalysis per table listed in <tables>, same order, same table_name.
  Do not merge, omit, or invent tables.

- component_totals: Never leave implicit a numeric column that is the sum of others in the
  same table. If sample data reveals col_a + col_b ≈ col_total across all rows, the
  column_meanings for col_total must say "total of col_a and col_b", and the meanings for
  col_a and col_b must each say "sub-component of col_total". This is mandatory — not
  optional — when the relationship is detectable from the sample.  
</rules>
 
<example>
Table "orders" (order_id, customer_id [FK -> customers.customer_id], channel, status, amount)
and table "marketing_campaigns" (campaign_id, channel, spend), no FK between their "channel"
columns. orders.channel sampled as web/app/in-store; marketing_campaigns.channel sampled as
email/social/paid_search — no overlap.
 
purpose: "This table records individual customer purchase transactions. It tracks each
order's sales channel, current status, and amount at time of purchase."
 
column_meanings: channel describes where the purchase was placed (web, app, or in-store);
status describes where the order currently sits in fulfillment (e.g. pending, shipped,
delivered, based on the sampled values).
 
business_value: "Answers which sales channel drives the most order volume and revenue, and
how orders are currently distributed across fulfillment stages."
 
ambiguity_flags: "channel here means web/app/in-store; the same-named column in
marketing_campaigns refers to email/social/paid_search instead, with no FK linking them — they
describe different things despite sharing a name."
 
relationships: "customer_id links to customers.customer_id."
</example>
"""


UNIVERSAL_COLUMNS = frozenset({
    "id", "created_at", "updated_at", "deleted_at", "is_active", "is_deleted",
    "created_by", "updated_by", "metadata", "description", "notes", "uuid", "version",
})

def build_cross_table_index(tables: list[dict]) -> str:
    total_tables = len(tables)
    name_to_tables = defaultdict(list)
    for table in tables:
        for col in table["columns"]:
            if col["foreign_key"] is None:
                name_to_tables[col["name"]].append(table["table_name"])

    by_name = {t["table_name"]: t for t in tables}
    lines = []
    for col_name, table_names in name_to_tables.items():
        if len(table_names) < 2:
            continue
        if col_name in UNIVERSAL_COLUMNS:
            continue
        if total_tables > 10 and len(table_names) > total_tables * 0.4:
            continue
        table_names = table_names[:8]  # cap at 8 entries

        sampled_values = {
            t: sorted({
                row[col_name]
                for row in by_name[t]["sample_rows"]
                if col_name in row and row[col_name] is not None
            })
            for t in table_names
        }
        any_overlap = set()
        for i in range(len(table_names)):
            for j in range(i + 1, len(table_names)):
                any_overlap |= set(sampled_values[table_names[i]]) & set(sampled_values[table_names[j]])

        block = [f'- "{col_name}" appears in: ' +
                 "; ".join(f"{t} {sampled_values[t]}" for t in table_names)]
        if any_overlap:
            block.append(
                f"  shared value(s) somewhere across these: {sorted(any_overlap)} — "
                f"if this is a small fraction of an otherwise disjoint set, treat as a "
                f"coincidental generic word, not a relationship signal. Only call it a "
                f"possible undeclared relationship if the overlap is substantial relative "
                f"to the value sets, not a single common word like 'active'."
            )
        else:
            block.append("  no shared values across any of these tables.")
        lines.append("\n".join(block))

    return "\n".join(lines) if lines else "(no cross-table column-name collisions found)"

def _get_llm(table_count: int = 8) -> LLM:
    # ~600 tokens per table for full analysis output, 1500 base overhead
    dynamic_max = table_count * 600 + 1500
    # Floor: 6000 so small schemas still get breathing room
    # Ceiling: 8192 — safe limit for gpt-oss-120b on Fireworks
    max_tokens = min(max(6000, dynamic_max), 8192)
    return LLM(
        model="fireworks_ai/accounts/fireworks/models/gpt-oss-120b",
        base_url="https://api.fireworks.ai/inference/v1",
        temperature=0.2,   # factual task, not creative — keep it deterministic
        max_tokens=max_tokens,   # cap runaway output cost; raise if you see truncation
    )

def _format_table_block(table: dict) -> str:
    columns_block = "\n".join(
        f"  - {c['name']} ({c['type']}, nullable={c['nullable']}, FK={c['foreign_key']})"
        for c in table["columns"]
    )
    samples_block = json.dumps(table["sample_rows"][:5], indent=2, default=str)
    return f"### Table: {table['table_name']}\nColumns:\n{columns_block}\nSample rows:\n{samples_block}\n"

def _build_task(agent: Agent, tables: list[dict]) -> Task:
    tables_block = "\n\n".join(_format_table_block(t) for t in tables)
    cross_table_index_block = build_cross_table_index(tables)
    return Task(
        description = (
            PROMPT_TEMPLATE
            .replace("{tables_block}", tables_block)
            .replace("{cross_table_index_block}", cross_table_index_block)
),
        expected_output=f"A SchemaAnalysisDraft with exactly {len(tables)} TableAnalysis entries, one per table above, in order.",
        agent=agent,
        output_pydantic=SchemaAnalysisDraft,
    )

def run_analysis(snapshot_path: Path = SNAPSHOT_PATH) -> SchemaAnalysis:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    analyst = Agent(
        role="Business Analyst",
        goal="Explain database tables in plain business language, flagging ambiguity instead of guessing.",
        backstory="A senior data analyst who values precision over confident-sounding guesses.",
        llm=_get_llm(len(snapshot["tables"])),
        verbose=True,
    )

    task = _build_task(analyst, snapshot["tables"])
    Crew(agents=[analyst], tasks=[task], process=Process.sequential).kickoff()

    draft = task.output.pydantic
    if draft is None:
        raise ValueError(f"Structured output parse failed. Raw output:\n{task.output.raw}")
    if len(draft.tables) != len(snapshot["tables"]):
        raise ValueError(f"Expected {len(snapshot['tables'])} tables, got {len(draft.tables)} — likely truncation, raise max_tokens.")

    return SchemaAnalysis(generated_at=datetime.now(timezone.utc).isoformat(), tables=draft.tables)

def write_analysis(analysis: SchemaAnalysis, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    # Compute + attach complexity metadata before writing
    table_count = len(analysis.tables)
    avg_cols = sum(len(t.column_meanings) for t in analysis.tables) / max(table_count, 1)
    complexity_score = round(table_count * avg_cols, 1)
    tier = 2 if complexity_score >= 250 else 1
    analysis = analysis.model_copy(update={
        "complexity_score": complexity_score,
        "tier": tier,
    })

    path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    import shutil
    shutil.copy2(path, path.parent / "context_pack.json")


if __name__ == "__main__":
    from markdown_renderer import render_markdown
    analysis = run_analysis()
    write_analysis(analysis)
    DOCS_PATH.write_text(render_markdown(analysis), encoding="utf-8")
    print(f"Wrote analysis + docs for {len(analysis.tables)} tables. 1 LLM call this run.")