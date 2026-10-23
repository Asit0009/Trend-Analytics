import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

load_dotenv(ROOT_DIR / ".env")

CSV_FILES = {
    "customers": "dim_customers.csv",
    "products": "dim_products.csv",
    "orders": "fact_orders.csv",
}


def get_db_settings(secrets=None):
    secrets = dict(secrets or {})
    settings = {
        "host": os.getenv("DB_HOST", secrets.get("host", "localhost")),
        "port": int(os.getenv("DB_PORT", secrets.get("port", 3306))),
        "user": os.getenv("DB_USER", secrets.get("user", "")),
        "password": os.getenv("DB_PASSWORD", secrets.get("password", "")),
        "database": os.getenv("DB_NAME", secrets.get("database", "ecommerce_analytics")),
    }
    if not settings["user"]:
        return None
    return settings


def clean_tables(customers, products, orders):
    customers = customers.copy()
    products = products.copy()
    orders = orders.copy()
    customers["signup_date"] = pd.to_datetime(customers["signup_date"])
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["order_value"] = pd.to_numeric(orders["order_value"], errors="coerce").fillna(0.0)
    orders["quantity"] = pd.to_numeric(orders["quantity"], errors="coerce").fillna(1).astype(int)
    products["price"] = pd.to_numeric(products["price"], errors="coerce").fillna(0.0)
    return customers, products, orders


def load_from_csv(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    paths = {name: data_dir / file_name for name, file_name in CSV_FILES.items()}
    missing = [path.name for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing {', '.join(missing)} in {data_dir}. Run generate_data.py first."
        )
    return clean_tables(
        pd.read_csv(paths["customers"]),
        pd.read_csv(paths["products"]),
        pd.read_csv(paths["orders"]),
    )


def connect(settings):
    import mysql.connector

    return mysql.connector.connect(
        host=settings["host"],
        port=int(settings["port"]),
        user=settings["user"],
        password=settings["password"],
        database=settings["database"],
        connection_timeout=5,
    )


def query_frame(connection, sql):
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)
    finally:
        cursor.close()


def load_from_mysql(settings):
    if not settings:
        raise ValueError("No database settings found. Add them to a .env file or Streamlit secrets.")
    connection = connect(settings)
    try:
        customers = query_frame(
            connection, "SELECT customer_id, customer_name, signup_date, segment FROM customers"
        )
        products = query_frame(
            connection, "SELECT product_id, product_name, category, price FROM products"
        )
        orders = query_frame(
            connection,
            "SELECT order_id, customer_id, product_id, order_date, quantity, order_value FROM orders",
        )
    finally:
        connection.close()
    return clean_tables(customers, products, orders)
