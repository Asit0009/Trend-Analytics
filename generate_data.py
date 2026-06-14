import os
import random
import datetime
import pandas as pd
import numpy as np

# Seed random generators to keep data generation deterministic across local runs
random.seed(42)
np.random.seed(42)

def generate_fashion_dataset():
    """
    Generates a localized customer transaction dataset for the 'Thread & Trend' apparel brand.
    Outputs a MySQL setup script and Power BI CSV files. No SQLite files are generated.
    """
    print("Initializing Thread & Trend data simulation engine...")
    
    # Date boundaries for transactions
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2026, 5, 31)
    
    # Core fashion product catalog in INR
    product_categories = {
        "Womenswear": [
            ("Designer Anarkali Suit", 4999.00),
            ("Linen Summer Dress", 2499.00),
            ("High-Waisted Denim Jeans", 1899.00),
            ("Floral Wrap Top", 1299.00),
            ("Cotton Lounge Kaftan", 999.00)
        ],
        "Menswear": [
            ("Premium Cotton Blazer", 5999.00),
            ("Oxford Button-Down Shirt", 1799.00),
            ("Slim Fit Chino Trousers", 1999.00),
            ("Graphic Print Streetwear Hoodie", 2199.00),
            ("Pack of 3 Crewneck Tees", 1199.00)
        ],
        "Footwear": [
            ("Handcrafted Leather Loafers", 3499.00),
            ("Classic White Sneakers", 2899.00),
            ("Casual Canvas Slip-Ons", 1499.00),
            ("Strappy Block Heels", 1999.00)
        ],
        "Accessories": [
            ("Genuine Leather Crossbody Bag", 2499.00),
            ("Polarized Aviator Sunglasses", 1299.00),
            ("Minimalist Gold-Plated Neckpiece", 899.00),
            ("Textured Leather Belt", 999.00)
        ]
    }
    
    # Create product records
    products = []
    pid = 101
    for cat, items in product_categories.items():
        for name, price in items:
            products.append({
                "product_id": pid,
                "product_name": name,
                "category": cat,
                "price": price
            })
            pid += 1
            
    df_products = pd.DataFrame(products)
    
    # Customer name templates for Indian market
    first_names = [
        "Aarav", "Vihaan", "Aditya", "Sai", "Arjun", "Krishna", "Ishaan", "Shaurya", "Atharva", "Kabir", 
        "Priya", "Ananya", "Diya", "Aanya", "Pihu", "Prisha", "Aadhya", "Saanvi", "Kiara", "Meera", 
        "Rahul", "Amit", "Vikram", "Sanjay", "Rohan", "Neha", "Pooja", "Shreya", "Karan", "Deepak",
        "Anil", "Sunita", "Rajesh", "Geeta", "Vijay", "Lata", "Ramesh", "Kiran", "Suresh", "Rekha"
    ]
    last_names = [
        "Sharma", "Verma", "Gupta", "Patel", "Mehta", "Joshi", "Kumar", "Singh", "Reddy", "Nair", 
        "Iyer", "Rao", "Choudhury", "Das", "Sen", "Mishra", "Pandey", "Yadav", "Trivedi", "Banerjee",
        "Deshmukh", "Kulkarni", "Patil", "Bose", "Pillai", "Shetty", "Saxena", "Roy", "Grover", "Kapoor"
    ]
    
    segments = ["Retail", "Corporate", "Direct"]
    customers = []
    cust_id = 1001
    
    # Populate cohorts on a monthly basis
    curr = start_date
    while curr <= end_date:
        yr, mn = curr.year, curr.month
        
        # Account for typical Indian retail cycles: Diwali (Oct/Nov) and Spring launch (Mar/Apr)
        base_size = 90
        if mn in [10, 11]:
            cohort_size = int(base_size * random.uniform(1.4, 1.7))
        elif mn in [3, 4]:
            cohort_size = int(base_size * random.uniform(1.1, 1.3))
        elif mn in [1, 2]:
            cohort_size = int(base_size * random.uniform(0.7, 0.9))
        else:
            cohort_size = int(base_size * random.uniform(0.9, 1.1))
            
        for _ in range(cohort_size):
            days_in_mn = pd.Period(f"{yr}-{mn}").days_in_month
            day = random.randint(1, days_in_mn)
            signup_dt = datetime.date(yr, mn, day)
            
            if signup_dt > end_date:
                continue
                
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            seg = np.random.choice(segments, p=[0.75, 0.18, 0.07])
            
            customers.append({
                "customer_id": cust_id,
                "customer_name": name,
                "signup_date": signup_dt,
                "segment": seg,
                "cohort_month": signup_dt.strftime("%Y-%m")
            })
            cust_id += 1
            
        # Move to next calendar month
        if mn == 12:
            curr = datetime.date(yr + 1, 1, 1)
        else:
            curr = datetime.date(yr, mn + 1, 1)
            
    df_customers = pd.DataFrame(customers)
    
    # Cohort retention decay parameters (standard log decay profile)
    ret_curve = {
        0: 1.00, 1: 0.35, 2: 0.22, 3: 0.16, 4: 0.13, 5: 0.11, 
        6: 0.10, 7: 0.09, 8: 0.08, 9: 0.08, 10: 0.07, 11: 0.07, 
        12: 0.06, 13: 0.06, 14: 0.05, 15: 0.05, 16: 0.05
    }
    
    orders = []
    oid = 50001
    
    for _, cust in df_customers.iterrows():
        cid = cust["customer_id"]
        signup_dt = cust["signup_date"]
        
        # Initial purchase immediately after signup
        first_order_dt = signup_dt + datetime.timedelta(days=random.randint(0, 3))
        if first_order_dt <= end_date:
            prod = df_products.sample(1).iloc[0]
            qty = int(np.random.choice([1, 2, 3], p=[0.75, 0.20, 0.05]))
            
            orders.append({
                "order_id": oid,
                "customer_id": cid,
                "product_id": prod["product_id"],
                "order_date": first_order_dt,
                "quantity": qty,
                "order_value": round(prod["price"] * qty, 2)
            })
            oid += 1
            
            last_order_dt = first_order_dt
            max_months = (end_date.year - signup_dt.year) * 12 + (end_date.month - signup_dt.month)
            
            # Simulate repeat purchases over active months
            for m in range(1, max_months + 1):
                p_rate = ret_curve.get(m, 0.05)
                
                # Loyalty adjustments based on business rules
                if cust["segment"] == "Corporate":
                    p_rate *= 1.20
                elif cust["segment"] == "Direct":
                    p_rate *= 0.85
                    
                if random.random() < p_rate:
                    orders_count = np.random.choice([1, 2], p=[0.90, 0.10])
                    
                    for _ in range(orders_count):
                        target_yr = signup_dt.year + (signup_dt.month + m - 1) // 12
                        target_mn = (signup_dt.month + m - 1) % 12 + 1
                        
                        days_in_target = pd.Period(f"{target_yr}-{target_mn}").days_in_month
                        order_day = random.randint(1, days_in_target)
                        order_dt = datetime.date(target_yr, target_mn, order_day)
                        
                        if order_dt <= end_date and order_dt >= last_order_dt:
                            prod = df_products.sample(1).iloc[0]
                            # Repeat purchase basket characteristics
                            qty_p = [0.70, 0.22, 0.08] if m <= 3 else [0.60, 0.28, 0.09, 0.03]
                            qty = int(np.random.choice([1, 2, 3] if m <= 3 else [1, 2, 3, 4], p=qty_p))
                            
                            orders.append({
                                "order_id": oid,
                                "customer_id": cid,
                                "product_id": prod["product_id"],
                                "order_date": order_dt,
                                "quantity": qty,
                                "order_value": round(prod["price"] * qty, 2)
                            })
                            oid += 1
                            last_order_dt = order_dt
                            
    df_orders = pd.DataFrame(orders)
    
    # Save SQL Seed File for local MySQL Workbench environment
    sql_file = "setup_mysql.sql"
    print(f"Generating {sql_file} for MySQL local import...")
    
    sql_lines = [
        "CREATE DATABASE IF NOT EXISTS ecommerce_analytics;",
        "USE ecommerce_analytics;\n",
        "DROP TABLE IF EXISTS orders;",
        "DROP TABLE IF EXISTS customers;",
        "DROP TABLE IF EXISTS products;\n",
        """CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(100),
    signup_date DATE,
    segment VARCHAR(50)
);\n""",
        """CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);\n""",
        """CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    product_id INT,
    order_date DATE,
    quantity INT,
    order_value DECIMAL(10, 2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);\n"""
    ]
    
    # Write Products DML
    prod_vals = [f"({row['product_id']}, '{row['product_name'].replace(chr(39), chr(39)+chr(39))}', '{row['category']}', {row['price']})" for _, row in df_products.iterrows()]
    sql_lines.append(f"INSERT INTO products VALUES\n" + ",\n".join(prod_vals) + ";\n")
    
    # Write Customers DML (batch in 200s for memory safety inside Workbench)
    cust_vals = [f"({row['customer_id']}, '{row['customer_name'].replace(chr(39), chr(39)+chr(39))}', '{row['signup_date']}', '{row['segment']}')" for _, row in df_customers.iterrows()]
    for i in range(0, len(cust_vals), 200):
        sql_lines.append(f"INSERT INTO customers VALUES\n" + ",\n".join(cust_vals[i:i+200]) + ";\n")
        
    # Write Orders DML (batch in 200s)
    order_vals = [f"({row['order_id']}, {row['customer_id']}, {row['product_id']}, '{row['order_date']}', {row['quantity']}, {row['order_value']})" for _, row in df_orders.iterrows()]
    for i in range(0, len(order_vals), 200):
        sql_lines.append(f"INSERT INTO orders VALUES\n" + ",\n".join(order_vals[i:i+200]) + ";\n")
        
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))
    print(f"Database seed script successfully saved to '{sql_file}'.")
    
    # Save Power BI Relational Schema CSVs
    print("Writing dimension and fact CSVs for Power BI loading...")
    df_customers.copy().drop(columns=["cohort_month"]).to_csv("dim_customers.csv", index=False)
    df_products.to_csv("dim_products.csv", index=False)
    df_orders.to_csv("fact_orders.csv", index=False)
    print("Power BI CSV exports complete.")
    
    # Cleanup SQLite leftovers if any are present
    if os.path.exists("ecommerce.db"):
        try:
            os.remove("ecommerce.db")
        except Exception:
            pass
            
    print(f"Data generation summary: {len(df_customers)} customers, {len(df_orders)} transactions.")

if __name__ == "__main__":
    generate_fashion_dataset()
