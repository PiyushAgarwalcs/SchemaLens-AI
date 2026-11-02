# agents/data_concierge.py

import json
import os
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlalchemy import text
from dotenv import load_dotenv

from connectors.postgres import get_engine

from langchain_core.exceptions import LangChainException

import re

from collections import defaultdict

load_dotenv()

ANALYSIS_PATH = Path("data/schema_analysis.json")
SNAPSHOT_PATH = Path("data/schema_snapshot.json")

# Token-saving constants

# 10 = 5 Q&A pairs. Beyond this, older turns are dropped entirely.
HISTORY_WINDOW = 10
# Older messages (still within the window) are compressed. 4 = last 2 Q&A pairs full — so follow-up SQL edits always have the original SQL in context.
RECENT_FULL_COUNT = 4


# LLM
def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL"),
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("FIREWORKS_API_KEY"),
        temperature=0,
    )




def _format_table_full(t: dict) -> str:
    cols = ", ".join(f"{c['column']}({c['meaning']})" for c in t["column_meanings"])
    rel = t.get("relationships", "").strip()
    flags = "; ".join(f"⚠{f['column']}: {f['note']}" for f in t.get("ambiguity_flags", []))
    entry = f"[{t['table_name']}] {t['purpose']}\nCols: {cols}"
    if rel:
        entry += f"\nFK: {rel}"
    if flags:
        entry += f"\n{flags}"
    return entry


def _format_table_summary(t: dict) -> str:
    return f"[{t['table_name']}] {t['purpose']}"


def _load_docs(path: Path = ANALYSIS_PATH, question: str = "") -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    tables = data["tables"]
    tier = data.get("tier", 1)

    if tier == 1 or not question:
        return "\n---\n".join(_format_table_full(t) for t in tables)

    # T2: inject full context only for relevant tables + FK neighbors
    question_lower = question.lower()

    # Build bidirectional FK neighbor map from relationships strings
    fk_neighbors: dict[str, set[str]] = defaultdict(set)
    for t in tables:
        for ref_table in re.findall(r'\b(\w+)\.\w+\b', t.get("relationships", "")):
            fk_neighbors[t["table_name"]].add(ref_table)
            fk_neighbors[ref_table].add(t["table_name"])

    # Tables whose name or column names appear in the question
    matched: set[str] = set()
    for t in tables:
        if t["table_name"].lower() in question_lower:
            matched.add(t["table_name"])
        for c in t["column_meanings"]:
            if c["column"].lower() in question_lower:
                matched.add(t["table_name"])

    # Expand to FK neighbors
    full_inject: set[str] = set(matched)
    for t_name in matched:
        full_inject |= fk_neighbors.get(t_name, set())

    # Fallback: no hints found → full injection
    if not full_inject:
        return "\n---\n".join(_format_table_full(t) for t in tables)

    return "\n---\n".join(
        _format_table_full(t) if t["table_name"] in full_inject else _format_table_summary(t)
        for t in tables
    )


# for comparison
def _load_raw_schema(path: Path = SNAPSHOT_PATH) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    for t in data["tables"]:
        cols = ", ".join(c['name'] for c in t["columns"])
        lines.append(f"[{t['table_name']}] Cols: {cols}")
    return "\n".join(lines)


# System prompt
SYSTEM_PROMPT = """You are SchemaLens AI, a database assistant. Answer questions using the documentation below, writing SQL only when real data is needed.

<database_documentation>
{docs}
</database_documentation>

CLASSIFY each question:
- MODE A: fully answered by the docs (schema structure, column meanings, relationships) — no SQL
- MODE B: requires real data (counts, totals, trends, specific records) — write SELECT
- MODE C: involves tables/columns not in the docs, or is unrelated to this database

Multi-part messages: each distinct question gets its own entry in "responses", in order.

SQL RULES (Mode B only):
- Single SELECT, valid {sql_dialect}, no SELECT *
- Reference only tables and columns named in the docs
- LIMIT 100 by default; omit only for bare aggregates (single COUNT/SUM/etc with no GROUP BY)
- Use table aliases and qualified column refs when joining tables that share column names
- Forbidden: INSERT UPDATE DELETE DROP ALTER CREATE TRUNCATE GRANT REVOKE EXEC COPY and any multi-statement (no semicolons separating statements)

RESPONSE RULES:
- Mode A: 1–3 plain sentences answering from the docs
- Mode B: explain what the result means for the user's question; describe what each row/column represents
- Mode C: name specifically what is missing or out of scope; don't say "I don't have real-time data"
- Ambiguous question: name both interpretations, write SQL for the most likely, state your assumption
- Never invent table names, column names, or business logic not in the docs

OUTPUT — return ONLY valid JSON, no markdown fences, no text before or after:
{{"responses": [{{"mode": "A"|"B"|"C", "answer": "<non-empty string>", "sql": "<SELECT or null>"}}]}}
Escape inner quotes as \\" and newlines as \\n. "answer" is never null. "responses" is never empty.
"""


# History compression
def _compress_turn(turn: dict) -> str:
    """Compress a completed Q&A turn into a compact history entry.

    For assistant turns: tries to parse the raw JSON response (if it was stored
    that way), otherwise falls back to truncating the plain-text content.
    For user turns: returned as-is (already short).

    This keeps older context in the window at a fraction of the token cost.
    """
    if turn["role"] == "assistant":
        try:
            data = json.loads(turn["content"])
            lines = []
            for r in data.get("responses", []):
                mode = r.get("mode", "?")
                answer_snippet = r.get("answer", "")[:80]
                sql = r.get("sql")
                if mode == "B" and sql:
                    lines.append(
                        f"[Mode B] Q answered with SQL: {sql[:120]}... | Summary: {answer_snippet}"
                    )
                elif mode == "A":
                    lines.append(f"[Mode A] Explained: {answer_snippet}")
                else:
                    lines.append(f"[Mode C] Out of scope: {answer_snippet}")
            return "\n".join(lines)
        except Exception:
            # History stores plain text (not raw JSON) — just truncate
            return turn["content"][:150]
    return turn["content"]   # user messages stay as-is


def _build_messages(system_content, history, question):
    messages = [{"role": "system", "content": system_content}]
    windowed = history[-HISTORY_WINDOW:]
    for i, turn in enumerate(windowed):
        distance_from_end = len(windowed) - i
        content = _compress_turn(turn) if distance_from_end > RECENT_FULL_COUNT else turn["content"]
        messages.append({"role": turn["role"], "content": content})
    messages.append({"role": "user", "content": question})
    return messages


# SQL safety + execution
def _is_safe_sql(sql: str) -> tuple[bool, str]:
    """
    Returns (is_safe, rejection_reason).
    Uses word-boundary regex so table/column names that happen to contain
    forbidden keywords as substrings (e.g. ORDEREXECUTIONS ⊃ EXEC) are not
    falsely rejected.
    """
    cleaned = sql.strip().lstrip("(").upper()

    if cleaned.startswith("WITH"):
        pass  # CTEs are fine as long as the body resolves to a SELECT
    elif not cleaned.startswith("SELECT"):
        return False, "statement does not begin with SELECT"

    forbidden = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXEC", "COPY",
    ]
    for kw in forbidden:
        if re.search(rf"\b{kw}\b", cleaned):
            return False, f"contains forbidden keyword '{kw}'"

    return True, ""

def _enforce_limit(sql: str, cap: int = 100) -> str:
    sql = sql.strip().rstrip(";").strip()
    if re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
        return sql
    is_bare_aggregate = (
        re.search(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', sql, re.IGNORECASE)
        and not re.search(r'\bGROUP\s+BY\b', sql, re.IGNORECASE)
    )
    if is_bare_aggregate:
        return sql
    
    # CTE — WITH clause must stay at statement level, can't be wrapped in FROM
    if re.search(r'^\s*WITH\b', sql, re.IGNORECASE):
        return f"{sql} LIMIT {cap}"
    return f"SELECT * FROM ({sql}) AS _q LIMIT {cap}"


def _execute_sql(sql: str, row_cap: int = 50) -> str:
    """Execute query via read-only engine; return results as a plain text table."""
    sql = _enforce_limit(sql)
    try:
        engine = get_engine()
        with engine.connect() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("SET LOCAL statement_timeout = '15s'"))
            result = conn.execute(text(sql))
            rows = result.mappings().all()

        if not rows:
            return "Query returned no rows."

        cols = list(rows[0].keys())
        header = " | ".join(cols)
        divider = "-" * len(header)
        body = [" | ".join(str(row[c]) for c in cols) for row in rows[:row_cap]]

        suffix = f"\n(showing {row_cap} of {len(rows)} rows)" if len(rows) > row_cap else ""
        return "\n".join([header, divider] + body) + suffix

    except Exception as e:
        return f"SQL execution error: {e}"


# Public API
def ask_question(
    question: str,
    history: list[dict],   # [{"role": "user"|"assistant", "content": "..."}]
    docs_path: Path = ANALYSIS_PATH,
    use_context_pack: bool = True,  #for comparison
) -> list[dict]:
    llm = _get_llm()

    try:
        docs = _load_docs(docs_path, question=question) if use_context_pack else _load_raw_schema() #test case
        safe_docs = docs.replace("{", "{{").replace("}", "}}")
        db_type = os.getenv("DB_TYPE", "postgresql").lower()
        sql_dialect = "SQLite" if db_type == "sqlite" else "PostgreSQL"
        system_content = SYSTEM_PROMPT.format(docs=safe_docs, sql_dialect=sql_dialect)
        messages = _build_messages(system_content, history, question)
        raw = llm.invoke(messages)
    except LangChainException as e:
        return [{"mode": "C", "answer": f"LLM call failed: {e}", "sql": None, "results": None}]
    except Exception as e:
        return [{"mode": "C", "answer": f"Unexpected error: {e}", "sql": None, "results": None}]

    # gpt-oss-120b quirk: reasoning tokens live in a separate field; use .content only.
    content = raw.content if isinstance(raw.content, str) else raw.content[0]["text"]
    content = content.strip().strip("```json").strip("```").strip()


    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return [{"mode": "A", "answer": content, "sql": None, "results": None}]

    responses = parsed.get("responses", [])
    if not responses:
        return [{"mode": "C", "answer": "No response generated.", "sql": None, "results": None}]

    output = []
    for entry in responses:
        sql = entry.get("sql")
        if not sql or (isinstance(sql, str) and sql.strip().lower() == "null"):
            sql = None

        results = None
        if sql:
            safe, reason = _is_safe_sql(sql)
            if safe:
                results = _execute_sql(sql)
            else:
                results = f"⚠️ SQL rejected: {reason}."

        output.append({
            "mode":    entry.get("mode", "A"),
            "answer":  entry.get("answer", ""),
            "sql":     sql,
            "results": results,
        })

    return output