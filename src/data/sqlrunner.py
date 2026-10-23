import re
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from src.data.loader import connect, query_frame

QUERY_FILE = Path(__file__).with_name("cohort_analysis.sql")
QUERY_PATTERN = re.compile(r"--\s*\[QUERY_START:\s*(\w+)\](.*?)--\s*\[QUERY_END:\s*\1\]", re.DOTALL)


def load_query_templates(path=QUERY_FILE):
    text = Path(path).read_text(encoding="utf-8")
    return {name: sql.strip() for name, sql in QUERY_PATTERN.findall(text)}


def parse_day(value):
    return date.fromisoformat(str(value)[:10])


def sql_year(value):
    return None if value is None else parse_day(value).year


def sql_month(value):
    return None if value is None else parse_day(value).month


def sql_datediff(later, earlier):
    if later is None or earlier is None:
        return None
    return (parse_day(later) - parse_day(earlier)).days


def sql_date_format(value, pattern):
    return None if value is None else parse_day(value).strftime(pattern)


def run_on_tables(query, customers, products, orders):
    connection = sqlite3.connect(":memory:")
    try:
        connection.create_function("year", 1, sql_year)
        connection.create_function("month", 1, sql_month)
        connection.create_function("datediff", 2, sql_datediff)
        connection.create_function("date_format", 2, sql_date_format)

        customers_sql = customers.copy()
        customers_sql["signup_date"] = customers_sql["signup_date"].dt.strftime("%Y-%m-%d")
        orders_sql = orders.copy()
        orders_sql["order_date"] = orders_sql["order_date"].dt.strftime("%Y-%m-%d")
        customers_sql.to_sql("customers", connection, index=False)
        products.to_sql("products", connection, index=False)
        orders_sql.to_sql("orders", connection, index=False)
        return pd.read_sql(query.strip().rstrip(";"), connection)
    finally:
        connection.close()


def run_on_mysql(query, settings):
    connection = connect(settings)
    try:
        return query_frame(connection, query.strip().rstrip(";"))
    finally:
        connection.close()
