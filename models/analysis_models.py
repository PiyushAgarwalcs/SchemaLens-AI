from pydantic import BaseModel, Field

class ColumnMeaning(BaseModel):
    column: str
    meaning: str

class AmbiguityFlag(BaseModel):
    column: str
    note: str

class TableAnalysis(BaseModel):
    table_name: str
    purpose: str
    column_meanings: list[ColumnMeaning]
    relationships: str
    business_value: str
    ambiguity_flags: list[AmbiguityFlag] = Field(default_factory=list)

class SchemaAnalysis(BaseModel):
    """What gets saved to disk — metadata added by us, not the LLM."""
    generated_at: str
    tables: list[TableAnalysis]
    complexity_score: float = 0.0
    tier: int = 1

class SchemaAnalysisDraft(BaseModel):
    """What the LLM returns — no metadata it can't know."""
    tables: list[TableAnalysis]