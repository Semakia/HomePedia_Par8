"""Load DAG documentation from Markdown files in `dags/config/`.

Keeps the prose out of the DAG modules: each DAG passes `doc_md=load_doc("x")`
and the text lives in `dags/config/x.md` (rendered in the Airflow UI "Docs"
panel). Missing/empty files degrade to an empty string so a DAG never fails to
parse over documentation.
"""

from __future__ import annotations

from pathlib import Path

# dags/utils/dag_docs.py -> dags/config
_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_doc(name: str) -> str:
    """Return the Markdown in `dags/config/<name>.md` ("" if absent)."""
    try:
        return (_CONFIG_DIR / f"{name}.md").read_text(encoding="utf-8")
    except OSError:
        return ""
