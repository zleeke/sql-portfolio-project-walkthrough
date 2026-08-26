import time
import importlib

# Dynamic imports for modules starting with numbers
mod_dim = importlib.import_module("01_create_dimension_tables")
generate_products = mod_dim.generate_products
generate_employees = mod_dim.generate_employees
generate_customers = mod_dim.generate_customers

mod_fact = importlib.import_module("02_create_fact_tables")
generate_tickets_and_notes = mod_fact.generate_tickets_and_notes

mod_db = importlib.import_module("03_create_database")
build_database = mod_db.build_database

def main():
    print("==================================================")
    print(" Starting Synthetic Data Generation & DB Build ")
    print("==================================================\n")
    start_time = time.time()

    # Step 1: Generate Dimension CSVs
    print("--- Step 1: Generating Dimension Tables ---")
    generate_products()
    generate_employees()
    generate_customers()
    print("Dimension tables generated successfully.\n")

    # Step 2: Generate Fact CSVs (~100k tickets + notes)
    print("--- Step 2: Generating Fact Tables ---")
    generate_tickets_and_notes(num_tickets=103847)
    print("Fact tables generated successfully.\n")

    # Step 3: Build DuckDB Database
    print("--- Step 3: Building DuckDB Database ---")
    build_database()
    print("\n==================================================")
    print(f" Pipeline Complete in {time.time() - start_time:.2f} seconds! ")
    print("==================================================")

if __name__ == "__main__":
    main()