# models/schema_models.py

from pydantic import BaseModel
from typing import Optional, Any

class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    is_primary_key: bool = False
    foreign_key: Optional[str] = None

class TableSchema(BaseModel):
    table_name: str
    columns: list[ColumnInfo]

class SampleRow(BaseModel):
    table_name: str
    row: dict[str, Any]