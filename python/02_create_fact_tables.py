import pandas as pd
import random as rnd
import datetime as dt
from pathlib import Path

# Setup dynamic paths relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# -----------------------------------------------------------------------------
# Global Settings & Reference Window Anchor Date
# -----------------------------------------------------------------------------
# Fixed 6-month window anchor: Jan 1, 2026 to Jun 30, 2026
AS_OF_DATE = dt.datetime(2026, 6, 30, 23, 59, 59)
START_DATE = dt.datetime(2026, 1, 1, 0, 0, 0)

print(f"Window Start: {START_DATE}")
print(f"Anchor As-Of Date: {AS_OF_DATE}")

def load_dimension_data():
    """
    Loads customers, products, and employees dimension CSVs into pandas DataFrames.
    Returns dictionaries/lists needed for ticket generation.
    """
    customers_df = pd.read_csv(DATA_DIR / "customers.csv")
    products_df = pd.read_csv(DATA_DIR / "products.csv")
    employees_df = pd.read_csv(DATA_DIR / "employees.csv")
    
    print(f"Loaded {len(customers_df)} customers, {len(products_df)} products, {len(employees_df)} employees.")
    
    return {
        "customers": customers_df,
        "products": products_df,
        "employees": employees_df
    }

def get_random_timestamp(start_dt, end_dt):
    """
    Generates a random datetime between start_dt and end_dt.
    """
    delta_seconds = int((end_dt - start_dt).total_seconds())
    if delta_seconds <= 0:
        return start_dt
    random_sec = rnd.randint(0, delta_seconds)
    return start_dt + dt.timedelta(seconds=random_sec)

def generate_tickets_and_notes(num_tickets):
    """
    Generates synthetic tickets and ticket_notes facts adhering to SLO and escalation rules.
    """
    dims = load_dimension_data()
    customers_df = dims["customers"]
    products_df = dims["products"]
    employees_df = dims["employees"]
    
    # Quick lookup pools
    customer_ids = customers_df["customer_id"].tolist()
    
    # Product mappings for segment story tuning
    product_lines = products_df["line"].unique().tolist()
    underperforming_line = rnd.choice(product_lines)
    overperforming_line = rnd.choice([l for l in product_lines if l != underperforming_line])
    
    # Director mappings for segment story tuning
    directors = employees_df["director_name"].unique().tolist()
    underperforming_director = rnd.choice(directors)
    overperforming_director = rnd.choice([d for d in directors if d != underperforming_director])
    
    print("\n--- Segment Story Configuration ---")
    print(f"Underperforming Line: {underperforming_line} | Director: {underperforming_director}")
    print(f"Overperforming Line:  {overperforming_line}  | Director: {overperforming_director}\n")
    
    # Convert DataFrames to dict lookups for fast iteration speed
    product_dict = products_df.set_index("product_id")["line"].to_dict()
    employee_dict = employees_df.set_index("employee_id")["director_name"].to_dict()
    employee_ids = employees_df["employee_id"].tolist()
    product_ids = products_df["product_id"].tolist()

    tickets_list = []
    notes_list = []
    
    note_counter = 1
    
    for t_idx in range(1, num_tickets + 1):
        ticket_id = f"TCK_{t_idx:06d}"
        cust_id = rnd.choice(customer_ids)
        prod_id = rnd.choice(product_ids)
        emp_id = rnd.choice(employee_ids)
        
        prod_line = product_dict[prod_id]
        emp_director = employee_dict[emp_id]
        
        # Determine escalation probability for this ticket based on segment tuning
        escalation_prob = 0.08  # Default 15% escalation rate
        if prod_line == underperforming_line or emp_director == underperforming_director:
            escalation_prob = 0.13  # Higher escalation rate for underperforming segment
        elif prod_line == overperforming_line or emp_director == overperforming_director:
            escalation_prob = 0.05  # Lower escalation rate for overperforming segment
            
        # Ticket creation timestamp
        ticket_created = get_random_timestamp(START_DATE, AS_OF_DATE - dt.timedelta(days=1))
        
        # --- NOTE 1: Initial Note ---
        is_escalation = rnd.random() < escalation_prob
        initial_category = "escalation" if is_escalation else "general_information"
        
        notes_list.append({
            "ticket_note_id": f"NOTE_{note_counter:08d}",
            "ticket_id": ticket_id,
            "employee_id": emp_id,
            "category": initial_category,
            "created_tstmp": ticket_created
        })
        note_counter += 1
        
        current_tstmp = ticket_created
        has_open_escalation = is_escalation
        ticket_is_closed = False
        
        # --- Handle Escalation Resolution (if escalated) ---
        if is_escalation:
            # Determine SLO resolution distribution (in hours)
            if prod_line == underperforming_line or emp_director == underperforming_director:
                # 50% breach SLO (>48 hours), 50% within SLO
                res_hours = rnd.choices([12, 36, 52, 72, 120], weights=[0.2, 0.3, 0.25, 0.15, 0.10])[0]
            elif prod_line == overperforming_line or emp_director == overperforming_director:
                # 95% comfortably within SLO (<24 hours)
                res_hours = rnd.choices([4, 12, 24, 36, 50], weights=[0.4, 0.4, 0.15, 0.04, 0.01])[0]
            else:
                # Standard overall distribution (~85% in SLO)
                res_hours = rnd.choices([6, 18, 36, 46, 54, 80], weights=[0.25, 0.35, 0.25, 0.05, 0.05, 0.05])[0]
                
            resolution_tstmp = ticket_created + dt.timedelta(hours=res_hours)
            
            # Log escalation_resolved ONLY if resolution occurs before AS_OF_DATE
            if resolution_tstmp <= AS_OF_DATE:
                resolving_emp = rnd.choice(employee_ids)
                notes_list.append({
                    "ticket_note_id": f"NOTE_{note_counter:08d}",
                    "ticket_id": ticket_id,
                    "employee_id": resolving_emp,
                    "category": "escalation_resolved",
                    "created_tstmp": resolution_tstmp
                })
                note_counter += 1
                current_tstmp = resolution_tstmp
                has_open_escalation = False
                
        # --- Handle Ticket Overall Closure ('resolved' note) ---
        # If no open escalation exists, decide if ticket gets closed (e.g. 85% of completed tickets get closed)
        if not has_open_escalation and rnd.random() < 0.85:
            closure_delay_hours = rnd.randint(1, 24)
            closure_tstmp = current_tstmp + dt.timedelta(hours=closure_delay_hours)
            
            if closure_tstmp <= AS_OF_DATE:
                closing_emp = rnd.choice(employee_ids)
                notes_list.append({
                    "ticket_note_id": f"NOTE_{note_counter:08d}",
                    "ticket_id": ticket_id,
                    "employee_id": closing_emp,
                    "category": "resolved",
                    "created_tstmp": closure_tstmp
                })
                note_counter += 1
                ticket_is_closed = True
                
        # --- Record Ticket Row ---
        tickets_list.append({
            "ticket_id": ticket_id,
            "customer_id": cust_id,
            "product_id": prod_id,
            "initial_employee_id": emp_id,
            "status": "closed" if ticket_is_closed else "open"
        })

    # Convert to DataFrames
    df_tickets = pd.DataFrame(tickets_list)
    df_notes = pd.DataFrame(notes_list)
    
    # Save CSVs
    print("Saving fact CSVs to data/ directory...")
    df_tickets.to_csv(DATA_DIR / "tickets.csv", index=False)
    df_notes.to_csv(DATA_DIR / "ticket_notes.csv", index=False)
    print(f"Done! Generated {len(df_tickets):,} tickets and {len(df_notes):,} ticket notes.")

if __name__ == "__main__":
    # You can test with 5,000 first, then scale up to 100,000!
    generate_tickets_and_notes(num_tickets=103847)