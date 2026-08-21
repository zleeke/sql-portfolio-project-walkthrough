"""Generators for the reference tables: customers, products, employees.

Employees are generated as a flattened hierarchy: a pool of director/manager/
supervisor names is built first (used only as text on agent rows), then
individual agents are created underneath each supervisor. Only agents get an
`employee_id` and appear as `initial_employee_id` / `ticket_notes.employee_id`
elsewhere, since they're the ones actually handling tickets.
"""

import random
from datetime import timedelta

import config


def generate_customers(fake, n=config.NUM_CUSTOMERS):
    customers = []
    # All customers sign up before the window starts, so every ticket's
    # timestamp is guaranteed to fall after its customer's signup_date.
    signup_start = config.WINDOW_START - timedelta(days=730)
    signup_end = config.WINDOW_START - timedelta(days=1)
    signup_span_days = (signup_end - signup_start).days

    for customer_id in range(1, n + 1):
        signup_date = signup_start + timedelta(days=random.randint(0, signup_span_days))
        customers.append(
            {
                "customer_id": customer_id,
                "customer_name": fake.name(),
                "email": fake.unique.email(),
                "phone_number": fake.phone_number(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "signup_date": signup_date,
            }
        )
    return customers


def generate_products(fake):
    products = []
    product_id = 1
    # Generate a fixed number of products for every line/category combo
    # defined in config.PRODUCT_LINES.
    for line, categories in config.PRODUCT_LINES.items():
        for category in categories:
            for _ in range(config.PRODUCTS_PER_CATEGORY):
                products.append(
                    {
                        "product_id": product_id,
                        "product_name": fake.unique.catch_phrase(),
                        "line": line,
                        "category": category,
                    }
                )
                product_id += 1
    return products


def generate_employees(fake):
    """Build the director/manager/supervisor tree, then agents underneath.

    Returns (employees, directors) where `employees` only contains agent rows
    (the ones that hold an employee_id) and `directors` is the list of
    director names, used to pick the SLO segment story.
    """
    directors = [fake.unique.name() for _ in range(config.NUM_DIRECTORS)]

    employees = []
    employee_id = 1
    # Agents can be hired well before the window (up to 8 years prior) but
    # not so close to the end that they'd have no time to work tickets.
    hire_start = config.WINDOW_START - timedelta(days=365 * 8)
    hire_end = config.WINDOW_END - timedelta(days=30)
    hire_span_days = (hire_end - hire_start).days

    # Walk director -> manager -> supervisor -> agent, generating one leader
    # name per branch so every agent under that branch shares identical
    # supervisor_name/manager_name/director_name values.
    for director_name in directors:
        for _ in range(config.MANAGERS_PER_DIRECTOR):
            manager_name = fake.unique.name()
            for _ in range(config.SUPERVISORS_PER_MANAGER):
                supervisor_name = fake.unique.name()
                num_agents = random.randint(*config.AGENTS_PER_SUPERVISOR_RANGE)
                for _ in range(num_agents):
                    hire_date = hire_start + timedelta(days=random.randint(0, hire_span_days))
                    employees.append(
                        {
                            "employee_id": employee_id,
                            "employee_name": fake.unique.name(),
                            "hire_date": hire_date,
                            "supervisor_name": supervisor_name,
                            "manager_name": manager_name,
                            "director_name": director_name,
                        }
                    )
                    employee_id += 1

    return employees, directors
