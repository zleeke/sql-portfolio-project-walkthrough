"""Shared constants for the synthetic data generator.

Tune these values to change data volume, date range, or the SLO edge-case
distributions without touching the generation logic.
"""

from datetime import date

# --- Reproducibility -------------------------------------------------------
# Not required for this project, but fixing a seed keeps generator runs
# comparable while iterating. Set to None for a different dataset each run.
SEED = 42

# --- Scale -------------------------------------------------------------
NUM_CUSTOMERS = 8_000
# Target ticket count -- the actual generated count is randomized within
# NUM_TICKETS_VARIANCE of this target so the row count isn't a suspiciously
# round number.
NUM_TICKETS = 100_000
NUM_TICKETS_VARIANCE = 0.03

# --- Date window ---------------------------------------------------------
# WINDOW_END doubles as the "as of" reference/anchor date used by the SLO
# logic below (e.g. an escalation isn't "unresolved" until the window ends
# without a matching escalation_resolved note).
WINDOW_START = date(2025, 1, 1)
WINDOW_END = date(2025, 6, 30)

# --- Products ------------------------------------------------------------
PRODUCT_LINES = {
    "Home & Kitchen": ["Small Appliances", "Cookware", "Furniture"],
    "Tech & Electronics": ["Audio", "Smart Home", "Computer Accessories"],
    "Outdoor & Garden": ["Grills & Smokers", "Patio Furniture", "Power Tools"],
    "Personal Care": ["Skincare", "Haircare", "Wellness Devices"],
}
PRODUCTS_PER_CATEGORY = 6

# Segment-level story: one product line is deliberately tuned to underperform
# on SLO, another to overperform (see README once queries surface the story).
UNDERPERFORMING_LINE = "Tech & Electronics"
OVERPERFORMING_LINE = "Personal Care"

# --- Employee hierarchy ---------------------------------------------------
NUM_DIRECTORS = 4
MANAGERS_PER_DIRECTOR = 3
SUPERVISORS_PER_MANAGER = 3
AGENTS_PER_SUPERVISOR_RANGE = (8, 14)

# Indexes into the generated directors list (order is randomized by Faker,
# so the actual names are resolved and logged at generation time).
UNDERPERFORMING_DIRECTOR_INDEX = 0
OVERPERFORMING_DIRECTOR_INDEX = 1

# --- Escalation behavior ---------------------------------------------------
# Share of tickets that get at least one escalation over their lifetime.
TICKET_ESCALATION_PROB = 0.30
# Of escalated tickets, chance the escalation is the very first note logged
# (vs. general_information/follow_up first, escalation added later).
FIRST_NOTE_IS_ESCALATION_PROB = 0.40
# Chance an already-resolved escalation is followed by a second cycle.
MULTI_ESCALATION_PROB = 0.06
# Chance a ticket with no unresolved escalation gets closed with a
# `resolved` note before the window ends.
CLOSE_PROB = 0.75

# Gap (in hours) between casual notes (general_information/follow_up) and
# between the last note and a closing `resolved` note.
GENERAL_GAP_HOURS_RANGE = (1, 96)

# SLO resolution-time buckets, in hours elapsed between `escalation` and
# `escalation_resolved`. "unresolved" means no escalation_resolved note is
# ever logged for that escalation.
BUCKET_HOUR_RANGES = {
    "comfortable": (2, 24),
    "just_under": (40, 47.9),
    "just_over": (48.1, 72),
}

BASE_WEIGHTS = {
    "comfortable": 0.55,
    "just_under": 0.20,
    "just_over": 0.15,
    "unresolved": 0.10,
}
UNDERPERFORM_WEIGHTS = {
    "comfortable": 0.20,
    "just_under": 0.15,
    "just_over": 0.35,
    "unresolved": 0.30,
}
OVERPERFORM_WEIGHTS = {
    "comfortable": 0.78,
    "just_under": 0.14,
    "just_over": 0.06,
    "unresolved": 0.02,
}

# --- Output ----------------------------------------------------------------
OUTPUT_DIR = "data"
