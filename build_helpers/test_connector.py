# test_connector.py

from connectors.postgres import get_engine, get_schema, sample_rows

def main():
    engine = get_engine()
    schema = get_schema(engine)

    print(f"Found {len(schema)} tables.\n")

    for table in schema:
        print(f"=== {table.table_name} ===")
        for col in table.columns:
            pk_flag = " [PK]" if col.is_primary_key else ""
            fk_flag = f" [FK -> {col.foreign_key}]" if col.foreign_key else ""
            print(f"  {col.name}: {col.type}{pk_flag}{fk_flag}")

        rows = sample_rows(engine, table.table_name, limit=5)
        print(f"  Sample rows: {len(rows)}")
        if rows:
            print(f"  Example: {rows[0].row}")
        print()

if __name__ == "__main__":
    main()