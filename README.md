# SchemaLens AI

**A semantic context layer for more reliable AI-powered SQL.**

SchemaLens AI documents database schemas in business language and packages that context for AI assistants. It helps address a common text-to-SQL problem: database structures can be difficult to interpret from table and column names alone, even when generated SQL is syntactically valid.

The project includes a SQLite demo database for local evaluation and can connect to PostgreSQL databases.

## What it produces

A **Context Pack** is a portable JSON description of a database schema. It contains:

- Table purpose and business value
- Plain-language meanings for columns
- Relationships backed by declared foreign keys
- Ambiguity notes for unclear meanings and shared column names
- Metadata used to identify schema drift

The Context Pack can be downloaded from the app or provided to an MCP-compatible AI client.

## Features

| Feature | Description |
|---|---|
| Schema snapshot | Collects tables, columns, data types, primary keys, foreign keys, and a small sample of rows |
| Business analysis | Uses an LLM to generate a structured, plain-language analysis across the schema |
| Ambiguity detection | Identifies same-named columns and provides their sampled values as analysis context |
| PII masking | Masks sample values in columns that match the built-in sensitive-name patterns |
| Documentation | Produces a JSON Context Pack and rendered Markdown documentation |
| Drift detection | Compares a saved snapshot with a later scan for structural changes |
| Streamlit app | Provides database settings, scanning, documentation, and a chat interface |
| MCP server | Exposes the Context Pack and schema information to compatible clients |

## How it works

1. **Collect:** Deterministic Python reads database structure and samples up to eight rows per table. The SQLite demo is opened read-only; PostgreSQL should be accessed with a read-only database account.
2. **Mask:** When enabled, matching sample values are replaced before they are passed to an LLM.
3. **Analyze:** A CrewAI business analyst produces structured table descriptions in a single schema-wide analysis.
4. **Publish:** The app writes `data/context_pack.json`, `data/schema_analysis.json`, and `data/documentation.md`.
5. **Use:** Browse the documentation in Streamlit, ask questions through the chat interface, or connect an MCP client.

## Requirements

- Python 3.10 or later
- No database installation or setup for the included SQLite demo
- Fireworks API key only for a new AI analysis or AI chat

The app defaults to the included SQLite demo database. It also has an optional PostgreSQL connector for scanning a PostgreSQL database you already have. The demo and existing documentation work without a Fireworks key; AI analyses and chat send requests to Fireworks and may use paid credits. Check your account's current terms and credits before using those features.

## Quickstart

Open a terminal in the project folder, then create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually <http://localhost:8501>. Select **SQLite demo** in the sidebar. On first use, the app creates `data/schemalens_demo.sqlite3` from the included schema snapshot and sample rows. This is demonstration data, not a copy of a production database.

The repository includes previously generated documentation, so you can browse it without configuring an API key. Scanning the included SQLite demo or using AI chat requires the Fireworks configuration below.

## Fireworks configuration

Create a `.env` file in the project root and add your Fireworks API key:

```dotenv
FIREWORKS_API_KEY=your_fireworks_api_key
LLM_BASE_URL=https://api.fireworks.ai/inference/v1
LLM_MODEL=accounts/fireworks/models/gpt-oss-120b
```

Keep `.env` private and do not commit it. The API key is sent to Fireworks when you use LLM-backed features. Sample rows are included in the analysis prompt; leave PII masking enabled unless you have reviewed what data will be sent.

## Optional: use your own PostgreSQL database

This is not needed for the SQLite demo. To scan your own PostgreSQL database, select **PostgreSQL** in the app and enter its connection settings in the sidebar, or set them in `.env`:

```dotenv
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_read_only_user
DB_PASSWORD=your_password
```

Use an account restricted to the required read access. The current connector reads the PostgreSQL `public` schema.

## MCP server

The FastMCP server uses standard input/output transport. To register it with an MCP client, configure the client to launch the Python interpreter in this project's virtual environment and pass the absolute path to `mcp_server.py`.

Example configuration for Claude Desktop on Windows (replace the paths with your project location):

```json
{
  "mcpServers": {
    "schemalens": {
      "command": "C:\\path\\to\\project\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\project\\mcp_server.py"]
    }
  }
}
```

Restart the MCP client after changing its configuration. The server provides:

| Tool | Purpose |
|---|---|
| `get_context_pack` | Returns the full Context Pack |
| `query_documentation` | Returns documentation for a named table |
| `check_drift` | Compares the saved snapshot with the connected database |
| `get_raw_schema` | Returns raw table and column information |

`check_drift` requires a reachable database and valid connection settings.

## Project layout

```text
.
├── agents/
│   ├── business_analyst.py   # LLM-based schema analysis
│   └── data_concierge.py     # Chat and SQL generation
├── connectors/
│   ├── postgres.py           # PostgreSQL and read-only SQLite connections
│   └── sqlite_demo.py        # Builds the local demo database
├── data/
│   ├── schema_snapshot.json  # Included schema and sample rows
│   ├── schema_analysis.json  # Generated analysis
│   ├── context_pack.json     # Machine-readable Context Pack
│   └── documentation.md      # Rendered documentation
├── models/                   # Pydantic schema and analysis models
├── app.py                    # Streamlit application
├── mcp_server.py             # MCP server
├── schema_snapshot.py        # Schema collection pipeline
├── drift_detector.py         # Structural drift comparison
├── markdown_renderer.py      # Markdown documentation renderer
├── pii_masker.py             # Sample-value masking
└── requirements.txt
```

## Demo schema

The included snapshot describes a ten-table cryptocurrency-exchange schema with intentionally obfuscated column names. It includes tables such as `users`, `orders`, `orderexecutions`, `accountbalances`, `riskandmargin`, `fees`, and `marketdata`.

The SQLite demo contains the sample rows from the snapshot. It is intended for trying the application and querying examples, not for evaluating production performance or representing a live database.

## Limitations

- The included SQLite database is a seeded demo, not a connection to your own data. PostgreSQL is available as an optional connector for a database you already have.
- PostgreSQL scanning currently targets the `public` schema.
- PII masking relies on column-name patterns and does not inspect values for sensitive information.
- JSON columns are documented, but their nested fields are not fully modeled as relational columns.
- SQL safety checks use keyword rules rather than a SQL parser. Treat generated SQL as untrusted and use read-only database credentials.
- New analyses and AI chat require a working Fireworks API key and network access.

## Technology

Python, Streamlit, SQLAlchemy, PostgreSQL, SQLite, CrewAI, LangChain, FastMCP, Pydantic, and Fireworks AI.
