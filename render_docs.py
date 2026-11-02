from pathlib import Path
from models.analysis_models import SchemaAnalysis
from markdown_renderer import render_markdown

ANALYSIS_PATH = Path("data/schema_analysis.json")
DOCS_PATH = Path("data/documentation.md")

def load_analysis(path: Path = ANALYSIS_PATH) -> SchemaAnalysis:
    return SchemaAnalysis.model_validate_json(path.read_text(encoding="utf-8"))

if __name__ == "__main__":
    analysis = load_analysis()
    DOCS_PATH.write_text(render_markdown(analysis), encoding="utf-8")
    print(f"Re-rendered documentation.md from cache ({len(analysis.tables)} tables) — 0 LLM calls.")