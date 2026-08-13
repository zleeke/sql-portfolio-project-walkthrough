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

PRODUCTS = ["Billing", "Mobile App", "Website", "API", "Hardware"]
REP_COUNT = 20  # simulates a team-based contact center (no single rep owns a ticket)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

REPS = [fake.name() for _ in range(REP_COUNT)]


def days_ago(n: int) -> datetime:
    return datetime.now() - timedelta(days=n)


def build_curated_tickets():
    """Hand-crafted tickets/notes that exercise the 45-day-window edge cases."""
    reps = REPS[:5]  # ticket N's initial rep is reps[N-1]

    tickets = [
        {
            "ticket_id": 1,
            "customer_name": fake.name(),
            "product": "Billing",
            "opened_at": days_ago(90),
            "status": "open",
            "initial_rep": reps[0],
        },
        {
            "ticket_id": 2,
            "customer_name": fake.name(),
            "product": "Mobile App",
            "opened_at": days_ago(60),
            "status": "pending",
            "initial_rep": reps[1],
        },
        {
            "ticket_id": 3,
            "customer_name": fake.name(),
            "product": "Website",
            "opened_at": days_ago(80),
            "status": "resolved",
            "initial_rep": reps[2],
        },
        {
            "ticket_id": 4,
            "customer_name": fake.name(),
            "product": "API",
            "opened_at": days_ago(15),
            "status": "open",
            "initial_rep": reps[3],
        },
        {
            "ticket_id": 5,
            "customer_name": fake.name(),
            "product": "Hardware",
            "opened_at": days_ago(30),
            "status": "closed",
            "initial_rep": reps[4],
        },
    ]

    notes = [
        # Ticket 1: initial escalation outside the window (47d), second one inside (35d).
        {"ticket_id": 1, "rep_name": reps[0], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(89)},
        {"ticket_id": 1, "rep_name": REPS[5], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(47)},
        {"ticket_id": 1, "rep_name": REPS[6], "note_type": "escalation", "note_text": "Escalated to tier 3.", "created_at": days_ago(35)},
        {"ticket_id": 1, "rep_name": REPS[5], "note_type": "follow_up", "note_text": "Checked in with customer.", "created_at": days_ago(20)},

        # Ticket 2: single escalation inside the window (40d).
        {"ticket_id": 2, "rep_name": reps[1], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(58)},
        {"ticket_id": 2, "rep_name": REPS[7], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(40)},

        # Ticket 3: single escalation outside the window (50d).
        {"ticket_id": 3, "rep_name": reps[2], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(79)},
        {"ticket_id": 3, "rep_name": REPS[8], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(50)},
        {"ticket_id": 3, "rep_name": REPS[8], "note_type": "resolution", "note_text": "Issue resolved.", "created_at": days_ago(40)},

        # Ticket 4: initial escalation inside the window (10d), second one even more recent (2d).
        {"ticket_id": 4, "rep_name": reps[3], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(14)},
        {"ticket_id": 4, "rep_name": REPS[9], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": days_ago(10)},
        {"ticket_id": 4, "rep_name": REPS[10], "note_type": "escalation", "note_text": "Escalated to tier 3.", "created_at": days_ago(2)},

        # Ticket 5: no escalation notes at all.
        {"ticket_id": 5, "rep_name": reps[4], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(29)},
        {"ticket_id": 5, "rep_name": REPS[11], "note_type": "follow_up", "note_text": "Checked in with customer.", "created_at": days_ago(20)},
        {"ticket_id": 5, "rep_name": REPS[11], "note_type": "resolution", "note_text": "Issue resolved.", "created_at": days_ago(5)},
    ]

    return tickets, notes


def build_random_tickets(start_id: int, count: int):
    """Builds tickets whose notes follow a coherent lifecycle (general ->
    optional escalation -> optional follow-ups -> optional resolution), with
    `status` derived from what actually happened rather than picked at random.
    """
    tickets = []
    notes = []

    for ticket_id in range(start_id, start_id + count):
        opened_at = fake.date_time_between(start_date="-2y", end_date="-60d")
        initial_rep = random.choice(REPS)
        age_days = (datetime.now() - opened_at).days

        ticket_notes = [
            {
                "note_type": "general",
                "note_text": fake.sentence(nb_words=8),
                "created_at": opened_at + timedelta(hours=random.uniform(0, 4)),
                "rep_name": initial_rep,
            }
        ]

        if random.random() < 0.20:  # some tickets get escalated
            ticket_notes.append(
                {
                    "note_type": "escalation",
                    "note_text": fake.sentence(nb_words=8),
                    "created_at": ticket_notes[-1]["created_at"] + timedelta(days=random.uniform(1, 10)),
                    "rep_name": random.choice(REPS),
                }
            )

        num_follow_ups = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]
        for _ in range(num_follow_ups):
            ticket_notes.append(
                {
                    "note_type": "follow_up",
                    "note_text": fake.sentence(nb_words=8),
                    "created_at": ticket_notes[-1]["created_at"] + timedelta(days=random.uniform(1, 7)),
                    "rep_name": random.choice(REPS),
                }
            )

        # Older tickets are more likely to have reached a terminal resolution.
        resolve_probability = min(0.9, 0.3 + (age_days / 365) * 0.5)
        resolved = random.random() < resolve_probability
        if resolved:
            ticket_notes.append(
                {
                    "note_type": "resolution",
                    "note_text": fake.sentence(nb_words=8),
                    "created_at": ticket_notes[-1]["created_at"] + timedelta(days=random.uniform(0.5, 5)),
                    "rep_name": random.choice(REPS),
                }
            )
            status = random.choices(["resolved", "closed"], weights=[0.4, 0.6])[0]
        else:
            status = random.choices(["open", "pending"], weights=[0.5, 0.5])[0]

        now = datetime.now()
        for note in ticket_notes:
            if note["created_at"] > now:
                note["created_at"] = now

        tickets.append(
            {
                "ticket_id": ticket_id,
                "customer_name": fake.name(),
                "product": random.choice(PRODUCTS),
                "opened_at": opened_at,
                "status": status,
                "initial_rep": initial_rep,
            }
        )

        for note in ticket_notes:
            notes.append({"ticket_id": ticket_id, **note})

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
        fieldnames=["ticket_id", "customer_name", "product", "opened_at", "status", "initial_rep"],
    )
    write_csv(
        DATA_DIR / "ticket_notes.csv",
        all_notes,
        fieldnames=["note_id", "ticket_id", "rep_name", "note_type", "note_text", "created_at"],
    )

    print(f"Wrote {len(all_tickets):,} tickets to {DATA_DIR / 'tickets.csv'}")
    print(f"Wrote {len(all_notes):,} ticket notes to {DATA_DIR / 'ticket_notes.csv'}")


if __name__ == "__main__":
    main()
