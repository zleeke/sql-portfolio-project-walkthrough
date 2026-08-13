"""
Generates synthetic support-ticket data for the QUALIFY demo project.

Produces two CSVs:
  - data/tickets.csv       (10,000 tickets)
  - data/ticket_notes.csv  (a variable number of notes per ticket)

The business rule being simulated: escalations have a 48-hour SLO
(`SLO_HOURS`), and an escalation is considered "at risk" once it has gone
`AT_RISK_THRESHOLD_HOURS` (32h, ~2/3 of the SLO) without a matching
`escalation_resolved` note. Six tickets (IDs 1-6) are hand-crafted rather
than randomized, so all three SLO buckets are always present in the data:

  ticket_id 1: escalated 40 hours ago, still unresolved
               -> AT RISK (past the 32h threshold, inside the 48h SLO).
  ticket_id 2: escalated 200 hours ago, resolved 100 hours ago
               -> RESOLVED LATE (took 100h to resolve, outside the 48h SLO).
  ticket_id 3: escalated 120 hours ago, still unresolved
               -> BREACHED (past the 48h SLO, still unresolved).
  ticket_id 4: escalated 50 hours ago, resolved 20 hours ago
               -> WITHIN SLO (resolved in 30h; control case, should NOT
                  appear in the SLO report).
  ticket_id 5: no escalation notes at all
               -> control case, should NOT appear in the SLO report.
  ticket_id 6: two escalations - the first resolved well within SLO, the
               second still open at 40 hours
               -> the first escalation is healthy and the second is AT
                  RISK, proving each escalation must be paired with its
                  own resolution rather than just checking "has this
                  ticket ever had a resolved escalation."

The remaining 9,994 tickets are randomized (with a fixed seed for
reproducibility). Roughly 10% of escalated tickets get re-escalated a
second time, and a small share (~2.5%) of resolved escalations log a
duplicate `escalation_resolved` note shortly after the first, simulating
the kind of messy, real-world contact-center data-entry issues that show
up in practice.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
TOTAL_TICKETS = 10_000
CURATED_TICKET_IDS = {1, 2, 3, 4, 5, 6}

SLO_HOURS = 48  # SLO for resolving an escalation once it's raised
AT_RISK_THRESHOLD_HOURS = 32  # unresolved escalations older than this are "at risk"

ESCALATION_PROBABILITY = 0.20  # fraction of tickets that get escalated at all
MULTI_ESCALATION_PROBABILITY = 0.10  # fraction of escalated tickets that get a second escalation
RESOLVED_ESCALATION_PROBABILITY = 0.55  # fraction of escalations that eventually get resolved
RESOLVED_WITHIN_SLO_PROBABILITY = 0.80  # of resolved escalations, fraction resolved within SLO
UNRESOLVED_WITHIN_SLO_PROBABILITY = 0.90  # of unresolved escalations, fraction still within SLO (i.e. recent)
DUPLICATE_RESOLUTION_PROBABILITY = 0.025  # fraction of resolutions that log a duplicate note shortly after

PRODUCTS = ["Billing", "Mobile App", "Website", "API", "Hardware"]
REP_COUNT = 20  # simulates a team-based contact center (no single rep owns a ticket)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

REPS = [fake.name() for _ in range(REP_COUNT)]


def days_ago(n: int) -> datetime:
    return datetime.now() - timedelta(days=n)


def hours_ago(n: float) -> datetime:
    return datetime.now() - timedelta(hours=n)


def build_curated_tickets():
    """Hand-crafted tickets/notes that exercise the 72-hour escalation-SLO edge cases."""
    reps = REPS[:6]  # ticket N's initial rep is reps[N-1]

    tickets = [
        {
            "ticket_id": 1,
            "customer_name": fake.name(),
            "product": "Billing",
            "opened_at": days_ago(10),
            "status": "open",
            "initial_rep": reps[0],
        },
        {
            "ticket_id": 2,
            "customer_name": fake.name(),
            "product": "Mobile App",
            "opened_at": days_ago(20),
            "status": "resolved",
            "initial_rep": reps[1],
        },
        {
            "ticket_id": 3,
            "customer_name": fake.name(),
            "product": "Website",
            "opened_at": days_ago(15),
            "status": "open",
            "initial_rep": reps[2],
        },
        {
            "ticket_id": 4,
            "customer_name": fake.name(),
            "product": "API",
            "opened_at": days_ago(7),
            "status": "resolved",
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
        {
            "ticket_id": 6,
            "customer_name": fake.name(),
            "product": "Billing",
            "opened_at": days_ago(25),
            "status": "open",
            "initial_rep": reps[5],
        },
    ]

    notes = [
        # Ticket 1: escalated 40 hours ago, still unresolved.
        # 40h is past the 32h at-risk threshold but inside the 48h SLO -> AT RISK.
        {"ticket_id": 1, "rep_name": reps[0], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(10)},
        {"ticket_id": 1, "rep_name": REPS[6], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(40)},

        # Ticket 2: escalated 200 hours ago, resolved 100 hours ago.
        # Resolution took 100h, which is outside the 48h SLO -> RESOLVED LATE.
        {"ticket_id": 2, "rep_name": reps[1], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(19)},
        {"ticket_id": 2, "rep_name": REPS[7], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(200)},
        {"ticket_id": 2, "rep_name": REPS[7], "note_type": "escalation_resolved", "note_text": "Escalation addressed, fix deployed.", "created_at": hours_ago(100)},
        {"ticket_id": 2, "rep_name": reps[1], "note_type": "resolution", "note_text": "Issue resolved.", "created_at": hours_ago(90)},

        # Ticket 3: escalated 120 hours ago, still unresolved.
        # 120h is past the 48h SLO -> BREACHED, STILL UNRESOLVED.
        {"ticket_id": 3, "rep_name": reps[2], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(14)},
        {"ticket_id": 3, "rep_name": REPS[8], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(120)},

        # Ticket 4: escalated 50 hours ago, resolved 20 hours ago.
        # Resolution took 30h, well within the 48h SLO -> WITHIN SLO (control case).
        {"ticket_id": 4, "rep_name": reps[3], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(7)},
        {"ticket_id": 4, "rep_name": REPS[9], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(50)},
        {"ticket_id": 4, "rep_name": REPS[9], "note_type": "escalation_resolved", "note_text": "Escalation addressed.", "created_at": hours_ago(20)},
        {"ticket_id": 4, "rep_name": reps[3], "note_type": "resolution", "note_text": "Issue resolved.", "created_at": hours_ago(15)},

        # Ticket 5: no escalation notes at all (control case).
        {"ticket_id": 5, "rep_name": reps[4], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(29)},
        {"ticket_id": 5, "rep_name": REPS[11], "note_type": "follow_up", "note_text": "Checked in with customer.", "created_at": days_ago(20)},
        {"ticket_id": 5, "rep_name": REPS[11], "note_type": "resolution", "note_text": "Issue resolved.", "created_at": days_ago(5)},

        # Ticket 6: two escalations. The first was resolved well within SLO (healthy);
        # the second is still open at 40 hours -> AT RISK. Proves each escalation must
        # be paired with its own resolution, not just "has this ticket ever recovered."
        {"ticket_id": 6, "rep_name": reps[5], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(24)},
        {"ticket_id": 6, "rep_name": REPS[12], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(200)},
        {"ticket_id": 6, "rep_name": REPS[12], "note_type": "escalation_resolved", "note_text": "First escalation addressed.", "created_at": hours_ago(160)},
        {"ticket_id": 6, "rep_name": REPS[13], "note_type": "escalation", "note_text": "Escalated again to tier 3.", "created_at": hours_ago(40)},
    ]

    return tickets, notes


def generate_escalation_episode(not_before: datetime, now: datetime):
    """Builds one escalation note plus its resolution note(s), if any.

    The escalation is placed no earlier than `not_before` so episodes can be
    chained (e.g. a ticket's second escalation starts after its first ends).
    Returns (notes, episode_end) so the caller can chain a follow-on episode.
    """
    resolved = random.random() < RESOLVED_ESCALATION_PROBABILITY
    resolved_at = None

    if resolved:
        within_slo = random.random() < RESOLVED_WITHIN_SLO_PROBABILITY
        resolution_hours = (
            random.uniform(1, SLO_HOURS - 1) if within_slo
            else random.uniform(SLO_HOURS + 1, SLO_HOURS * 4)
        )
        available_hours = (now - not_before).total_seconds() / 3600
        if available_hours > resolution_hours + 1:
            escalation_at = not_before + timedelta(hours=random.uniform(0, available_hours - resolution_hours))
            resolved_at = escalation_at + timedelta(hours=resolution_hours)
        else:
            resolved = False  # not enough runway left before "now" to resolve in time

    if not resolved:
        within_slo = random.random() < UNRESOLVED_WITHIN_SLO_PROBABILITY
        hours_ago_value = (
            random.uniform(0, SLO_HOURS - 1) if within_slo
            else random.uniform(SLO_HOURS + 1, SLO_HOURS * 6)
        )
        escalation_at = max(not_before, now - timedelta(hours=hours_ago_value))

    notes = [
        {
            "note_type": "escalation",
            "note_text": fake.sentence(nb_words=8),
            "created_at": escalation_at,
            "rep_name": random.choice(REPS),
        }
    ]

    if resolved_at is not None:
        notes.append(
            {
                "note_type": "escalation_resolved",
                "note_text": fake.sentence(nb_words=8),
                "created_at": resolved_at,
                "rep_name": random.choice(REPS),
            }
        )
        # A small share of escalations pick up a duplicate resolution note
        # logged shortly after -- messy, but realistic contact-center data.
        if random.random() < DUPLICATE_RESOLUTION_PROBABILITY:
            duplicate_at = resolved_at + timedelta(hours=random.uniform(0.1, 12))
            if duplicate_at <= now:
                notes.append(
                    {
                        "note_type": "escalation_resolved",
                        "note_text": fake.sentence(nb_words=8),
                        "created_at": duplicate_at,
                        "rep_name": random.choice(REPS),
                    }
                )

    return notes, notes[-1]["created_at"]


def build_random_tickets(start_id: int, count: int):
    """Builds tickets whose notes follow a coherent lifecycle (general ->
    optional escalation -> optional follow-ups -> optional resolution), with
    `status` derived from what actually happened rather than picked at random.
    """
    tickets = []
    notes = []

    for ticket_id in range(start_id, start_id + count):
        # Includes recently-opened tickets so recent-escalation scenarios
        # (e.g. "escalated in the last 7 days") have rows to match against.
        opened_at = fake.date_time_between(start_date="-2y", end_date="-1d")
        initial_rep = random.choice(REPS)
        age_days = (datetime.now() - opened_at).days
        now = datetime.now()

        ticket_notes = [
            {
                "note_type": "general",
                "note_text": fake.sentence(nb_words=8),
                "created_at": opened_at + timedelta(hours=random.uniform(0, 4)),
                "rep_name": initial_rep,
            }
        ]

        if random.random() < ESCALATION_PROBABILITY:  # some tickets get escalated
            episode_notes, episode_end = generate_escalation_episode(ticket_notes[-1]["created_at"], now)
            ticket_notes.extend(episode_notes)

            if random.random() < MULTI_ESCALATION_PROBABILITY:  # ticket gets re-escalated
                episode2_notes, _ = generate_escalation_episode(episode_end, now)
                ticket_notes.extend(episode2_notes)

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
        start_id=len(CURATED_TICKET_IDS) + 1, count=TOTAL_TICKETS - len(CURATED_TICKET_IDS)
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
