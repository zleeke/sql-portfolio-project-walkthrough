import pandas as pd
import random as rnd
import re
import zipcodes
from faker import Faker
from pathlib import Path

fake = Faker()

# Get root directory of the project (one level up from python/ folder)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def generate_products():
    """
    Generates synthetic product records mapping for product lines, categories,
    and product names.
    """
    # 1. Define raw product hierarchy (product line -> category -> product name)
    # We manually define this dictionary list because Faker doesn't have built-in tech/appliance generators.
    raw_products = [
        # Smart Home Line
        {"line": "Smart Home", "category": "Climate", "product_name": "Smart Thermostat Pro"},
        {"line": "Smart Home", "category": "Climate", "product_name": "Smart Air Purifier"},
        {"line": "Smart Home", "category": "Security", "product_name": "HD Doorbell Camera"},
        {"line": "Smart Home", "category": "Security", "product_name": "Outdoor Floodlight Cam"},
        {"line": "Smart Home", "category": "Security", "product_name": "Smart Door Lock"},

        # Personal Tech Line
        {"line": "Personal Tech", "category": "Audio", "product_name": "Wireless Noise-Canceling Headphones"},
        {"line": "Personal Tech", "category": "Audio", "product_name": "Pro Earbuds"},
        {"line": "Personal Tech", "category": "Wearables", "product_name": "Fitness Tracker Watch"},
        {"line": "Personal Tech", "category": "Wearables", "product_name": "Smart Health Ring"},

        # Kitchen Appliances Line
        {"line": "Kitchen Appliances", "category": "Cooking", "product_name": "Air Fryer Deluxe"},
        {"line": "Kitchen Appliances", "category": "Cooking", "product_name": "Smart Pressure Cooker"},
        {"line": "Kitchen Appliances", "category": "Beverage", "product_name": "Espresso Machine Pro"},
        {"line": "Kitchen Appliances", "category": "Beverage", "product_name": "Smart Coffee Maker"}
    ]

    products_list = []
    
    # 2. Loop through and assign product_id
    for idx, item in enumerate(raw_products, start=1):
        product_record = {
            "product_id": f"PROD_{idx:03d}",  # Generates PROD_001, PROD_002, etc.
            "product_name": item["product_name"],
            "line": item["line"],
            "category": item["category"]
        }
        products_list.append(product_record)
        
    # 3. Convert to pandas DataFrame
    df_products = pd.DataFrame(products_list)
    
    # Save to CSV using dynamic absolute path
    df_products.to_csv(DATA_DIR / "products.csv", index=False)
    
    return df_products

def generate_employees(num_employees=102):
    # 1. Generate 3 Directors
    directors = [f"{fake.first_name()} {fake.last_name()}" for _ in range(3)]
    
    # 2. Generate 6 Managers (2 per Director, balanced)
    managers = []
    for idx in range(6):
        managers.append({
            "manager_name": f"{fake.first_name()} {fake.last_name()}",
            "director_name": directors[idx % len(directors)]
        })
        
    # 3. Generate 18 Supervisors (3 per Manager, balanced)
    supervisors = []
    for idx in range(18):
        mgr = managers[idx % len(managers)]
        supervisors.append({
            "supervisor_name": f"{fake.first_name()} {fake.last_name()}",
            "manager_name": mgr["manager_name"],
            "director_name": mgr["director_name"]
        })
        
    # 4. Generate Frontline Employees
    employees_list = []
    for idx in range(1, num_employees + 1):
        # Using rnd.choice now gives realistic, slight variance around a balanced tree
        sup = supervisors[(idx - 1) % len(supervisors)]
        hire_date = fake.date_between(start_date="-5y", end_date="today")
        
        employees_list.append({
            "employee_id": f"EMP_{idx:03d}",
            "employee_name": f"{fake.first_name()} {fake.last_name()}",
            "hire_date": hire_date,
            "supervisor_name": sup["supervisor_name"],
            "manager_name": sup["manager_name"],
            "director_name": sup["director_name"]
        })
        
    df_employees = pd.DataFrame(employees_list)
    df_employees.to_csv(DATA_DIR / "employees.csv", index=False)
    
    return df_employees

def generate_customers(num_customers=8023):
    """
    Generates synthetic customer records using Faker.
    """

    # Get all valid US zip code dictionaries
    zip_records = zipcodes.filter_by(active=True)

    print(f"Loaded {len(zip_records)} real zip code records")

    customers_list = []
    
    for idx in range(1, num_customers + 1):
        name = f"{fake.first_name()} {fake.last_name()}"
        
        # Clean up name using regex for a formatted email handle
        clean = re.sub(r"[^a-z0-9\s]", "", name.lower())
        email_handle = re.sub(r"\s+", ".", clean)
        
        domain = rnd.choice(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com"])
        email = f"{email_handle}@{domain}"

        # Pick one real zip record — city/state/zip all come from it, guaranteed consistent
        zip_record = rnd.choice(zip_records)

        customer_record = {
            "customer_id": f"CUST_{idx:05d}",
            "customer_name": name,
            "email": email,
            "phone_number": fake.phone_number(),
            "city": zip_record["city"],
            "state": zip_record["state"],
            "signup_date": fake.date_between(start_date="-3y", end_date="today")
        }
        customers_list.append(customer_record)
        
    # Convert to pandas DataFrame
    df_customers = pd.DataFrame(customers_list)
    
    # Save to CSV using dynamic absolute path
    df_customers.to_csv(DATA_DIR / "customers.csv", index=False)
    
    return df_customers

# Call the function to generate the products data
if __name__ == "__main__":
    products_df = generate_products()
    print("Products data generated successfully!")
    print(products_df)

    employees_df = generate_employees()
    print("Employees data generated successfully!")
    print(employees_df)

    customers_df = generate_customers()
    print("Customers data generated successfully!")
    print(customers_df)
    

