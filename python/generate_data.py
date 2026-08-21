"""Main entry point for the synthetic data generator.

Generates customers, products, employees, tickets, and ticket_notes per the
plan in project_context.md and writes them out as CSVs under `data/`. A
later step loads these CSVs into the DuckDB database.

Usage:
    python python/generate_data.py
"""

import csv
import os
import random

from faker import Faker

import config
import reference_data
import tickets


def _write_csv(rows, path, fieldnames):
    # fieldnames controls column order in the CSV since dict key order
    # isn't guaranteed to match across all rows.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    # Seeding both random and Faker keeps a run reproducible; set
    # config.SEED to None for a fresh dataset every run.
    if config.SEED is not None:
        random.seed(config.SEED)
        Faker.seed(config.SEED)
    fake = Faker()

    print("Generating reference data...")
    customers = reference_data.generate_customers(fake)
    products = reference_data.generate_products(fake)
    employees, directors = reference_data.generate_employees(fake)

    # Pick which director's team is tuned to under/overperform on SLO (see
    # tickets.py's bucket-weight logic). Printed below so it can be copied
    # into the README once queries confirm the story shows up in the data.
    underperforming_director = directors[config.UNDERPERFORMING_DIRECTOR_INDEX]
    overperforming_director = directors[config.OVERPERFORMING_DIRECTOR_INDEX]

    print("Generating tickets and ticket_notes...")
    ticket_rows, ticket_note_rows = tickets.generate_tickets_and_notes(
        customers, products, employees, underperforming_director, overperforming_director
    )

    print("Writing CSVs to data/...")
    _write_csv(
        customers,
        os.path.join(config.OUTPUT_DIR, "customers.csv"),
        ["customer_id", "customer_name", "email", "phone_number", "city", "state", "signup_date"],
    )
    _write_csv(
        products,
        os.path.join(config.OUTPUT_DIR, "products.csv"),
        ["product_id", "product_name", "line", "category"],
    )
    _write_csv(
        employees,
        os.path.join(config.OUTPUT_DIR, "employees.csv"),
        ["employee_id", "employee_name", "hire_date", "supervisor_name", "manager_name", "director_name"],
    )
    _write_csv(
        ticket_rows,
        os.path.join(config.OUTPUT_DIR, "tickets.csv"),
        ["ticket_id", "customer_id", "product_id", "initial_employee_id", "status"],
    )
    _write_csv(
        ticket_note_rows,
        os.path.join(config.OUTPUT_DIR, "ticket_notes.csv"),
        ["ticket_note_id", "ticket_id", "employee_id", "category", "created_tstmp"],
    )

    # Quick sanity numbers -- full validation happens in the next project step.
    escalations = sum(1 for n in ticket_note_rows if n["category"] == "escalation")
    resolved_escalations = sum(1 for n in ticket_note_rows if n["category"] == "escalation_resolved")
    closed_tickets = sum(1 for t in ticket_rows if t["status"] == "closed")

    print("\nDone.")
    print(f"  Customers: {len(customers):,}")
    print(f"  Products: {len(products):,}")
    print(f"  Employees: {len(employees):,}")
    print(f"  Tickets: {len(ticket_rows):,} ({closed_tickets:,} closed)")
    print(f"  Ticket notes: {len(ticket_note_rows):,}")
    print(f"  Escalations: {escalations:,} ({resolved_escalations:,} resolved)")
    print(f"\n  Segment story -- underperforming line: {config.UNDERPERFORMING_LINE}")
    print(f"  Segment story -- overperforming line: {config.OVERPERFORMING_LINE}")
    print(f"  Segment story -- underperforming director: {underperforming_director}")
    print(f"  Segment story -- overperforming director: {overperforming_director}")


if __name__ == "__main__":
    main()
