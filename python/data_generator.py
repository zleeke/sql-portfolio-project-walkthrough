import time
from create_dimension_tables import generate_products, generate_employees, generate_customers
from create_fact_tables import generate_tickets_and_notes
from python.create_database import build_database

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