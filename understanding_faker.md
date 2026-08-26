# Understanding Faker

Faker is a Python library for creating realistic-looking **synthetic data**.
It does not connect to a real customer system and it does not make data true;
it simply gives us convenient functions for generating values such as names,
email addresses, cities, and product descriptions.

That makes it useful for this project: we can build a believable contact-center
dataset without using anyone's real personal information.

## The basic pattern

Faker is included in `requirements.txt`, so it is installed with the rest of
the project's Python dependencies. In a Python file, the basic pattern is:

```python
from faker import Faker

fake = Faker()

name = fake.name()
email = fake.email()
city = fake.city()
```

`Faker()` creates an object that knows how to produce many types of fake
values. Each method call generates one value. For example, `fake.name()` is a
method call, and its result is a string such as `"Alex Smith"`.

The method names are called **providers** in Faker's documentation. A
provider is a group of related methods, such as person, internet, address, or
company data. We mostly use the default providers in this project.

## How this project creates Faker

The main entry point creates one Faker object:

```python
fake = Faker()
```

It then passes that object to the functions that generate each group of rows:

```python
customers = reference_data.generate_customers(fake)
products = reference_data.generate_products(fake)
employees, directors = reference_data.generate_employees(fake)
```

Passing the object into those functions means they all use the same Faker
configuration. It also makes the functions easier to test: they receive the
data generator they need instead of creating a hidden global object.

## Faker calls used in this project

The calls in `python/reference_data.py` map to database columns like this:

| Faker call | Used for |
| --- | --- |
| `fake.name()` | Customer, employee, manager, supervisor, and director names |
| `fake.unique.email()` | Customer email addresses |
| `fake.phone_number()` | Customer phone numbers |
| `fake.city()` | Customer cities |
| `fake.state_abbr()` | Two-letter customer state values |
| `fake.unique.catch_phrase()` | Product names |

For example, one customer row is assembled from several generated values:

```python
{
		"customer_id": customer_id,
		"customer_name": fake.name(),
		"email": fake.unique.email(),
		"phone_number": fake.phone_number(),
		"city": fake.city(),
		"state": fake.state_abbr(),
		"signup_date": signup_date,
}
```

Notice that Faker generates the descriptive fields, but `customer_id` and
`signup_date` come from our own Python logic. Faker is one tool in the
generator; it does not decide the whole data model.

## `unique` values

`fake.unique.email()` asks Faker not to repeat an email address during that
Faker session. The same idea is used for product names and employee/leader
names.

This is useful when a value should look unique, but it is not a replacement
for database constraints. In this project, the integer IDs are still assigned
by our code and are the actual primary-key values. Also, a finite provider can
eventually run out of unique values and raise an error if we request too many.

## Randomness and reproducibility

Faker values are random-looking. This project can make a run repeatable by
setting a seed in `python/config.py`:

```python
SEED = 42
```

The main script applies that seed to both random sources:

```python
random.seed(config.SEED)
Faker.seed(config.SEED)
```

Both lines matter because the project uses two different systems:

- Faker generates names, emails, and other text values.
- Python's `random` module chooses customers, products, employees, dates,
	ticket paths, and SLO-resolution buckets.

If `SEED` is set to `None`, each run creates a different dataset. Keeping the
seed at `42` is helpful while learning or debugging because the generated
results can be compared from one run to the next.

## Faker versus project rules

Faker makes individual values realistic, but our code must enforce the
relationships and business rules. For example:

- `random.choice(customers)` links a ticket to an existing customer.
- A loop assigns the same generated manager and director names to everyone
	in the same reporting branch.
- `random.uniform(...)` and the configured buckets create escalation
	resolution times around the 48-hour SLO.
- The ticket simulator controls whether a note is `escalation`,
	`escalation_resolved`, or `resolved` and in what order.

This separation is important: `fake.name()` can create a name, but it cannot
know that a `resolved` note is forbidden while an escalation is still open.
That rule belongs in `python/tickets.py`.

## A tiny example

This is the smallest useful mental model for the project:

```python
from faker import Faker

fake = Faker()

for customer_id in range(1, 4):
		print(customer_id, fake.name(), fake.email())
```

The loop controls how many records are created. Faker supplies the values for
the name and email columns. Our actual generator follows the same pattern,
then adds IDs, dates, foreign-key relationships, and ticket business rules.
