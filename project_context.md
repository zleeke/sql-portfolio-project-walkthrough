# About Me
- I'm a data analyst with experience in Property & Casualty Insurance.
- I'm working on a SQL portfolio to demonstrate my skills in SQL
- In this project, I want to show how useful the qualify statement can be in SQL.

# Tools that we're using
- VS Code as code editor
- DuckDB as SQL engine
- DBCode extension in VS Code to interact with DuckDB Database
- Faker Library in Python for synthetic data creation
- I'm working on MacBook
- I'm using GitHub to version my project and have a public repo so others can view the code I've written

# My objectives with this project
- I want to use this project to demonstrate my ability to write complex SQL queries to answer realistic questions posed by a business area.
- As you assist me with this project, here are some important guardrails you should follow:
    - Don't write the SQL queries for me. I want to do that to demonstrate my skill.
    - I do you need your assistance with building the framework for the project (folder structure, readme file, python code to generate synthetic data for the database, and database creation.)
    - I want a lot of opportunities throughout this project to learn something new.
    - Always add comments to any Python scripts you write or edit, explaining what each part of the code is doing and why, so I can learn from it.
- At the end of this project I want to have code that I can share with prospective employers so they can understand my SQL capabilities.
- Additionally, I do want to create an HTML dashboard as well that visualizes the data in my database and host it on GitHub.
- I will be documenting this project as a series of YouTube videos shared on LinkedIn, walking through my design decisions and SQL techniques. Teaching the material reinforces my own mastery of it, and it doubles as a way to showcase my technical communication and SQL skills to potential employers.

# Business Problem
- The business: A contact center that handles support tickets from customers about products that they have purchased from us. When a customer calls in for assistance with a product, an initial ticket is opened and a ticket note is recorded for the interaction. If the customer calls in to follow-up on the ticket, additional notes are entered as well. We are most focused on analyzing what happens when the customer calls in to complain about a product. We'll refer to these as escalations throughout the project.
- Our business as a service level objective (SLO) of resolving 80% of escalations received within 48 hours. The queries we will be writing will focus on how well the company is achieving their service level objective.
- Here are some qustions that are business needs help answering?
    - How well are we doing at achieving our service level objective?
    - What percentage of our unresolved escalations are in SLO, but at risk of exceeding SLO and remaining unresolved?
    - What percentage of our resolved escalations were resolved within SLO?
    - What percentage of our resolved escalations were resolved outside of SLO?

# Data Model

## customers
- `customer_id` (PK)
- `customer_name`
- `email`
- `phone_number`
- `city`
- `state`
- `signup_date`

## products
- `product_id` (PK)
- `product_name`
- `line`
- `category`

## employees
- `employee_id` (PK)
- `employee_name`
- `hire_date`
- `supervisor_name` (employee's 1st-line leader)
- `manager_name` (employee's 2nd-line leader)
- `director_name` (employee's 3rd-line leader)

## tickets
- `ticket_id` (PK)
- `customer_id` (FK → customers)
- `product_id` (FK → products)
- `initial_employee_id` (FK → employees) — the employee who opened the ticket
- `status` (`open`/`closed`, as of the reference date)

## ticket_notes
- `ticket_note_id` (PK)
- `ticket_id` (FK → tickets)
- `employee_id` (FK → employees) — the employee who logged this note
- `category`: one of `general_information`, `follow_up`, `escalation`, `escalation_resolved`, `resolved` (see Escalation & Resolution Rules)
- `created_tstmp` — timestamp the note was entered, in UTC

# Escalation & Resolution Rules
- Note categories:
    - `general_information` — customer calls in with a general question.
    - `follow_up` — customer calls in to follow up on an existing ticket.
    - `escalation` — customer calls in with a complaint.
    - `escalation_resolved` — an employee logs this to indicate a prior escalation was resolved. This resolves that specific escalation but does not by itself close the ticket.
    - `resolved` — an employee logs this to close out the ticket overall. This is the only note category that transitions a ticket's `status` to `closed` (and can only be logged when the ticket has no currently unresolved escalation).
    - The first note on any ticket can only be `general_information` or `escalation` (`follow_up`/`escalation_resolved`/`resolved` require prior context that doesn't yet exist).
- An **escalation** is identified by an `escalation` note on a ticket. Escalations are tracked and SLO-measured individually (per-escalation, not per-ticket) — a ticket can have multiple escalations over its lifetime.
- Only one escalation per ticket may be open (unresolved) at a time. A new `escalation` note can't be logged on a ticket until any prior escalation on that same ticket already has a matching `escalation_resolved` note. This removes any ambiguity about which escalation a resolution note applies to.
- The 48-hour SLO clock for an escalation starts when its `escalation` note is logged, and stops when its paired `escalation_resolved` note is logged. SLO is measured in **calendar hours** (nights/weekends count).
- An escalation is **"at risk" of exceeding SLO** when it is still unresolved (no `escalation_resolved` note yet) and 32+ hours have elapsed since its `escalation` note was logged.
- A ticket's `status` cannot be `closed` while it has any unresolved escalation. A ticket transitions to `closed` only when a `resolved` note is logged on it (whether or not it ever had an escalation).

# Synthetic Data Generation Plan
- Scale: ~100,000 tickets, ~8,000 customers, over a 6-month date range.
- Escalation frequency should be realistic for a contact center that isn't performing terribly (not an extreme percentage of all notes).
- Resolution-time distributions should intentionally include edge cases: comfortably within SLO, just under 48 hours, just over 48 hours, and long-unresolved/still-open escalations — to make the SQL analysis interesting.
- Reference "as of" date: anchor to the **last day of the 6-month generation window**. All SQL that needs "today" (unresolved/at-risk calculations) uses this fixed anchor instead of the real current date, so results stay consistent over time.
- Random seed: no preference — reproducibility across generator runs isn't required.
- **Intentional segment-level story**: one product line and one director's team will be deliberately tuned to underperform on SLO, and another product line and director's team will be deliberately tuned to overperform, so segment-slicing queries surface a real (synthetic) business insight rather than just a flat aggregate. I'll pick the specific segments during generation and document them in the README.

# Project Scope & Deliverables
- Folder structure:
```
sql-portfolio-project-walkthrough/
├── project_context.md
├── README.md
├── requirements.txt
├── data/              # generated support_tickets.db lives here (gitignored)
├── python/            # Faker-based synthetic data generation scripts
├── sql/               # your SQL challenge queries, organized by business question
└── dashboard/         # HTML dashboard assets
```
- The DuckDB database file (`data/support_tickets.db`) is **not** committed to the repo — it's generated on demand via script and gitignored.
- I will write all the SQL challenge queries myself. The 4 business questions already listed are a starting point, not the final list — there's intentionally room for additional stretch questions (e.g., SLO trend over time, product/team performance) to showcase more SQL techniques (`QUALIFY`, CTEs, joins, `CASE` statements) beyond the original `QUALIFY`-focused idea. Recursive CTEs are optional/undecided; the `employees` table stays a flattened (non-recursive) structure regardless.
- Once queries are written, the README should open with an executive-summary-style narrative (actual computed key findings) **and** document/narrate each query technically for prospective employers.
- A Python `requirements.txt`/virtual environment should be set up for the generation scripts.

# Scope Status
All identified gaps are resolved and the schema is fully specified in the Data Model section above. Ready to move on to database creation and the synthetic data generator.

# Implementation Decisions (no action needed unless you disagree)
- **Employee hierarchy realism**: Since `supervisor_name`/`manager_name`/`director_name` are plain text fields (not FK self-joins), I'll generate a consistent reporting-tree behind the scenes (e.g., a handful of directors, each with several managers, each with several supervisors) so employees sharing a leader show identical values — rather than randomizing each employee's leader names independently. Flag it if you'd rather each employee's hierarchy values be independently randomized.
- **Product `line`/`category` values**: I'll invent a small set of plausible product lines/categories (this is a generic contact center, not insurance-specific) since none were specified.
- **Date range**: I'll set the 6-month window to end on the reference/anchor date and pick an arbitrary start date 6 months prior, since the exact dates don't matter.

# Next Steps
Order of operations for the project, updated as we complete each step.

- [x] Lock project scope (business rules, data model, generation plan) — see sections above.
- [x] Scaffold folder structure (`data/`, `python/`, `sql/`, `dashboard/`, `requirements.txt`, `.gitignore`, `README.md` stub).
- [x] Write the Python synthetic data generator (`python/`): reference data first (`customers`, `products`, `employees` incl. hierarchy tree), then `tickets` + `ticket_notes` together, applying the SLO edge-case distributions. Run via `python python/generate_data.py`; writes CSVs to `data/` (gitignored). Segment story (underperforming/overperforming line + director) is randomized per run and printed at the end — pick a run's output to lock in before writing the README narrative.
- [x] Create the DuckDB database (`data/support_tickets.db`) from the generated data, matching the locked schema. Run via `python python/build_database.py` (after `generate_data.py`); creates tables with PK/FK/CHECK constraints and loads the CSVs in FK-safe order.
- [ ] Write SQL challenge queries in `sql/` (user-authored).
- [ ] Update `README.md` to document/narrate each SQL query for prospective employers.
- [ ] Build the HTML dashboard in `dashboard/` and host on GitHub.