"""
app.py
------
FastAPI application exposing a POST endpoint for Slack slash commands.

Flow:
  1. Slack sends a POST to /slack/ask-data with form-encoded data.
  2. The `text` field contains the user's natural-language question.
  3. llm.generate_sql() converts the question into a SELECT query.
  4. database.execute_query() runs the query against PostgreSQL.
  5. The results (or an error) are returned to Slack as a JSON payload
     with the message wrapped in a code block.
"""

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse

from llm import generate_sql
from database import execute_query

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Slack AI Data Bot",
    description="Converts natural language to SQL and returns query results in Slack.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_results(sql: str, rows: list[dict]) -> str:
    """
    Build a Slack-friendly message with the generated SQL and query results.

    The output is wrapped in triple-backtick code blocks so it renders
    as monospace in Slack.
    """
    if not rows:
        return f"```\nGenerated SQL:\n{sql}\n\nNo results found.\n```"

    # Build a plain-text table from the list of dicts
    headers = list(rows[0].keys())
    col_widths = {h: len(str(h)) for h in headers}
    for row in rows:
        for h in headers:
            col_widths[h] = max(col_widths[h], len(str(row.get(h, ""))))

    header_line = " | ".join(str(h).ljust(col_widths[h]) for h in headers)
    separator = "-+-".join("-" * col_widths[h] for h in headers)
    data_lines = []
    for row in rows:
        line = " | ".join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers)
        data_lines.append(line)

    table = "\n".join([header_line, separator] + data_lines)
    return f"```\nGenerated SQL:\n{sql}\n\nResults ({len(rows)} rows):\n{table}\n```"


def _format_error(error: str) -> str:
    """Wrap an error message inside a Slack code block."""
    return f"```\nError:\n{error}\n```"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/slack/ask-data")
async def slack_ask_data(text: str = Form("")):
    """
    Slack slash-command handler.

    Slack sends form-encoded POST with fields like `token`, `team_id`,
    `channel_id`, `user_id`, `command`, `text`, etc.  We only need `text`.
    """
    if not text.strip():
        return JSONResponse(
            content={"text": _format_error("Please provide a question after /ask-data.")}
        )

    try:
        # Step 1 – Convert natural language → SQL
        sql = generate_sql(text)

        # Step 2 – Execute SQL against PostgreSQL
        rows = execute_query(sql)

        # Step 3 – Format and return
        message = _format_results(sql, rows)
        return JSONResponse(content={"text": message})

    except ValueError as ve:
        # Raised by database.py when the query is not a SELECT
        return JSONResponse(content={"text": _format_error(str(ve))})

    except Exception as exc:
        # Catch-all for DB connection errors, LLM failures, etc.
        return JSONResponse(content={"text": _format_error(str(exc))})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Simple liveness probe."""
    return {"status": "ok"}
