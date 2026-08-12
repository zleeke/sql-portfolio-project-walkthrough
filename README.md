# SQL `QUALIFY` Demo — Returning the "First Within a Window" Record

A small, self-contained project that demonstrates one of the more underused
pieces of SQL syntax: the **`QUALIFY`** clause. `QUALIFY` lets you filter on
the result of a window function (`ROW_NUMBER()`, `RANK()`, etc.) directly,
without wrapping your query in a subquery/CTE just to apply a `WHERE` on a
calculated column.

This project uses **DuckDB** (not SQLite) because SQLite does not implement
`QUALIFY` — it's supported by DuckDB, Snowflake, BigQuery, and Teradata. DuckDB
is a great free/local choice because it runs as a single file, has a real SQL
CLI, and is well supported by SQL extensions in VS Code.

## The business scenario

Imagine a support desk where every ticket can accumulate multiple **notes**
over time, tagged with a `note_type` (`general`, `escalation`, `follow_up`,
`resolution`). Leadership wants a report of tickets whose **initial escalation
note** was logged within the **last 45 days** — i.e. "recently escalated for
the first time."

This sounds simple until you consider: a ticket can be escalated more than
once. If a ticket's *first* escalation note was logged 47 days ago, and a
*second* escalation note was logged 35 days ago, that ticket should **not**
appear in the report — the initial escalation is what matters, and it fell
outside the 45-day window. Only looking at "does this ticket have any
escalation note in the last 45 days" would incorrectly include it.

This is exactly the class of problem `QUALIFY` + `ROW_NUMBER()` is built for:
rank each ticket's escalation notes by date, keep only the earliest one per
ticket (`row_num = 1`), and filter that row by date — all in one query, no
nested subquery required.

## Project structure

```
sql-return-latest-example/
├── README.md
├── requirements.txt
├── scripts/
│   └── generate_data.py        # Faker-based synthetic data generator
├── sql/
│   ├── 01_create_schema.sql    # table definitions
│   ├── 02_load_data.sql        # loads the generated CSVs into DuckDB
│   ├── 03_qualify_first_escalation_within_window.sql   # the main demo
│   ├── 04_equivalent_without_qualify.sql                # same result, no QUALIFY
│   └── 05_bonus_qualify_patterns.sql                    # more "latest N" examples
├── data/                        # generated CSVs land here (gitignored)
└── db/                          # the DuckDB database file lands here (gitignored)
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Generate the synthetic data (10,000 tickets, plus a variable number of
   notes per ticket):

   ```bash
   python scripts/generate_data.py
   ```

   This writes `data/tickets.csv` and `data/ticket_notes.csv`. The script is
   seeded (`Faker.seed(42)` / `random.seed(42)`) so the random portion of the
   data is reproducible, and it always injects five hand-crafted "demo"
   tickets (IDs 1–5) whose note timing intentionally exercises the edge cases
   described above.

3. Install a DuckDB SQL extension in VS Code (search the Extensions
   marketplace for "DuckDB"), or use the [DuckDB CLI](https://duckdb.org/docs/api/cli/overview).
   Either way, point it at `db/support_tickets.duckdb` (the file will be
   created automatically the first time you run the schema script).

4. Run the SQL scripts in order, either by opening each file and executing it
   with your VS Code SQL extension, or from the DuckDB CLI:

   ```bash
   duckdb db/support_tickets.duckdb
   .read sql/01_create_schema.sql
   .read sql/02_load_data.sql
   .read sql/03_qualify_first_escalation_within_window.sql
   .read sql/04_equivalent_without_qualify.sql
   .read sql/05_bonus_qualify_patterns.sql
   ```

## The demo tickets

| ticket_id | escalation note timing              | expected in 45-day report? |
|-----------|--------------------------------------|-----------------------------|
| 1         | first 47 days ago, second 35 days ago | **No** — first escalation is outside the window |
| 2         | single escalation, 40 days ago        | Yes |
| 3         | single escalation, 50 days ago        | No |
| 4         | first 10 days ago, second 2 days ago  | Yes — first escalation is inside the window |
| 5         | no escalation notes at all            | No |

Because the random data is regenerated relative to "today," re-run
`scripts/generate_data.py` if you come back to this project much later and
want the 45-day window to still line up with the demo tickets above (the
demo tickets are always generated relative to the current date, so the table
above holds true every time you regenerate).

## Why `QUALIFY` matters

Without `QUALIFY`, you have to compute the window function in a CTE/subquery
and then filter in an outer `WHERE`:

```sql
WITH ranked AS (
    SELECT
        n.*,
        ROW_NUMBER() OVER (
            PARTITION BY n.ticket_id
            ORDER BY n.created_at ASC
        ) AS rn
    FROM ticket_notes n
    WHERE n.note_type = 'escalation'
)
SELECT *
FROM ranked
WHERE rn = 1
  AND created_at >= CURRENT_DATE - INTERVAL 45 DAY;
```

With `QUALIFY`, the same logic collapses into a single `SELECT`:

```sql
SELECT
    n.*,
    ROW_NUMBER() OVER (
        PARTITION BY n.ticket_id
        ORDER BY n.created_at ASC
    ) AS rn
FROM ticket_notes n
WHERE n.note_type = 'escalation'
QUALIFY rn = 1
    AND created_at >= CURRENT_DATE - INTERVAL 45 DAY;
```

Both queries are included side by side in [sql/03_qualify_first_escalation_within_window.sql](sql/03_qualify_first_escalation_within_window.sql)
and [sql/04_equivalent_without_qualify.sql](sql/04_equivalent_without_qualify.sql)
so you can compare them directly.
