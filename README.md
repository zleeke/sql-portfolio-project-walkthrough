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

Imagine a **team-based support desk** where no single rep owns a ticket
end-to-end — a ticket's `initial_rep` (who took the first note) is frequently
not the same rep handling it later (`ticket_notes.rep_name` can differ note
to note). Every ticket accumulates **notes** over time, tagged with a
`note_type` (`general`, `escalation`, `follow_up`, `resolution`).

Leadership wants an early-warning report of **at-risk, potential-churn
tickets**: tickets that are still unresolved (`status` = `open` or `pending`)
whose **first escalation note** was logged within the **last 7 days** — i.e.
"recently escalated for the first time, and still not resolved."

This sounds simple until you consider: a ticket can be escalated more than
once. A ticket whose *first* escalation happened 90 days ago and just got
escalated *again* this week is a different situation than one being escalated
for the very first time this week — but a plain `WHERE created_at >= today -
7` on escalation notes can't distinguish the two. Only looking at "does this
ticket have any escalation note in the last 7 days" would incorrectly lump
both cases together.

This is exactly the class of problem `QUALIFY` + `ROW_NUMBER()` is built for:
rank each ticket's escalation notes by date, keep only the earliest one per
ticket (`row_num = 1`), and filter that row by date — all in one query, no
nested subquery required. The report in
[sql/03_qualify_first_escalation_within_window.sql](sql/03_qualify_first_escalation_within_window.sql)
further prioritizes results by `escalation_count` (repeat escalations are a
bigger red flag) and `ticket_age_days` (a long-open ticket that's now
escalating is riskier than a brand-new one).

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

Five hand-crafted tickets (IDs 1-5) are always present, with note timing fixed
relative to "today" so they reliably exercise **first-occurrence-within-a-window**
edge cases (a ticket escalated more than once, where only the *first*
escalation date should determine whether it counts):

| ticket_id | escalation note timing              | initial escalation age |
|-----------|--------------------------------------|-----------------------------|
| 1         | first 47 days ago, second 35 days ago | 47 days — outside a 45-day window |
| 2         | single escalation, 40 days ago        | 40 days — inside a 45-day window |
| 3         | single escalation, 50 days ago        | 50 days — outside a 45-day window |
| 4         | first 10 days ago, second 2 days ago  | 10 days — inside a 45-day window |
| 5         | no escalation notes at all            | n/a |

These fixed offsets were originally tuned for a 45-day window demo; none of
them fall within the current 7-day at-risk report in
[sql/03_qualify_first_escalation_within_window.sql](sql/03_qualify_first_escalation_within_window.sql),
but they still demonstrate the core "rank and keep the first occurrence"
pattern used throughout [sql/04_equivalent_without_qualify.sql](sql/04_equivalent_without_qualify.sql)
and [sql/05_bonus_qualify_patterns.sql](sql/05_bonus_qualify_patterns.sql).
The remaining ~9,995 randomly generated tickets follow a coherent note
lifecycle (`general` -> optional `escalation` -> optional `follow_up`(s) ->
optional `resolution`), with `status` derived from whether/when a resolution
note exists, and reps drawn from a fixed pool of 20 to simulate the
team-based contact center. Because this data is regenerated relative to
"today," re-run `scripts/generate_data.py` periodically to keep a healthy
number of tickets landing inside the 7-day at-risk window.

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

Both queries are included side by side in [sql/04_equivalent_without_qualify.sql](sql/04_equivalent_without_qualify.sql)
(against the original 45-day escalation example) so you can compare them
directly. [sql/03_qualify_first_escalation_within_window.sql](sql/03_qualify_first_escalation_within_window.sql)
applies the same `QUALIFY` + `ROW_NUMBER()` pattern to the real at-risk-ticket
business report described above, and [sql/05_bonus_qualify_patterns.sql](sql/05_bonus_qualify_patterns.sql)
has a few more "latest/top-N per group" variations.
