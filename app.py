# app.py
"""
SchemaLens AI — Streamlit UI
Covers Module 6: connect, scan, documentation, and chat.
Module 7: PII masking toggle wired through to snapshot collection.
"""
import os
import json
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values

_secrets_paths = (
    Path(".streamlit/secrets.toml"),
    Path.home() / ".streamlit" / "secrets.toml",
)
if any(path.is_file() for path in _secrets_paths):
    for key, value in st.secrets.items():
        os.environ[key] = str(value)

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="SchemaLens AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ────────────────────────────────────────────────────────────────────
ANALYSIS_PATH = Path("data/schema_analysis.json")
DOCS_PATH     = Path("data/documentation.md")
ENV_PATH      = Path(".env")

# ── Session-state initialisation ─────────────────────────────────────────────
def _init_state():
    defaults = {
        "history":     [],           # [{role, content}] for data_concierge
        "scan_done":   ANALYSIS_PATH.exists(),
        "scan_error":  None,
        "use_context_pack": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Load .env defaults for the connection form ───────────────────────────────
_env = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}

def _env_default(key: str, fallback: str = "") -> str:
    return _env.get(key, fallback)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _apply_connection_to_env(
    db_type, host="", port="", dbname="", user="", password="", db_path=""
):
    """Inject form values into os.environ so get_engine() picks them up."""
    os.environ["DB_TYPE"] = db_type
    if db_type == "sqlite":
        os.environ["DB_PATH"] = db_path
    else:
        os.environ["DB_HOST"]     = host
        os.environ["DB_PORT"]     = port
        os.environ["DB_NAME"]     = dbname
        os.environ["DB_USER"]     = user
        os.environ["DB_PASSWORD"] = password


def _run_scan(
    db_type, host, port, dbname, user, password, db_path, pii_masking: bool = True
):
    """Run the full Agent 2 pipeline and write artefacts to disk."""
    _apply_connection_to_env(db_type, host, port, dbname, user, password, db_path)

    from connectors.postgres import reset_engine
    reset_engine()

    # Re-import here so the updated env vars are visible when the modules load.
    from connectors.postgres import get_engine          # noqa: F401 — forces engine init
    from schema_snapshot import collect_schema_and_samples, write_snapshot
    from agents.business_analyst import run_analysis, write_analysis
    from markdown_renderer import render_markdown

    # Step 1: collect schema + samples, applying PII masking if enabled
    data = collect_schema_and_samples(pii_masking=pii_masking)
    write_snapshot(data, pii_masking=pii_masking)

    # Step 2: run Agent 2 (Business Analyst) on the (possibly masked) snapshot
    analysis = run_analysis()
    write_analysis(analysis)
    DOCS_PATH.write_text(render_markdown(analysis), encoding="utf-8")


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 SchemaLens AI")
    st.caption("AI-powered database documentation & chat")

    st.divider()
    st.subheader("Database Connection")

    db_type = st.selectbox(
        "Database type",
        options=["sqlite", "postgresql"],
        format_func=lambda value: "SQLite demo (no setup)" if value == "sqlite" else "PostgreSQL",
        index=0 if _env_default("DB_TYPE", "sqlite").lower() == "sqlite" else 1,
    )
    db_path = ""
    db_host = db_port = db_name = db_user = db_pass = ""
    if db_type == "sqlite":
        from connectors.sqlite_demo import DATABASE_PATH, create_demo_database

        db_path = st.text_input(
            "SQLite database file",
            value=_env_default("DB_PATH", str(DATABASE_PATH)),
        )
        if not Path(db_path).is_file() and db_path == str(DATABASE_PATH):
            with st.spinner("Preparing the included local demo database…"):
                create_demo_database(database_path=Path(db_path))
        st.caption("Uses the included sample rows; no PostgreSQL server or account needed.")
    else:
        db_host = st.text_input("Host", value=_env_default("DB_HOST", "localhost"))
        db_port = st.text_input("Port", value=_env_default("DB_PORT", "5432"))
        db_name = st.text_input("Database", value=_env_default("DB_NAME", "schemalens"))
        db_user = st.text_input("User", value=_env_default("DB_USER", "schemalens_reader"))
        db_pass = st.text_input(
            "Password", value=_env_default("DB_PASSWORD", ""), type="password"
        )

    st.divider()

    pii_masking = st.toggle(
        "PII Masking",
        value=True,
        help="Mask email addresses, names, phone numbers, and other sensitive sample "
             "values before sending them to the AI. Matching is based on column names.",
    )
    if pii_masking:
        st.caption("🛡️ PII masking **on** — sensitive sample values will be hidden from the AI.")
    else:
        st.caption("⚠️ PII masking **off** — all sample values sent to the AI as-is.")

    st.divider()

    scan_btn = st.button("⚡ Scan Database", type="primary", use_container_width=True)

    if scan_btn:
        st.session_state.scan_error = None
        with st.spinner("Analysing schema — this takes 30–60 s…"):
            try:
                _run_scan(
                    db_type, db_host, db_port, db_name, db_user, db_pass, db_path,
                    pii_masking=pii_masking,
                )
                st.session_state.scan_done  = True
                st.session_state.history    = []   # fresh chat on re-scan
            except Exception as exc:
                st.session_state.scan_error = str(exc)

        if st.session_state.scan_error:
            st.error(f"Scan failed: {st.session_state.scan_error}")
        else:
            st.success("Scan complete!")


    st.divider()

    drift_btn = st.button("🔄 Check for Schema Drift", use_container_width=True)

    if drift_btn:
        if not ANALYSIS_PATH.exists():
            st.warning("No baseline scan found. Run a scan first.")
        else:
            with st.spinner("Comparing schema against last scan…"):
                try:
                    _apply_connection_to_env(
                        db_type, db_host, db_port, db_name, db_user, db_pass, db_path
                    )
                    from drift_detector import detect_drift, format_drift_report
                    report = detect_drift()
                    if report.has_drift:
                        st.warning("⚠️ Schema drift detected")
                        drift_lines = format_drift_report(report).splitlines()
                        detail = "\n".join(drift_lines[3:])
                        st.caption(detail)
                        st.caption("Re-scan to update documentation.")
                    else:
                        st.success("✅ No drift — schema matches last scan.")
                except Exception as exc:
                    st.error(f"Drift check failed: {exc}")


    # Show last-scan timestamp + masking state if docs exist
    if ANALYSIS_PATH.exists():
        try:
            meta = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
            ts   = meta.get("generated_at", "")[:19].replace("T", " ")
            st.caption(f"Last scan: {ts} UTC")
        except Exception:
            pass

    context_pack_path = Path("data/context_pack.json")
    if context_pack_path.exists():
        st.download_button(
            label="⬇️ Download Context Pack",
            data=context_pack_path.read_bytes(),
            file_name="context_pack.json",
            mime="application/json",
            use_container_width=True,
        )

    # Show which columns were masked in the last snapshot
    snapshot_path = Path("data/schema_snapshot.json")
    if snapshot_path.exists():
        try:
            snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if snap.get("pii_masking_enabled"):
                masked = {
                    t["table_name"]: t.get("pii_columns_masked", [])
                    for t in snap.get("tables", [])
                    if t.get("pii_columns_masked")
                }
                if masked:
                    with st.expander("🛡️ Masked columns", expanded=False):
                        for table, cols in masked.items():
                            st.caption(f"**{table}:** {', '.join(cols)}")
        except Exception:
            pass


# ── Main area ────────────────────────────────────────────────────────────────
if not st.session_state.scan_done:
    st.markdown("## Welcome to SchemaLens AI")
    st.info(
        "Fill in your database connection on the left and click **⚡ Scan Database** "
        "to generate documentation and unlock the chat assistant."
    )
    st.markdown(
        """
        **What happens during a scan:**
        1. SchemaLens AI reads your schema — table names, column types, foreign keys
        2. It samples a handful of rows per table (never a full scan)
        3. PII masking replaces sensitive sample values before anything reaches the AI
        4. An AI analyst turns that into plain-English documentation
        5. You get searchable docs + a chat assistant that knows your data
        """
    )
    st.stop()

# ── Tabs (only shown after first scan) ───────────────────────────────────────
tab_docs, tab_chat = st.tabs(["📄 Documentation", "💬 Ask Questions"])

# ── Documentation tab ─────────────────────────────────────────────────────────
with tab_docs:
    if DOCS_PATH.exists():
        st.markdown(DOCS_PATH.read_text(encoding="utf-8"), unsafe_allow_html=False)
    else:
        st.warning("Documentation file not found. Try running a scan.")

# ── Chat tab ──────────────────────────────────────────────────────────────────
with tab_chat:
    st.markdown("Ask anything about your database — schema, column meanings, or real data queries.")

    use_context_pack = st.toggle("🧠 Use Context Pack", value=True, 
                                  help="When off, the assistant only sees raw column names — no meanings or ambiguity flags.")

    # Chat input
    prompt = st.chat_input("E.g. 'Which table tracks revenue?' or 'How many active customers are there?'")

    # Replay conversation history
    for turn in st.session_state.history:
        with st.chat_message(turn["role"]):
            if turn["role"] == "assistant":
                try:
                    data = json.loads(turn["content"])
                    for resp in data.get("responses", []):
                        st.markdown(resp.get("answer", ""))
                    if resp.get("sql"):
                        with st.expander("SQL"):
                            st.code(resp["sql"], language="sql")
                except Exception:
                    st.markdown(turn["content"])
            else:
                st.markdown(turn["content"])

    if prompt:
        # Show the user's message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call the Data Concierge
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    from agents.data_concierge import ask_question
                    responses = ask_question(
                        question=prompt,
                        history=st.session_state.history,
                        docs_path=ANALYSIS_PATH,
                        use_context_pack=use_context_pack,   # ← temp, for testing
                    )
                except Exception as exc:
                    responses = [{
                        "mode":    "C",
                        "answer":  f"Something went wrong: {exc}",
                        "sql":     None,
                        "results": None,
                    }]

            # Render each response entry
            answer_parts = []
            for i, resp in enumerate(responses):
                answer = resp.get("answer", "")
                mode   = resp.get("mode", "A")
                sql    = resp.get("sql")
                results = resp.get("results")

                # Mode badge (subtle)
                _badge = {"A": "📖 Explanation", "B": "📊 Data Query", "C": "❓ Out of Scope"}
                if len(responses) > 1:
                    st.caption(_badge.get(mode, ""))

                st.markdown(answer)
                answer_parts.append(answer)

                if sql:
                    with st.expander("View SQL", expanded=False):
                        st.code(sql, language="sql")

                if results:
                    with st.expander("Query Results", expanded=True):
                        lines = results.strip().splitlines()
                        if len(lines) >= 3 and " | " in lines[0]:
                            try:
                                import pandas as pd
                                cols = [c.strip() for c in lines[0].split(" | ")]
                                rows = [
                                    [c.strip() for c in line.split(" | ")]
                                    for line in lines[2:]
                                    if line.strip() and "showing" not in line
                                ]
                                df = pd.DataFrame(rows, columns=cols)
                                st.dataframe(df, use_container_width=True)
                                if any("showing" in l for l in lines):
                                    note = next(l for l in lines if "showing" in l)
                                    st.caption(note.strip())
                            except Exception:
                                st.text(results)
                        else:
                            st.text(results)

                if i < len(responses) - 1:
                    st.divider()

        # Append to history
        st.session_state.history.append({"role": "user",      "content": prompt})
        st.session_state.history.append({"role": "assistant", "content": json.dumps({"responses": responses})})