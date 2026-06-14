import pandas as pd
import numpy as np

def get_connection(conn_details):
    if not conn_details:
        raise ValueError("Connection details missing.")
        
    try:
        import mysql.connector  # mysql library
    except ImportError:
        raise ImportError(
            "Missing dependency: mysql-connector-python. "
            "Please run: pip install mysql-connector-python"
        )
        
    return mysql.connector.connect(  # connect to local db
        host=conn_details.get("host", "localhost"),
        port=int(conn_details.get("port", 3306)),
        user=conn_details.get("user", "root"),
        password=conn_details.get("password", ""),
        database=conn_details.get("database", "ecommerce_analytics")
    )

def fetch_data_from_db(conn_details):
    conn = None
    try:
        conn = get_connection(conn_details)  # open conn
        df_customers = pd.read_sql("SELECT customer_id, customer_name, signup_date, segment FROM customers", conn)  # customer data
        df_products = pd.read_sql("SELECT product_id, product_name, category, price FROM products", conn)
        df_orders = pd.read_sql("SELECT order_id, customer_id, product_id, order_date, quantity, order_value FROM orders", conn)  # orders table
        
        df_customers["signup_date"] = pd.to_datetime(df_customers["signup_date"])  # change to datetme
        df_orders["order_date"] = pd.to_datetime(df_orders["order_date"])
        
        return df_customers, df_products, df_orders
    finally:
        if conn:
            conn.close()

def calculate_cohort_retention(df_orders, df_customers):
    df = pd.merge(df_orders, df_customers, on="customer_id", how="inner")  # merge both tables
    
    df["cohort_month"] = df["signup_date"].dt.to_period("M")  # signup month
    df["order_month"] = df["order_date"].dt.to_period("M")
    df["month_index"] = (df["order_month"].dt.year - df["cohort_month"].dt.year) * 12 + \
                         (df["order_month"].dt.month - df["cohort_month"].dt.month)  # diff in months
    
    cohort_group = df.groupby(["cohort_month", "month_index"])["customer_id"].nunique().reset_index()  # count unique users
    
    cohort_counts = cohort_group.pivot_table(  # create pivot
        index="cohort_month",
        columns="month_index",
        values="customer_id"
    )
    
    cohort_sizes = cohort_counts.iloc[:, 0]  # month 0 users
    cohort_percentages = cohort_counts.divide(cohort_sizes, axis=0)  # retension rate
    
    cohort_counts.index = cohort_counts.index.astype(str)
    cohort_percentages.index = cohort_percentages.index.astype(str)
    
    return cohort_counts, cohort_percentages

def calculate_cohort_ltv(df_orders, df_customers):
    df = pd.merge(df_orders, df_customers, on="customer_id", how="inner")
    cohort_sizes = df_customers.groupby(df_customers["signup_date"].dt.to_period("M"))["customer_id"].nunique().to_dict()  # cohort size
    
    df["cohort_month"] = df["signup_date"].dt.to_period("M")
    df["order_month"] = df["order_date"].dt.to_period("M")
    df["month_index"] = (df["order_month"].dt.year - df["cohort_month"].dt.year) * 12 + \
                         (df["order_month"].dt.month - df["cohort_month"].dt.month)
    
    cohort_spend = df.groupby(["cohort_month", "month_index"])["order_value"].sum().reset_index()  # total rev
    
    spend_pivot = cohort_spend.pivot_table(
        index="cohort_month",
        columns="month_index",
        values="order_value"
    ).fillna(0)
    
    cumulative_spend = spend_pivot.cumsum(axis=1)  # cumsum for ltv
    
    cohort_ltv = pd.DataFrame(index=cumulative_spend.index, columns=cumulative_spend.columns)
    for cohort, size in cohort_sizes.items():
        if cohort in cumulative_spend.index:
            cohort_ltv.loc[cohort] = cumulative_spend.loc[cohort] / size  # avg spend per person
            
    cohort_ltv.index = cohort_ltv.index.astype(str)
    return cohort_ltv.astype(float)

def calculate_purchase_intervals(df_orders):
    df_sorted = df_orders.sort_values(by=["customer_id", "order_date"])  # sort by cust and date
    df_sorted["prev_order_date"] = df_sorted.groupby("customer_id")["order_date"].shift(1)  # prev date
    df_sorted["days_between"] = (df_sorted["order_date"] - df_sorted["prev_order_date"]).dt.days  # days betweeen orders
    
    return df_sorted.dropna(subset=["days_between"])
