"""Builds the DuckDB database from the generated CSVs in `data/`.

Creates `data/support_tickets.db` from scratch (overwriting any existing
file) with the schema locked in project_context.md, then loads each CSV in
FK-safe order: customers/products/employees, then tickets, then
ticket_notes.

Usage:
    python python/build_database.py
"""

import os

import duckdb

import config

DB_PATH = os.path.join(config.OUTPUT_DIR, "support_tickets.db")

# Mirrors the locked schema in project_context.md, including the FK and
# CHECK constraints DuckDB enforces at insert time below.
SCHEMA_SQL = """
CREATE TABLE customers (
    customer_id     INTEGER PRIMARY KEY,
    customer_name   VARCHAR NOT NULL,
    email           VARCHAR NOT NULL,
    phone_number    VARCHAR NOT NULL,
    city            VARCHAR NOT NULL,
    state           VARCHAR NOT NULL,
    signup_date     DATE NOT NULL
);

CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY,
    product_name    VARCHAR NOT NULL,
    line            VARCHAR NOT NULL,
    category        VARCHAR NOT NULL
);

CREATE TABLE employees (
    employee_id     INTEGER PRIMARY KEY,
    employee_name   VARCHAR NOT NULL,
    hire_date       DATE NOT NULL,
    supervisor_name VARCHAR NOT NULL,
    manager_name    VARCHAR NOT NULL,
    director_name   VARCHAR NOT NULL
);

CREATE TABLE tickets (
    ticket_id           INTEGER PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES customers (customer_id),
    product_id          INTEGER NOT NULL REFERENCES products (product_id),
    initial_employee_id INTEGER NOT NULL REFERENCES employees (employee_id),
    status              VARCHAR NOT NULL CHECK (status IN ('open', 'closed'))
);

CREATE TABLE ticket_notes (
    ticket_note_id  INTEGER PRIMARY KEY,
    ticket_id       INTEGER NOT NULL REFERENCES tickets (ticket_id),
    employee_id     INTEGER NOT NULL REFERENCES employees (employee_id),
    category        VARCHAR NOT NULL CHECK (
        category IN (
            'general_information',
            'follow_up',
            'escalation',
            'escalation_resolved',
            'resolved'
        )
    ),
    created_tstmp   TIMESTAMP NOT NULL
);
"""

LOAD_ORDER = ["customers", "products", "employees", "tickets", "ticket_notes"]


def main():
    # Always rebuild from scratch so the schema/constraints and data stay
    # in sync with whatever CSVs are currently in data/.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = duckdb.connect(DB_PATH)
    con.execute(SCHEMA_SQL)

    # Parent tables must load before the tables that reference them, or the
    # FK constraints below will reject the inserts.
    for table in LOAD_ORDER:
        csv_path = os.path.join(config.OUTPUT_DIR, f"{table}.csv")
        con.execute(f"INSERT INTO {table} SELECT * FROM read_csv_auto('{csv_path}')")

    print(f"Built {DB_PATH}")
    for table in LOAD_ORDER:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} rows")

    con.close()


if __name__ == "__main__":
    main()
