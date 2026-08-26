import duckdb
from pathlib import Path

# Paths relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "support_tickets.db"

# SQL statements to recreate tables
CREATE_CUSTOMERS_TABLE = """
CREATE TABLE customers (
    customer_id VARCHAR PRIMARY KEY,
    customer_name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    phone_number VARCHAR,
    city VARCHAR,
    state VARCHAR,
    signup_date DATE NOT NULL
);
"""

CREATE_PRODUCTS_TABLE = """
CREATE TABLE products (
    product_id VARCHAR PRIMARY KEY,
    product_name VARCHAR NOT NULL,
    line VARCHAR NOT NULL,
    category VARCHAR NOT NULL
);
"""

CREATE_EMPLOYEES_TABLE = """
CREATE TABLE employees (
    employee_id VARCHAR PRIMARY KEY,
    employee_name VARCHAR NOT NULL,
    hire_date DATE NOT NULL,
    supervisor_name VARCHAR NOT NULL,
    manager_name VARCHAR NOT NULL,
    director_name VARCHAR NOT NULL
);
"""

CREATE_TICKETS_TABLE = """
CREATE TABLE tickets (
    ticket_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR NOT NULL REFERENCES customers(customer_id),
    product_id VARCHAR NOT NULL REFERENCES products(product_id),
    initial_employee_id VARCHAR NOT NULL REFERENCES employees(employee_id),
    status VARCHAR NOT NULL CHECK (status IN ('open', 'closed'))
);
"""

CREATE_TICKET_NOTES_TABLE = """
CREATE TABLE ticket_notes (
    ticket_note_id VARCHAR PRIMARY KEY,
    ticket_id VARCHAR NOT NULL REFERENCES tickets(ticket_id),
    employee_id VARCHAR NOT NULL REFERENCES employees(employee_id),
    category VARCHAR NOT NULL CHECK (
        category IN ('general_information', 'follow_up', 'escalation', 'escalation_resolved', 'resolved')
    ),
    created_tstmp TIMESTAMP NOT NULL
);
"""

def build_database():
    """
    Creates DuckDB database at data/support_tickets.db and loads generated CSV facts/dimensions.
    """
    print(f"Connecting to DuckDB at {DB_PATH}...")
    conn = duckdb.connect(str(DB_PATH))
    
    try:
        # Drop existing tables in reverse FK order
        print("Dropping old tables if present...")
        conn.execute("DROP TABLE IF EXISTS ticket_notes;")
        conn.execute("DROP TABLE IF EXISTS tickets;")
        conn.execute("DROP TABLE IF EXISTS employees;")
        conn.execute("DROP TABLE IF EXISTS products;")
        conn.execute("DROP TABLE IF EXISTS customers;")
        
        # Create dimension tables
        print("Creating dimension tables...")
        conn.execute(CREATE_CUSTOMERS_TABLE)
        conn.execute(CREATE_PRODUCTS_TABLE)
        conn.execute(CREATE_EMPLOYEES_TABLE)
        
        # Create fact tables
        print("Creating fact tables...")
        conn.execute(CREATE_TICKETS_TABLE)
        conn.execute(CREATE_TICKET_NOTES_TABLE)
        
        # Load CSV data into DuckDB tables
        print("Loading CSV files into DuckDB...")
        conn.execute(f"COPY customers FROM '{(DATA_DIR / 'customers.csv').as_posix()}' (HEADER, AUTO_DETECT);")
        conn.execute(f"COPY products FROM '{(DATA_DIR / 'products.csv').as_posix()}' (HEADER, AUTO_DETECT);")
        conn.execute(f"COPY employees FROM '{(DATA_DIR / 'employees.csv').as_posix()}' (HEADER, AUTO_DETECT);")
        conn.execute(f"COPY tickets FROM '{(DATA_DIR / 'tickets.csv').as_posix()}' (HEADER, AUTO_DETECT);")
        conn.execute(f"COPY ticket_notes FROM '{(DATA_DIR / 'ticket_notes.csv').as_posix()}' (HEADER, AUTO_DETECT);")
        
        print("\n--- Database Built Successfully! ---")
        
        # Print table row summary
        for table in ["customers", "products", "employees", "tickets", "ticket_notes"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"Table '{table}': {count:,} rows")
            
    finally:
        conn.close()

if __name__ == "__main__":
    build_database()