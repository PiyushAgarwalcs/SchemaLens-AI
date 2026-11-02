from models.analysis_models import SchemaAnalysis, TableAnalysis

def _render_table(table: TableAnalysis) -> str:
    lines = [f"## {table.table_name}", "", f"**Purpose:** {table.purpose}", "", "**Columns:**"]
    lines += [f"- `{c.column}`: {c.meaning}" for c in table.column_meanings]
    lines += ["", f"**Relationships:** {table.relationships}", "", f"**Business Value:** {table.business_value}"]
    if table.ambiguity_flags:
        lines += ["", "**⚠️ Ambiguity Flags:**"]
        lines += [f"- `{f.column}`: {f.note}" for f in table.ambiguity_flags]
    return "\n".join(lines) + "\n"

def render_markdown(analysis: SchemaAnalysis) -> str:
    lines = ["# SchemaLens AI — Auto-Generated Documentation", "", f"_Generated: {analysis.generated_at}_", ""]
    lines += [_render_table(t) for t in analysis.tables]
    return "\n".join(lines)