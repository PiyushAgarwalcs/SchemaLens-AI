import json
import tempfile
from pathlib import Path

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    Table,
    Text,
    create_engine,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "data" / "schema_snapshot.json"
DATABASE_PATH = ROOT / "data" / "schemalens_demo.sqlite3"


def _sqlite_type(column_type: str):
    normalized = column_type.upper().split("(", 1)[0].strip()
    if normalized in {"JSON", "JSONB"}:
        return JSON()
    if normalized in {"BOOL", "BOOLEAN"}:
        return Boolean()
    if normalized in {"BIGINT", "BIGSERIAL"}:
        return BigInteger()
    if normalized in {"INT", "INTEGER", "SMALLINT", "SERIAL", "SMALLSERIAL"}:
        return Integer()
    if normalized in {"REAL", "FLOAT", "DOUBLE", "DOUBLE PRECISION"}:
        return Float()
    if normalized in {"NUMERIC", "DECIMAL", "MONEY"}:
        return Numeric()
    if normalized in {"BYTEA", "BLOB"}:
        return LargeBinary()
    if normalized in {"TEXT", "XML"}:
        return Text()
    return Text()


def create_demo_database(
    snapshot_path: Path = SNAPSHOT_PATH,
    database_path: Path = DATABASE_PATH,
) -> Path:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    tables = snapshot.get("tables")
    if not isinstance(tables, list) or not tables:
        raise ValueError(f"No tables found in schema snapshot: {snapshot_path}")

    metadata = MetaData()
    table_definitions = {}
    for table_data in tables:
        columns = []
        for column_data in table_data["columns"]:
            args = []
            foreign_key = column_data.get("foreign_key")
            if foreign_key:
                args.append(ForeignKey(foreign_key))
            columns.append(
                Column(
                    column_data["name"],
                    _sqlite_type(column_data.get("type", "")),
                    *args,
                    primary_key=column_data.get("is_primary_key", False),
                    nullable=column_data.get("nullable", True),
                )
            )
        table_definitions[table_data["table_name"]] = Table(
            table_data["table_name"], metadata, *columns
        )

    database_path = Path(database_path).resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {database_path}")
    with tempfile.NamedTemporaryFile(
        dir=database_path.parent, suffix=".sqlite3", delete=False
    ) as temp_file:
        temporary_path = Path(temp_file.name)

    engine = create_engine(f"sqlite:///{temporary_path.as_posix()}")
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            for table_data in tables:
                rows = table_data.get("sample_rows", [])
                if rows:
                    connection.execute(
                        table_definitions[table_data["table_name"]].insert(),
                        [
                            {
                                column: None if value == "[MASKED]" else value
                                for column, value in row.items()
                            }
                            for row in rows
                        ],
                    )
    except Exception:
        engine.dispose()
        temporary_path.unlink(missing_ok=True)
        raise
    engine.dispose()
    temporary_path.replace(database_path)
    return database_path
