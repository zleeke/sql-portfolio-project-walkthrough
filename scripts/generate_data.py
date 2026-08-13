"""
Generates synthetic support-desk data for the QUALIFY demo project.

Produces four CSVs:
  - data/employee.csv      (org hierarchy: reps, first-line leaders, second-line leaders)
  - data/customer.csv      (customer dimension; repeat customers allowed)
  - data/tickets.csv       (~103,742 tickets -- close to 100K, deliberately not round)
  - data/ticket_notes.csv  (a variable number of notes per ticket)

Employee hierarchy is flattened onto each employee row rather than a single
self-referencing manager_id: reps have both `first_line_leader_id` and
`second_line_leader_id` set; first-line leaders have only
`second_line_leader_id` set; second-line leaders have neither. Only reps
author ticket notes -- leaders exist purely for org-chart realism.

Ticket `status` is derived entirely from note history, not picked at random:
  - 'new'     : the ticket has exactly one note (its initial note) so far.
  - 'closed'  : if the ticket has any escalation(s), only once every
                escalation has a matching escalation_resolved note. If the
                ticket never escalated, an age-based probability decides
                closed vs. pending (older tickets are more likely closed),
                since there's no dedicated "resolution" note type.
  - 'pending' : everything else.

The business rule being simulated for escalations: a 48-hour SLO
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

The remaining tickets are randomized (with a fixed seed for
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
TOTAL_TICKETS = 103_742  # ~100K, but deliberately not a round number
CURATED_TICKET_IDS = {1, 2, 3, 4, 5, 6}
CURATED_CUSTOMER_IDS = {1, 2, 3, 4, 5, 6}

CUSTOMER_COUNT = 41_000  # smaller than TOTAL_TICKETS so repeat customers occur

SLL_COUNT = 3  # second-line leaders
FLL_COUNT = 15  # first-line leaders
REP_COUNT = 100  # individual-contributor reps who actually work tickets

SLO_HOURS = 48  # SLO for resolving an escalation once it's raised
AT_RISK_THRESHOLD_HOURS = 32  # unresolved escalations older than this are "at risk"

ESCALATION_PROBABILITY = 0.20  # fraction of tickets that get escalated at all
MULTI_ESCALATION_PROBABILITY = 0.10  # fraction of escalated tickets that get a second escalation
RESOLVED_ESCALATION_PROBABILITY = 0.55  # fraction of escalations that eventually get resolved
RESOLVED_WITHIN_SLO_PROBABILITY = 0.80  # of resolved escalations, fraction resolved within SLO
UNRESOLVED_WITHIN_SLO_PROBABILITY = 0.90  # of unresolved escalations, fraction still within SLO (i.e. recent)
DUPLICATE_RESOLUTION_PROBABILITY = 0.025  # fraction of resolutions that log a duplicate note shortly after

PRODUCTS = ["Billing", "Mobile App", "Website", "API", "Hardware"]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)


def days_ago(n: int) -> datetime:
    return datetime.now() - timedelta(days=n)


def hours_ago(n: float) -> datetime:
    return datetime.now() - timedelta(hours=n)


def build_employees():
    """Builds the org hierarchy: second-line leaders -> first-line leaders -> reps.

    Returns (employees, rep_ids) -- only rep_ids are used elsewhere to author
    ticket notes, since leaders don't work tickets directly.
    """
    employees = []
    next_id = 1

    second_line_leader_ids = []
    for _ in range(SLL_COUNT):
        employees.append(
            {
                "employee_id": next_id,
                "employee_name": fake.name(),
                "role": "second_line_leader",
                "first_line_leader_id": None,
                "second_line_leader_id": None,
            }
        )
        second_line_leader_ids.append(next_id)
        next_id += 1

    first_line_leader_ids = []
    first_line_leader_to_sll = {}
    for i in range(FLL_COUNT):
        sll_id = second_line_leader_ids[i % SLL_COUNT]
        employees.append(
            {
                "employee_id": next_id,
                "employee_name": fake.name(),
                "role": "first_line_leader",
                "first_line_leader_id": None,
                "second_line_leader_id": sll_id,
            }
        )
        first_line_leader_to_sll[next_id] = sll_id
        first_line_leader_ids.append(next_id)
        next_id += 1

    rep_ids = []
    for i in range(REP_COUNT):
        fll_id = first_line_leader_ids[i % FLL_COUNT]
        employees.append(
            {
                "employee_id": next_id,
                "employee_name": fake.name(),
                "role": "rep",
                "first_line_leader_id": fll_id,
                "second_line_leader_id": first_line_leader_to_sll[fll_id],
            }
        )
        rep_ids.append(next_id)
        next_id += 1

    return employees, rep_ids


def build_curated_customers():
    """Six hand-crafted customers, one per curated ticket."""
    customers = []
    for customer_id in sorted(CURATED_CUSTOMER_IDS):
        customers.append(
            {
                "customer_id": customer_id,
                "customer_name": fake.name(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "email": fake.email(),
                "customer_since": days_ago(400).date(),  # safely before any curated ticket
            }
        )
    return customers


def build_customers(count: int, start_id: int):
    """Builds a customer dimension smaller than the ticket count on purpose,
    so repeat customers show up when tickets are assigned to customer_ids.
    """
    customers = []
    for customer_id in range(start_id, start_id + count):
        customers.append(
            {
                "customer_id": customer_id,
                "customer_name": fake.name(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "email": fake.email(),
                "customer_since": fake.date_between(start_date="-8y", end_date="-60d"),
            }
        )
    return customers


def build_curated_tickets(rep_ids):
    """Hand-crafted tickets/notes that exercise the 48-hour escalation-SLO edge cases."""
    reps = rep_ids[:6]  # ticket N's initial rep is reps[N-1]

    tickets = [
        {
            "ticket_id": 1,
            "customer_id": 1,
            "product": "Billing",
            "opened_at": days_ago(10),
            "status": "pending",
            "initial_rep_employee_id": reps[0],
        },
        {
            "ticket_id": 2,
            "customer_id": 2,
            "product": "Mobile App",
            "opened_at": days_ago(20),
            "status": "closed",
            "initial_rep_employee_id": reps[1],
        },
        {
            "ticket_id": 3,
            "customer_id": 3,
            "product": "Website",
            "opened_at": days_ago(15),
            "status": "pending",
            "initial_rep_employee_id": reps[2],
        },
        {
            "ticket_id": 4,
            "customer_id": 4,
            "product": "API",
            "opened_at": days_ago(7),
            "status": "closed",
            "initial_rep_employee_id": reps[3],
        },
        {
            "ticket_id": 5,
            "customer_id": 5,
            "product": "Hardware",
            "opened_at": days_ago(30),
            "status": "closed",
            "initial_rep_employee_id": reps[4],
        },
        {
            "ticket_id": 6,
            "customer_id": 6,
            "product": "Billing",
            "opened_at": days_ago(25),
            "status": "pending",
            "initial_rep_employee_id": reps[5],
        },
    ]

    notes = [
        # Ticket 1: escalated 40 hours ago, still unresolved.
        # 40h is past the 32h at-risk threshold but inside the 48h SLO -> AT RISK.
        {"ticket_id": 1, "employee_id": reps[0], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(10)},
        {"ticket_id": 1, "employee_id": rep_ids[6], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(40)},

        # Ticket 2: escalated 200 hours ago, resolved 100 hours ago.
        # Resolution took 100h, which is outside the 48h SLO -> RESOLVED LATE.
        {"ticket_id": 2, "employee_id": reps[1], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(19)},
        {"ticket_id": 2, "employee_id": rep_ids[7], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(200)},
        {"ticket_id": 2, "employee_id": rep_ids[7], "note_type": "escalation_resolved", "note_text": "Escalation addressed, fix deployed.", "created_at": hours_ago(100)},

        # Ticket 3: escalated 120 hours ago, still unresolved.
        # 120h is past the 48h SLO -> BREACHED, STILL UNRESOLVED.
        {"ticket_id": 3, "employee_id": reps[2], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(14)},
        {"ticket_id": 3, "employee_id": rep_ids[8], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(120)},

        # Ticket 4: escalated 50 hours ago, resolved 20 hours ago.
        # Resolution took 30h, well within the 48h SLO -> WITHIN SLO (control case).
        {"ticket_id": 4, "employee_id": reps[3], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(7)},
        {"ticket_id": 4, "employee_id": rep_ids[9], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(50)},
        {"ticket_id": 4, "employee_id": rep_ids[9], "note_type": "escalation_resolved", "note_text": "Escalation addressed.", "created_at": hours_ago(20)},

        # Ticket 5: no escalation notes at all (control case).
        {"ticket_id": 5, "employee_id": reps[4], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(29)},
        {"ticket_id": 5, "employee_id": rep_ids[11], "note_type": "follow_up", "note_text": "Checked in with customer.", "created_at": days_ago(20)},

        # Ticket 6: two escalations. The first was resolved well within SLO (healthy);
        # the second is still open at 40 hours -> AT RISK. Proves each escalation must
        # be paired with its own resolution, not just "has this ticket ever recovered."
        {"ticket_id": 6, "employee_id": reps[5], "note_type": "general", "note_text": "Customer reported issue.", "created_at": days_ago(24)},
        {"ticket_id": 6, "employee_id": rep_ids[12], "note_type": "escalation", "note_text": "Escalated to tier 2.", "created_at": hours_ago(200)},
        {"ticket_id": 6, "employee_id": rep_ids[12], "note_type": "escalation_resolved", "note_text": "First escalation addressed.", "created_at": hours_ago(160)},
        {"ticket_id": 6, "employee_id": rep_ids[13], "note_type": "escalation", "note_text": "Escalated again to tier 3.", "created_at": hours_ago(40)},
    ]

    return tickets, notes


def generate_escalation_episode(not_before: datetime, now: datetime, rep_ids: list):
    """Builds one escalation note plus its resolution note(s), if any.

    The escalation is placed no earlier than `not_before` so episodes can be
    chained (e.g. a ticket's second escalation starts after its first ends).
    Returns (notes, episode_end, resolved) so the caller can chain a
    follow-on episode and track whether this episode was ever closed out.
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
            "employee_id": random.choice(rep_ids),
        }
    ]

    if resolved_at is not None:
        notes.append(
            {
                "note_type": "escalation_resolved",
                "note_text": fake.sentence(nb_words=8),
                "created_at": resolved_at,
                "employee_id": random.choice(rep_ids),
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
                        "employee_id": random.choice(rep_ids),
                    }
                )

    return notes, notes[-1]["created_at"], resolved


def build_random_tickets(start_id: int, count: int, rep_ids: list, customer_ids: list, customer_since_by_id: dict):
    """Builds tickets whose notes follow a coherent lifecycle (general ->
    optional escalation episode(s) -> optional follow-ups). `status` is
    derived entirely from what happened (see module docstring).
    """
    tickets = []
    notes = []
    now = datetime.now()
    two_years_ago = now - timedelta(days=730)
    upper_bound = now - timedelta(days=1)

    for ticket_id in range(start_id, start_id + count):
        customer_id = random.choice(customer_ids)
        customer_since = customer_since_by_id[customer_id]

        # Tickets can't predate the customer's tenure, but still lean on the
        # same "mostly recent" window used before for realistic escalation timing.
        lower_bound = max(customer_since, two_years_ago)
        if lower_bound >= upper_bound:
            lower_bound = upper_bound - timedelta(days=1)
        opened_at = fake.date_time_between(start_date=lower_bound, end_date=upper_bound)

        initial_rep = random.choice(rep_ids)
        age_days = (now - opened_at).days

        ticket_notes = [
            {
                "note_type": "general",
                "note_text": fake.sentence(nb_words=8),
                "created_at": opened_at + timedelta(hours=random.uniform(0, 4)),
                "employee_id": initial_rep,
            }
        ]

        has_escalation = False
        all_escalations_resolved = True

        if random.random() < ESCALATION_PROBABILITY:  # some tickets get escalated
            has_escalation = True
            episode_notes, episode_end, resolved = generate_escalation_episode(ticket_notes[-1]["created_at"], now, rep_ids)
            ticket_notes.extend(episode_notes)
            all_escalations_resolved = resolved

            if random.random() < MULTI_ESCALATION_PROBABILITY:  # ticket gets re-escalated
                episode2_notes, _, resolved2 = generate_escalation_episode(episode_end, now, rep_ids)
                ticket_notes.extend(episode2_notes)
                all_escalations_resolved = all_escalations_resolved and resolved2

        num_follow_ups = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]
        for _ in range(num_follow_ups):
            ticket_notes.append(
                {
                    "note_type": "follow_up",
                    "note_text": fake.sentence(nb_words=8),
                    "created_at": ticket_notes[-1]["created_at"] + timedelta(days=random.uniform(1, 7)),
                    "employee_id": random.choice(rep_ids),
                }
            )

        for note in ticket_notes:
            if note["created_at"] > now:
                note["created_at"] = now

        if len(ticket_notes) == 1:
            status = "new"
        elif has_escalation:
            status = "closed" if all_escalations_resolved else "pending"
        else:
            # No escalation and no dedicated "resolution" note type anymore --
            # older tickets are more likely to have quietly wrapped up.
            resolve_probability = min(0.9, 0.3 + (age_days / 365) * 0.5)
            status = "closed" if random.random() < resolve_probability else "pending"

        tickets.append(
            {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "product": random.choice(PRODUCTS),
                "opened_at": opened_at,
                "status": status,
                "initial_rep_employee_id": initial_rep,
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
    employees, rep_ids = build_employees()

    curated_customers = build_curated_customers()
    random_customers = build_customers(
        count=CUSTOMER_COUNT - len(CURATED_CUSTOMER_IDS),
        start_id=max(CURATED_CUSTOMER_IDS) + 1,
    )
    all_customers = curated_customers + random_customers
    random_customer_ids = [c["customer_id"] for c in random_customers]
    customer_since_by_id = {
        c["customer_id"]: datetime.combine(c["customer_since"], datetime.min.time())
        for c in all_customers
    }

    curated_tickets, curated_notes = build_curated_tickets(rep_ids)
    random_tickets, random_notes = build_random_tickets(
        start_id=len(CURATED_TICKET_IDS) + 1,
        count=TOTAL_TICKETS - len(CURATED_TICKET_IDS),
        rep_ids=rep_ids,
        customer_ids=random_customer_ids,
        customer_since_by_id=customer_since_by_id,
    )

    all_tickets = curated_tickets + random_tickets

    # Assign sequential note IDs after all notes are collected.
    all_notes = curated_notes + random_notes
    for note_id, note in enumerate(all_notes, start=1):
        note["note_id"] = note_id

    write_csv(
        DATA_DIR / "employee.csv",
        employees,
        fieldnames=["employee_id", "employee_name", "role", "first_line_leader_id", "second_line_leader_id"],
    )
    write_csv(
        DATA_DIR / "customer.csv",
        all_customers,
        fieldnames=["customer_id", "customer_name", "city", "state", "email", "customer_since"],
    )
    write_csv(
        DATA_DIR / "tickets.csv",
        all_tickets,
        fieldnames=["ticket_id", "customer_id", "product", "opened_at", "status", "initial_rep_employee_id"],
    )
    write_csv(
        DATA_DIR / "ticket_notes.csv",
        all_notes,
        fieldnames=["note_id", "ticket_id", "employee_id", "note_type", "note_text", "created_at"],
    )

    print(f"Wrote {len(employees):,} employees to {DATA_DIR / 'employee.csv'}")
    print(f"Wrote {len(all_customers):,} customers to {DATA_DIR / 'customer.csv'}")
    print(f"Wrote {len(all_tickets):,} tickets to {DATA_DIR / 'tickets.csv'}")
    print(f"Wrote {len(all_notes):,} ticket notes to {DATA_DIR / 'ticket_notes.csv'}")


if __name__ == "__main__":
    main()
