"""
Generates synthetic support-ticket data for the QUALIFY demo project.

Produces two CSVs:
  - data/tickets.csv       (10,000 tickets)
  - data/ticket_notes.csv  (a variable number of notes per ticket)

Five tickets (IDs 1-5) are hand-crafted rather than randomized, so the
edge cases described in README.md are always present in the data:

  ticket_id 1: two escalation notes (47 days ago, then 35 days ago)
               -> should NOT appear in the "escalated in last 45 days" report,
                  because the *initial* escalation is outside the window.
  ticket_id 2: one escalation note (40 days ago)
               -> SHOULD appear.
  ticket_id 3: one escalation note (50 days ago)
               -> should NOT appear.
  ticket_id 4: two escalation notes (10 days ago, then 2 days ago)
               -> SHOULD appear, because the *initial* escalation is inside
                  the window (the second note doesn't change that).
  ticket_id 5: no escalation notes at all (general/follow_up/resolution only)
               -> should NOT appear.

The remaining 9,995 tickets are randomized (with a fixed seed for
reproducibility) so the demo also has a realistic volume of "noise" data
to query against.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
TOTAL_TICKETS = 10_000
CURATED_TICKET_IDS = {1, 2, 3, 4, 5}

NOTE_TYPES = ["general", "escalation", "follow_up", "resolution"]
NOTE_TYPE_WEIGHTS = [0.55, 0.15, 0.20, 0.10]
PRODUCTS = ["Billing", "Mobile App", "Website", "API", "Hardware"]
STATUSES = ["open", "pending", "resolved", "closed"]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)


def days_ago(n: int) -> datetime:
    return datetime.now() - timedelta(days=n)


def build_curated_tickets():
    """Hand-crafted tickets/notes that exercise the 45-day-window edge cases."""
    tickets = [
        {
            "ticket_id": 1,
            "customer_name": fake.name(),
            "product": "Billing",
            "opened_at": days_ago(90),
            "status": "open",
        },
        {
            "ticket_id": 2,
            "customer_name": fake.name(),
            "product": "Mobile App",
            "opened_at": days_ago(60),
            "status": "pending",
        },
        {
            "ticket_id": 3,
            "customer_name": fake.name(),
            "product": "Website",
            "opened_at": days_ago(80),
            "status": "resolved",
        },
        {
            "ticket_id": 4,
            "customer_name": fake.name(),
            "product": "API",
            "opened_at": days_ago(15),
            "status": "open",
        },
        {
            "ticket_id": 5,
            "customer_name": fake.name(),
            "product": "Hardware",
            "opened_at": days_ago(30),
            "status": "closed",
        },
    ]

    notes = [
        # Ticket 1: initial escalation outside the window (47d), second one inside (35d).
        {"ticket_id": 1, "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(89)},
        {"ticket_id": 1, "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(47)},
        {"ticket_id": 1, "note_type": "escalation", "note_text": "Escalated to tier 3.", "created_at": days_ago(35)},
        {"ticket_id": 1, "note_type": "follow_up", "note_text": "Checked in with customer.", "created_at": days_ago(20)},

        # Ticket 2: single escalation inside the window (40d).
        {"ticket_id": 2, "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(58)},
        {"ticket_id": 2, "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(40)},

        # Ticket 3: single escalation outside the window (50d).
        {"ticket_id": 3, "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(79)},
        {"ticket_id": 3, "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(50)},
        {"ticket_id": 3, "note_type": "resolution", "note_text": "Issue resolved.", "created_at": days_ago(40)},

        # Ticket 4: initial escalation inside the window (10d), second one even more recent (2d).
        {"ticket_id": 4, "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(14)},
        {"ticket_id": 4, "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(10)},
        {"ticket_id": 4, "note_type": "escalation", "note_text": "Escalated to tier 3.", "created_at": days_ago(2)},

        # Ticket 5: no escalation notes at all.
        {"ticket_id": 5, "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(29)},
        {"ticket_id": 5, "note_type": "follow_up", "note_text": "Checked in with customer.", "created_at": days_ago(20)},
        {"ticket_id": 5, "note_type": "resolution", "note_text": "Issue resolved.", "created_at": days_ago(5)},
    ]

    return tickets, notes


def build_random_tickets(start_id: int, count: int):
    tickets = []
    notes = []

    for ticket_id in range(start_id, start_id + count):
        opened_at = fake.date_time_between(start_date="-2y", end_date="-60d")
        tickets.append(
            {
                "ticket_id": ticket_id,
                "customer_name": fake.name(),
                "product": random.choice(PRODUCTS),
                "opened_at": opened_at,
                "status": random.choice(STATUSES),
            }
        )

        num_notes = random.choices([0, 1, 2, 3, 4], weights=[0.15, 0.35, 0.25, 0.15, 0.10])[0]
        for _ in range(num_notes):
            note_date = fake.date_time_between(start_date=opened_at, end_date="now")
            notes.append(
                {
                    "ticket_id": ticket_id,
                    "note_type": random.choices(NOTE_TYPES, weights=NOTE_TYPE_WEIGHTS)[0],
                    "note_text": fake.sentence(nb_words=8),
                    "created_at": note_date,
                }
            )

    return tickets, notes


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    curated_tickets, curated_notes = build_curated_tickets()
    random_tickets, random_notes = build_random_tickets(
        start_id=6, count=TOTAL_TICKETS - len(CURATED_TICKET_IDS)
    )

    all_tickets = curated_tickets + random_tickets

    # Assign sequential note IDs after all notes are collected.
    all_notes = curated_notes + random_notes
    for note_id, note in enumerate(all_notes, start=1):
        note["note_id"] = note_id

    write_csv(
        DATA_DIR / "tickets.csv",
        all_tickets,
        fieldnames=["ticket_id", "customer_name", "product", "opened_at", "status"],
    )
    write_csv(
        DATA_DIR / "ticket_notes.csv",
        all_notes,
        fieldnames=["note_id", "ticket_id", "note_type", "note_text", "created_at"],
    )

    print(f"Wrote {len(all_tickets):,} tickets to {DATA_DIR / 'tickets.csv'}")
    print(f"Wrote {len(all_notes):,} ticket notes to {DATA_DIR / 'ticket_notes.csv'}")


if __name__ == "__main__":
    main()
