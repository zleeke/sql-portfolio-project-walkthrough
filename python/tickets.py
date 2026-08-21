"""Generator for `tickets` + `ticket_notes`, applying the SLO edge-case
distributions and the underperforming/overperforming segment story.

Each ticket is simulated as a single conversation timeline owned by one
agent (its `initial_employee_id`), moving through general_information /
follow_up / escalation / escalation_resolved / resolved notes in an order
that always respects the business rules in project_context.md:
  - the first note is only ever general_information or escalation
  - only one escalation per ticket may be open at a time
  - `resolved` can only be logged when no escalation is currently open
  - the SLO clock runs from `escalation` to its matching `escalation_resolved`
"""

import random
from datetime import datetime, timedelta

import config

# WINDOW_END_DT is the exclusive upper bound (end of WINDOW_END's day), so
# any note timestamped anywhere on WINDOW_END itself is still in-window.
WINDOW_START_DT = datetime.combine(config.WINDOW_START, datetime.min.time())
WINDOW_END_DT = datetime.combine(config.WINDOW_END, datetime.min.time()) + timedelta(days=1)


def _random_datetime_in_window():
    span_seconds = int((WINDOW_END_DT - WINDOW_START_DT).total_seconds())
    return WINDOW_START_DT + timedelta(seconds=random.randint(0, span_seconds))


def _random_gap():
    # Random gap between casual notes / before a closing note, in hours.
    lo, hi = config.GENERAL_GAP_HOURS_RANGE
    return timedelta(hours=random.uniform(lo, hi))


def _sample_bucket(line, director_name, underperforming_director, overperforming_director):
    # Collect every tuned weight profile that applies to this escalation
    # (product line and/or the owning agent's director). If both an
    # underperforming and overperforming signal apply (rare), average them
    # instead of picking one arbitrarily.
    profiles = []
    if line == config.UNDERPERFORMING_LINE or director_name == underperforming_director:
        profiles.append(config.UNDERPERFORM_WEIGHTS)
    if line == config.OVERPERFORMING_LINE or director_name == overperforming_director:
        profiles.append(config.OVERPERFORM_WEIGHTS)

    if not profiles:
        weights = config.BASE_WEIGHTS
    else:
        keys = config.BASE_WEIGHTS.keys()
        weights = {k: sum(p[k] for p in profiles) / len(profiles) for k in keys}

    buckets = list(weights.keys())
    probs = list(weights.values())
    return random.choices(buckets, weights=probs, k=1)[0]


def _sample_offset_hours(bucket):
    # Turn a resolution-time bucket (e.g. "just_under") into an actual
    # elapsed-hours value for the escalation -> escalation_resolved gap.
    lo, hi = config.BUCKET_HOUR_RANGES[bucket]
    return random.uniform(lo, hi)


def _simulate_ticket_notes(product, director_name, underperforming_director, overperforming_director):
    """Build the chronological list of (category, timestamp) notes for one
    ticket, honoring the SLO edge-case distribution. Returns (notes, status).
    """
    notes = []
    current_time = _random_datetime_in_window()

    # Decide up front whether this ticket will ever escalate, and if so,
    # whether the escalation is the very first note (vs. general chatter
    # first, escalation appended later).
    has_escalation = random.random() < config.TICKET_ESCALATION_PROB
    first_is_escalation = has_escalation and random.random() < config.FIRST_NOTE_IS_ESCALATION_PROB

    first_category = "escalation" if first_is_escalation else "general_information"
    notes.append((first_category, current_time))
    open_escalation = first_is_escalation

    # If this ticket should escalate but didn't open with one, add a couple
    # of casual notes first, then the escalation (if there's still room in
    # the window).
    if has_escalation and not first_is_escalation:
        for _ in range(random.randint(0, 1)):
            current_time += _random_gap()
            if current_time > WINDOW_END_DT:
                break
            notes.append(("follow_up", current_time))
        else:
            current_time += _random_gap()
            if current_time <= WINDOW_END_DT:
                notes.append(("escalation", current_time))
                open_escalation = True

    forced_open = False
    escalation_cycles = 0

    # Each pass through this loop is one escalation cycle: sample how it
    # resolves (or doesn't), and optionally start a second cycle afterward.
    while open_escalation:
        bucket = _sample_bucket(
            product["line"], director_name, underperforming_director, overperforming_director
        )
        if bucket == "unresolved":
            # Deliberately never resolved -- ticket stays open indefinitely.
            forced_open = True
            break

        escalation_time = current_time
        resolution_time = escalation_time + timedelta(hours=_sample_offset_hours(bucket))
        if resolution_time > WINDOW_END_DT:
            # Would resolve after the data window ends -- from the anchor
            # date's point of view this escalation is still open.
            forced_open = True
            break

        # A few follow_up notes can land between the escalation and its
        # resolution without affecting the SLO clock itself.
        for _ in range(random.randint(0, 2)):
            followup_time = escalation_time + (resolution_time - escalation_time) * random.uniform(0.1, 0.9)
            notes.append(("follow_up", followup_time))

        notes.append(("escalation_resolved", resolution_time))
        current_time = resolution_time
        open_escalation = False
        escalation_cycles += 1

        # Only the first cycle can chain into a second escalation, keeping
        # multi-escalation tickets rare rather than potentially unbounded.
        if escalation_cycles == 1 and random.random() < config.MULTI_ESCALATION_PROB:
            current_time += _random_gap()
            if current_time > WINDOW_END_DT:
                break
            notes.append(("escalation", current_time))
            open_escalation = True

    closed = False
    if not forced_open:
        # No escalation is currently open, so the ticket is eligible to
        # collect a few more casual notes and/or get closed out.
        for _ in range(random.randint(0, 2)):
            current_time += _random_gap()
            if current_time > WINDOW_END_DT:
                break
            notes.append(("follow_up", current_time))

        if current_time <= WINDOW_END_DT and random.random() < config.CLOSE_PROB:
            current_time += _random_gap()
            if current_time <= WINDOW_END_DT:
                notes.append(("resolved", current_time))
                closed = True

    notes.sort(key=lambda note: note[1])
    status = "closed" if closed else "open"
    return notes, status


def generate_tickets_and_notes(
    customers, products, employees, underperforming_director, overperforming_director
):
    tickets = []
    ticket_notes = []
    ticket_note_id = 1

    # Randomize the actual ticket count around config.NUM_TICKETS so the
    # row count isn't a suspiciously exact round number.
    variance = int(config.NUM_TICKETS * config.NUM_TICKETS_VARIANCE)
    num_tickets = random.randint(config.NUM_TICKETS - variance, config.NUM_TICKETS + variance)

    for ticket_id in range(1, num_tickets + 1):
        customer = random.choice(customers)
        product = random.choice(products)
        employee = random.choice(employees)

        notes, status = _simulate_ticket_notes(
            product, employee["director_name"], underperforming_director, overperforming_director
        )

        tickets.append(
            {
                "ticket_id": ticket_id,
                "customer_id": customer["customer_id"],
                "product_id": product["product_id"],
                "initial_employee_id": employee["employee_id"],
                "status": status,
            }
        )

        for category, created_tstmp in notes:
            ticket_notes.append(
                {
                    "ticket_note_id": ticket_note_id,
                    "ticket_id": ticket_id,
                    "employee_id": employee["employee_id"],
                    "category": category,
                    "created_tstmp": created_tstmp,
                }
            )
            ticket_note_id += 1

    return tickets, ticket_notes
