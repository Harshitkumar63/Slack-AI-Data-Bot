# Slack AI Data Bot

A minimal FastAPI service that lets Slack users query a PostgreSQL database using natural language.  
LangChain + Groq translate the question into SQL; the results are returned directly inside Slack.

---

## Architecture

```
Slack  ──▶  /slack/ask-data  ──▶  llm.py (LangChain + Groq)
                                       │
                                       ▼
                                  database.py (psycopg2 → PostgreSQL)
                                       │
                                       ▼
                                  Formatted response → Slack
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| PostgreSQL | 13+ |
| ngrok | latest |
| Slack workspace with admin access | — |

---

## Installation

```bash
# 1. Clone the repo / navigate to the project folder
cd "Slack_AI Data"

# 2. Create a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Edit the `.env` file and fill in your credentials:

```
GROQ_API_KEY=gsk_...
DB_HOST=localhost
DB_PORT=5432
DB_NAME=analytics
DB_USER=postgres
DB_PASSWORD=your_db_password
```

### Database Setup

Make sure the `analytics` database and `sales_daily` table exist:

```sql
CREATE DATABASE analytics;

\c analytics

CREATE TABLE sales_daily (
    date        DATE          NOT NULL,
    region      TEXT          NOT NULL,
    category    TEXT          NOT NULL,
    revenue     NUMERIC,
    orders      INTEGER,
    created_at  TIMESTAMPTZ   DEFAULT now(),
    PRIMARY KEY (date, region, category)
);

-- Sample data
INSERT INTO sales_daily (date, region, category, revenue, orders) VALUES
('2025-09-01', 'North', 'Electronics', 15000.00, 120),
('2025-09-01', 'South', 'Electronics', 12000.00, 95),
('2025-09-01', 'East',  'Clothing',    8000.00,  60),
('2025-09-01', 'West',  'Clothing',    9500.00,  70);
```

---

## Running the Server

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.  
Health check: `GET http://localhost:8000/health`

---

## Exposing with ngrok

Slack needs a public URL. Use [ngrok](https://ngrok.com/) to tunnel traffic to your local server:

```bash
ngrok http 8000
```

Copy the **Forwarding** URL (e.g. `https://xxxx-xx-xx.ngrok-free.app`).

---

## Configuring the Slack Slash Command

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click **Create New App → From Scratch**.
2. Name it (e.g. *AI Data Bot*) and pick your workspace.
3. In the left sidebar click **Slash Commands → Create New Command**.

| Field | Value |
|-------|-------|
| Command | `/ask-data` |
| Request URL | `https://<ngrok-url>/slack/ask-data` |
| Short Description | Query the database with natural language |
| Usage Hint | `show revenue by region for 2025-09-01` |

4. Click **Save**, then go to **Install App** and install it to your workspace.

---

## Example Usage

In any Slack channel type:

```
/ask-data show revenue by region for 2025-09-01
```

The bot responds with something like:

```
Generated SQL:
SELECT region, revenue FROM sales_daily WHERE date = '2025-09-01';

Results (4 rows):
region | revenue
-------+--------
North  | 15000.00
South  | 12000.00
East   | 8000.00
West   | 9500.00
```

More examples:

```
/ask-data total orders by category last month
/ask-data top 5 regions by revenue
/ask-data average revenue per region for Electronics
```

---

## Project Structure

```
.
├── app.py              # FastAPI app + Slack endpoint
├── database.py         # PostgreSQL connection & query execution
├── llm.py              # LangChain prompt + Groq SQL generation
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
└── README.md           # This file
```

---

## Safety Guardrails

- Only `SELECT` queries are executed — mutations are rejected.
- Dangerous keywords (`INSERT`, `DROP`, `DELETE`, …) are blocked even in subqueries.
- All results are capped at **20 rows** to avoid flooding Slack.
- `temperature=0` keeps SQL generation deterministic.

---

## License

MIT
