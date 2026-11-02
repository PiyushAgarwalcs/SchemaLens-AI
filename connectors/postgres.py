# connectors/postgres.py

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine import URL
import os
from dotenv import load_dotenv

from sqlalchemy.exc import OperationalError

load_dotenv()

_engine: Engine | None = None  # module-level cache, starts empty

def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    db_type = os.getenv("DB_TYPE", "postgresql").lower()
    if db_type == "sqlite":
        db_path = Path(os.getenv("DB_PATH", "data/schemalens_demo.sqlite3")).resolve()
        if not db_path.is_file():
            raise FileNotFoundError(
                f"SQLite database not found: {db_path}. Create it from the included "
                "sample data in the app or with connectors.sqlite_demo."
            )
        connection_url = URL.create(
            "sqlite",
            database=f"file:{db_path.as_posix()}",
            query={"mode": "ro", "uri": "true"},
        )
        connect_args = {"timeout": 10}
    elif db_type == "postgresql":
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")
        if not db_user or db_password is None or not db_name:
            raise ValueError(
                "PostgreSQL needs DB_USER, DB_PASSWORD, and DB_NAME. "
                "Select SQLite demo to run without PostgreSQL credentials."
            )
        connection_url = URL.create(
            "postgresql+psycopg2",
            username=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            database=db_name,
        )
        connect_args = {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000 -c lock_timeout=5000",
        }
    else:
        raise ValueError(f"Unsupported DB_TYPE: {db_type!r}. Use sqlite or postgresql.")

    try:
        _engine = create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        with _engine.connect():  # validate connection immediately
            pass
    except OperationalError as e:
        _engine = None
        raise ConnectionError(f"Could not connect to database: {e.orig}") from e
    return _engine

def reset_engine() -> None:
    global _engine
    _engine = None

from sqlalchemy import inspect
from models.schema_models import ColumnInfo, TableSchema


def get_schema(engine) -> list[TableSchema]:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    schemas = []

    for table_name in tables:
        columns_metadata = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = set(pk_constraint.get("constrained_columns", []))

        fk_lookup = {}
        for fk in inspector.get_foreign_keys(table_name):
            referred_table = fk["referred_table"]
            for local_col, remote_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                fk_lookup[local_col] = f"{referred_table}.{remote_col}"

        columns = []
        for col in columns_metadata:
            columns.append(ColumnInfo(
                name=col["name"],
                type=str(col["type"]),
                nullable=col["nullable"],
                is_primary_key=col["name"] in pk_columns,
                foreign_key=fk_lookup.get(col["name"]),
            ))

        schemas.append(TableSchema(table_name=table_name, columns=columns))

    return schemas


def _select_columns_adaptive(columns: list[ColumnInfo], budget: int) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()

    def _add(name: str):
        if name not in seen and len(selected) < budget:
            selected.append(name)
            seen.add(name)

    # Priority 1 — PKs and FK columns
    for c in columns:
        if c.is_primary_key or c.foreign_key is not None:
            _add(c.name)

    # Priority 2 — NOT NULL columns
    for c in columns:
        if not c.nullable:
            _add(c.name)

    # Priority 3 — business-signal patterns
    _PATTERNS = ("_status", "_date", "_amount", "_type", "_name", "_code",
                 "status", "date", "amount", "type", "name", "code")
    for c in columns:
        if any(p in c.name.lower() for p in _PATTERNS):
            _add(c.name)

    # Fill remaining budget in original column order
    for c in columns:
        _add(c.name)

    return selected


def _truncate_strings(row: dict, max_len: int = 150) -> dict:
    return {
        k: (v[:max_len] if isinstance(v, str) and len(v) > max_len else v)
        for k, v in row.items()
    }



from sqlalchemy import text
from models.schema_models import SampleRow

def sample_rows(
    engine,
    table_name: str,
    limit: int = 8,
    columns: list[ColumnInfo] | None = None,
) -> list[SampleRow]:
    n_cols = len(columns) if columns else 0

    if columns is None or n_cols <= 50:
        col_clause = "*"
        row_limit = limit
    elif n_cols <= 150:
        selected = _select_columns_adaptive(columns, budget=50)
        col_clause = ", ".join(f'"{c}"' for c in selected)
        row_limit = limit
    else:
        selected = _select_columns_adaptive(columns, budget=20)
        col_clause = ", ".join(f'"{c}"' for c in selected)
        row_limit = 3

    query = text(f'SELECT {col_clause} FROM "{table_name}" LIMIT :limit')
    with engine.connect() as conn:
        result = conn.execute(query, {"limit": row_limit})
        rows = result.mappings().all()

    return [SampleRow(table_name=table_name, row=_truncate_strings(dict(row))) for row in rows]