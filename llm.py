"""
llm.py
------
Natural-language → SQL translation layer powered by LangChain + Groq.

- Uses ChatGroq with temperature=0 for deterministic output.
- A strict prompt template embeds the full table schema so the model
  never invents columns or tables.
- Returns a single raw SELECT statement (no markdown, no explanation).
"""

import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# ---------------------------------------------------------------------------
# Schema reference injected into every prompt
# ---------------------------------------------------------------------------

TABLE_SCHEMA = """
Database : analytics
Table    : sales_daily

Columns:
  date        DATE          (part of composite primary key)
  region      TEXT          (part of composite primary key)
  category    TEXT          (part of composite primary key)
  revenue     NUMERIC
  orders      INTEGER
  created_at  TIMESTAMPTZ   (default now())
""".strip()

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a PostgreSQL SQL expert. "
    "Given the table schema below and a user question, generate a single "
    "valid SELECT query that answers the question.\n\n"
    "Rules:\n"
    "1. Output ONLY the SQL query — no explanation, no markdown fences.\n"
    "2. The query MUST be a SELECT statement.\n"
    "3. Never use INSERT, UPDATE, DELETE, DROP, or any DDL/DML.\n"
    "4. Use only columns that exist in the schema.\n"
    "5. If the user asks for something impossible with the schema, "
    "return: SELECT 'Sorry, the requested data is not available.' AS message;\n\n"
    f"Schema:\n{TABLE_SCHEMA}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)

# ---------------------------------------------------------------------------
# LLM instance (lazy-initialised on first call)
# ---------------------------------------------------------------------------

_llm = None


def _get_llm() -> ChatGroq:
    """Return a singleton ChatGroq instance."""
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )
    return _llm


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_sql(question: str) -> str:
    """
    Convert a natural-language question into a raw SQL SELECT string.

    Parameters
    ----------
    question : str
        The human question, e.g. "show revenue by region for 2025-09-01".

    Returns
    -------
    str
        A single SELECT statement ready for execution.
    """
    chain = prompt | _get_llm()
    response = chain.invoke({"question": question})
    sql = response.content.strip()

    # Strip markdown code fences if the model wraps them anyway
    if sql.startswith("```"):
        sql = sql.strip("`").removeprefix("sql").strip()

    return sql
