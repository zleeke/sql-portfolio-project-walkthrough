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
`note_type` (`general`, `escalation`, `escalation_resolved`, `follow_up`,
`resolution`).

The desk has a **48-hour SLO** for addressing an escalation once it's raised.
Leadership doesn't just want a list of "tickets that got escalated" — they
want every escalation classified into one of three actionable buckets:

1. **At risk** — not yet resolved, still inside the 48-hour SLO, but old
   enough (32+ hours) that it needs attention *now* before it breaches.
2. **Resolved late** — an `escalation_resolved` note exists, but it landed
   more than 48 hours after the escalation.
3. **Breached, still unresolved** — no `escalation_resolved` note, and the
   48-hour SLO has already passed.

This sounds simple until you consider: a ticket can be escalated more than
once, and each escalation needs to be matched to *its own* resolution — not
just "has this ticket ever had a resolved escalation." A ticket whose first
escalation was closed out cleanly last month but has since been escalated
again is a very different situation from one that's never been resolved at
all, even though both technically "have a resolved escalation somewhere in
their history."

This is exactly the class of problem `QUALIFY` + window functions is built
for: pair each escalation note with the *next* `escalation_resolved` note
that follows it (per ticket), then classify the pair by how much time
elapsed relative to the 48-hour SLO. The report in
[sql/03_escalation_sla_status.sql](sql/03_escalation_sla_status.sql) does
exactly that.

## Project structure

```
sql-return-latest-example/
├── README.md
├── requirements.txt
├── scripts/
│   └── generate_data.py        # Faker-based synthetic data generator
├── sql/
│   ├── 01_create_schema.sql        # table definitions
│   ├── 02_load_data.sql            # loads the generated CSVs into DuckDB
│   └── 03_escalation_sla_status.sql  # the main demo: 48h escalation SLO report
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
   .read sql/03_escalation_sla_status.sql
   ```

## The demo tickets

Six hand-crafted tickets (IDs 1-6) are always present, with note timing fixed
relative to "today" so they reliably exercise all three SLO buckets plus a
couple of control cases:

| ticket_id | escalation timing                                   | outcome |
|-----------|-------------------------------------------------------|---------|
| 1         | escalated 40 hours ago, still unresolved               | **At risk** — past the 32h threshold, inside the 48h SLO |
| 2         | escalated 200 hours ago, resolved 100 hours ago         | **Resolved late** — took 100h, outside the 48h SLO |
| 3         | escalated 120 hours ago, still unresolved               | **Breached** — past the 48h SLO, unresolved |
| 4         | escalated 50 hours ago, resolved 20 hours ago           | Within SLO (control — resolved in 30h, should NOT appear) |
| 5         | no escalation notes at all                              | control — should NOT appear |
| 6         | first escalation resolved within SLO, second escalated 40 hours ago and still open | first escalation healthy, second is **At risk** — proves each escalation is paired with its own resolution |

The remaining ~9,994 randomly generated tickets follow a coherent note
lifecycle (`general` -> optional `escalation` -> optional
`escalation_resolved` -> optional `follow_up`(s) -> optional `resolution`),
with `status` derived from whether/when a resolution note exists, and reps
drawn from a fixed pool of 20 to simulate the team-based contact center.
About 10% of escalated tickets get re-escalated a second time, and a small
share (~2.5%) of resolved escalations log a duplicate `escalation_resolved`
note shortly after the first, simulating messy real-world contact-center
data entry. Because this data is regenerated relative to "today," re-run
`scripts/generate_data.py` periodically to keep a healthy number of
escalations landing in each SLO bucket.

## Why `QUALIFY` matters

Without `QUALIFY`, matching each escalation to its nearest following
resolution would require computing the window function in a CTE/subquery
and then filtering in an outer `WHERE`:

```sql
WITH candidates AS (
    SELECT
        e.ticket_id,
        e.note_id AS escalation_note_id,
        e.created_at AS escalation_at,
        r.created_at AS resolved_at,
        ROW_NUMBER() OVER (
            PARTITION BY e.ticket_id, e.note_id
            ORDER BY r.created_at ASC
        ) AS rn
    FROM ticket_notes e
    LEFT JOIN ticket_notes r
        ON r.ticket_id = e.ticket_id
       AND r.note_type = 'escalation_resolved'
       AND r.created_at > e.created_at
    WHERE e.note_type = 'escalation'
)
SELECT *
FROM candidates
WHERE rn = 1;
```

With `QUALIFY`, the same logic collapses into a single `SELECT`:

```sql
SELECT
    e.ticket_id,
    e.note_id AS escalation_note_id,
    e.created_at AS escalation_at,
    r.created_at AS resolved_at
FROM ticket_notes e
LEFT JOIN ticket_notes r
    ON r.ticket_id = e.ticket_id
   AND r.note_type = 'escalation_resolved'
   AND r.created_at > e.created_at
WHERE e.note_type = 'escalation'
QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY e.ticket_id, e.note_id
        ORDER BY r.created_at ASC
    ) = 1;
```

[sql/03_escalation_sla_status.sql](sql/03_escalation_sla_status.sql) uses
exactly this pattern to pair each escalation with its nearest resolution,
then classifies the result against the 48-hour SLO into the three
actionable buckets described above.
