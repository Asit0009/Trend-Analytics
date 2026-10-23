import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
START_DATE = pd.Timestamp("2023-06-01")
END_DATE = pd.Timestamp("2026-05-31")

PRODUCTS = [
    (101, "Designer Anarkali Suit", "Womenswear", 4999.0),
    (102, "Linen Summer Dress", "Womenswear", 2499.0),
    (103, "High-Waisted Denim Jeans", "Womenswear", 1899.0),
    (104, "Floral Wrap Top", "Womenswear", 1299.0),
    (105, "Cotton Lounge Kaftan", "Womenswear", 999.0),
    (106, "Premium Cotton Blazer", "Menswear", 5999.0),
    (107, "Oxford Button-Down Shirt", "Menswear", 1799.0),
    (108, "Slim Fit Chino Trousers", "Menswear", 1999.0),
    (109, "Graphic Print Streetwear Hoodie", "Menswear", 2199.0),
    (110, "Pack of 3 Crewneck Tees", "Menswear", 1199.0),
    (111, "Handcrafted Leather Loafers", "Footwear", 3499.0),
    (112, "Classic White Sneakers", "Footwear", 2899.0),
    (113, "Casual Canvas Slip-Ons", "Footwear", 1499.0),
    (114, "Strappy Block Heels", "Footwear", 1999.0),
    (115, "Genuine Leather Crossbody Bag", "Accessories", 2499.0),
    (116, "Polarized Aviator Sunglasses", "Accessories", 1299.0),
    (117, "Minimalist Gold-Plated Neckpiece", "Accessories", 899.0),
    (118, "Textured Leather Belt", "Accessories", 999.0),
]

MONTH_SEASON = {
    1: 0.90, 2: 0.80, 3: 1.00, 4: 1.05, 5: 1.00, 6: 0.80,
    7: 0.75, 8: 0.90, 9: 1.00, 10: 1.35, 11: 1.55, 12: 1.25,
}

CATEGORY_SEASON = {
    "Womenswear": {10: 1.3, 11: 1.4, 12: 1.1, 2: 1.1},
    "Menswear": {11: 1.1, 12: 1.2, 3: 1.1},
    "Footwear": {3: 1.3, 4: 1.3, 5: 1.2, 7: 0.8},
    "Accessories": {2: 1.4, 12: 1.4, 11: 1.2, 6: 0.9},
}

CUSTOMER_TYPES = {
    "one_time": dict(share=0.40, mean_gap=None, lifetime=0, big=False),
    "occasional": dict(share=0.30, mean_gap=60, lifetime=250, big=False),
    "loyal": dict(share=0.13, mean_gap=22, lifetime=400, big=False),
    "big_spender": dict(share=0.08, mean_gap=55, lifetime=450, big=True),
    "lapsed": dict(share=0.09, mean_gap=28, lifetime=120, big=False),
}

FIRST_NAMES = [
    "Aarav", "Vihaan", "Atharva", "Arjun", "Krishna", "Rohan", "Vijay", "Rajesh",
    "Karan", "Dev", "Ishaan", "Kabir", "Nikhil", "Rahul", "Sameer", "Amit",
    "Saanvi", "Shreya", "Ananya", "Diya", "Isha", "Kavya", "Lata", "Meera",
    "Neha", "Pooja", "Priya", "Riya", "Sneha", "Tanvi", "Aditi", "Divya",
    "Nisha", "Pallavi", "Radhika", "Simran", "Anjali", "Swati", "Rhea", "Zoya",
]

LAST_NAMES = [
    "Singh", "Bose", "Gupta", "Verma", "Kumar", "Banerjee", "Sharma", "Patel",
    "Mehta", "Iyer", "Nair", "Reddy", "Das", "Joshi", "Kapoor", "Malhotra",
    "Chopra", "Agarwal", "Rao", "Menon", "Shah", "Pillai", "Saxena", "Bhat",
    "Khan", "Mishra", "Pandey", "Sinha", "Roy", "Ghosh",
]

SCHEMA_SQL = """CREATE DATABASE IF NOT EXISTS ecommerce_analytics;
USE ecommerce_analytics;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(100),
    signup_date DATE,
    segment VARCHAR(50)
);

CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    product_id INT,
    order_date DATE,
    quantity INT,
    order_value DECIMAL(10, 2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
"""


def build_products():
    return pd.DataFrame(PRODUCTS, columns=["product_id", "product_name", "category", "price"])


def build_customers(rng, n_customers):
    days = pd.date_range(START_DATE, END_DATE, freq="D")
    months_since_start = np.asarray((days.year - START_DATE.year) * 12 + (days.month - START_DATE.month))
    season = np.array([MONTH_SEASON[m] for m in days.month])
    weights = season * (1 + 0.006 * months_since_start)
    signup_dates = np.sort(rng.choice(days.values, size=n_customers, p=weights / weights.sum()))

    names = [
        f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}" for _ in range(n_customers)
    ]
    channels = rng.choice(["Retail", "Corporate", "Direct"], size=n_customers, p=[0.75, 0.18, 0.07])
    customers = pd.DataFrame({
        "customer_id": np.arange(1001, 1001 + n_customers),
        "customer_name": names,
        "signup_date": pd.to_datetime(signup_dates),
        "segment": channels,
    })
    return customers


def product_probabilities(products, rng):
    popularity = rng.dirichlet(np.ones(len(products)) * 4)
    table = {}
    for month in range(1, 13):
        category_factor = np.array([
            CATEGORY_SEASON[cat].get(month, 1.0) for cat in products["category"]
        ])
        regular = popularity * category_factor
        pricey = regular * np.where(products["price"].values >= 2500, 4.0, 0.5)
        table[(month, False)] = regular / regular.sum()
        table[(month, True)] = pricey / pricey.sum()
    return table


def build_orders(rng, customers, products):
    n_months = (END_DATE.year - START_DATE.year) * 12 + (END_DATE.month - START_DATE.month) + 1
    month_shock = rng.lognormal(mean=0.0, sigma=0.07, size=n_months)
    acceptance_scale = max(MONTH_SEASON.values()) * 1.3

    type_names = list(CUSTOMER_TYPES)
    type_shares = np.array([CUSTOMER_TYPES[t]["share"] for t in type_names])
    customer_types = rng.choice(type_names, size=len(customers), p=type_shares)

    probs = product_probabilities(products, rng)
    prices = products["price"].values
    product_ids = products["product_id"].values

    rows = []
    for customer_id, signup, type_name in zip(
        customers["customer_id"], customers["signup_date"], customer_types
    ):
        settings = CUSTOMER_TYPES[type_name]
        order_dates = [signup]
        if settings["mean_gap"] is not None:
            last_day = min(END_DATE, signup + pd.Timedelta(days=rng.exponential(settings["lifetime"])))
            current = signup
            while True:
                current = current + pd.Timedelta(days=max(1.0, rng.exponential(settings["mean_gap"])))
                if current > last_day:
                    break
                month_position = (current.year - START_DATE.year) * 12 + (current.month - START_DATE.month)
                chance = MONTH_SEASON[current.month] * month_shock[month_position] / acceptance_scale
                if rng.random() < min(chance, 1.0):
                    order_dates.append(current)

        for order_date in order_dates:
            product_index = rng.choice(len(products), p=probs[(order_date.month, settings["big"])])
            quantity_probs = [0.5, 0.35, 0.12, 0.03] if settings["big"] else [0.7, 0.22, 0.07, 0.01]
            quantity = int(rng.choice([1, 2, 3, 4], p=quantity_probs))
            rows.append((
                customer_id,
                int(product_ids[product_index]),
                order_date.normalize(),
                quantity,
                float(quantity * prices[product_index]),
            ))

    orders = pd.DataFrame(
        rows, columns=["customer_id", "product_id", "order_date", "quantity", "order_value"]
    )
    orders = orders.sort_values(["order_date", "customer_id"]).reset_index(drop=True)
    orders.insert(0, "order_id", np.arange(50001, 50001 + len(orders)))
    return orders


def build_dataset(seed=42, n_customers=6000):
    rng = np.random.default_rng(seed)
    products = build_products()
    customers = build_customers(rng, n_customers)
    orders = build_orders(rng, customers, products)
    return customers, products, orders


def sql_value(value):
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, pd.Timestamp):
        return "'" + value.strftime("%Y-%m-%d") + "'"
    return str(value)


def insert_statements(table, frame, batch_size=500):
    statements = []
    for start in range(0, len(frame), batch_size):
        chunk = frame.iloc[start:start + batch_size]
        values = ",\n".join(
            "(" + ", ".join(sql_value(v) for v in row) + ")" for row in chunk.itertuples(index=False)
        )
        statements.append(f"INSERT INTO {table} VALUES\n{values};\n")
    return "\n".join(statements)


def write_outputs(customers, products, orders, data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    customers.to_csv(data_dir / "dim_customers.csv", index=False)
    products.to_csv(data_dir / "dim_products.csv", index=False)
    orders.to_csv(data_dir / "fact_orders.csv", index=False)
    script = "\n".join([
        SCHEMA_SQL,
        insert_statements("products", products),
        insert_statements("customers", customers),
        insert_statements("orders", orders),
    ])
    (data_dir / "setup_mysql.sql").write_text(script, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=6000)
    args = parser.parse_args()
    customers, products, orders = build_dataset(args.seed, args.customers)
    write_outputs(customers, products, orders)
    print(f"customers: {len(customers)}, orders: {len(orders)}, revenue: {orders['order_value'].sum():,.0f}")
    print(f"orders from {orders['order_date'].min().date()} to {orders['order_date'].max().date()}")


if __name__ == "__main__":
    main()
