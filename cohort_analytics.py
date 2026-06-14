import pandas as pd
import numpy as np

def get_connection(conn_details):
    """
    Returns a MySQL connection handle using parameters defined in the dashboard UI.
    """
    if not conn_details:
        raise ValueError("Connection details missing.")
        
    try:
        import mysql.connector
    except ImportError:
        raise ImportError(
            "Missing dependency: mysql-connector-python. "
            "Please run: pip install mysql-connector-python"
        )
        
    return mysql.connector.connect(
        host=conn_details.get("host", "localhost"),
        port=int(conn_details.get("port", 3306)),
        user=conn_details.get("user", "root"),
        password=conn_details.get("password", ""),
        database=conn_details.get("database", "ecommerce_analytics")
    )

def fetch_data_from_db(conn_details):
    """
    Pulls clean pandas dataframes for customers, products, and orders.
    """
    conn = None
    try:
        conn = get_connection(conn_details)
        
        # Load tables
        df_customers = pd.read_sql("SELECT customer_id, customer_name, signup_date, segment FROM customers", conn)
        df_products = pd.read_sql("SELECT product_id, product_name, category, price FROM products", conn)
        df_orders = pd.read_sql("SELECT order_id, customer_id, product_id, order_date, quantity, order_value FROM orders", conn)
        
        # Enforce date formats
        df_customers["signup_date"] = pd.to_datetime(df_customers["signup_date"])
        df_orders["order_date"] = pd.to_datetime(df_orders["order_date"])
        
        return df_customers, df_products, df_orders
    finally:
        if conn:
            conn.close()

def calculate_cohort_retention(df_orders, df_customers):
    """
    Returns user cohort counts and retention percentages.
    """
    # Join transactional records to shopper cohorts
    df = pd.merge(df_orders, df_customers, on="customer_id", how="inner")
    
    # Calculate months elapsed relative to signup month
    df["cohort_month"] = df["signup_date"].dt.to_period("M")
    df["order_month"] = df["order_date"].dt.to_period("M")
    df["month_index"] = (df["order_month"].dt.year - df["cohort_month"].dt.year) * 12 + \
                         (df["order_month"].dt.month - df["cohort_month"].dt.month)
    
    # Calculate unique customers per cohort index
    cohort_group = df.groupby(["cohort_month", "month_index"])["customer_id"].nunique().reset_index()
    
    # Pivot to generate retention counts table
    cohort_counts = cohort_group.pivot_table(
        index="cohort_month",
        columns="month_index",
        values="customer_id"
    )
    
    # Divide row-wise by Month 0 (initial size) to get percentages
    cohort_sizes = cohort_counts.iloc[:, 0]
    cohort_percentages = cohort_counts.divide(cohort_sizes, axis=0)
    
    # Format indexes to string for Plotly rendering
    cohort_counts.index = cohort_counts.index.astype(str)
    cohort_percentages.index = cohort_percentages.index.astype(str)
    
    return cohort_counts, cohort_percentages

def calculate_cohort_ltv(df_orders, df_customers):
    """
    Returns the cumulative LTV (average spend per customer) over cohort tenure.
    """
    df = pd.merge(df_orders, df_customers, on="customer_id", how="inner")
    
    # Store initial cohort sizes for division
    cohort_sizes = df_customers.groupby(df_customers["signup_date"].dt.to_period("M"))["customer_id"].nunique().to_dict()
    
    df["cohort_month"] = df["signup_date"].dt.to_period("M")
    df["order_month"] = df["order_date"].dt.to_period("M")
    df["month_index"] = (df["order_month"].dt.year - df["cohort_month"].dt.year) * 12 + \
                         (df["order_month"].dt.month - df["cohort_month"].dt.month)
    
    # Sum order values per cohort month index
    cohort_spend = df.groupby(["cohort_month", "month_index"])["order_value"].sum().reset_index()
    
    # Pivot and compute cumulative spend curves
    spend_pivot = cohort_spend.pivot_table(
        index="cohort_month",
        columns="month_index",
        values="order_value"
    ).fillna(0)
    
    cumulative_spend = spend_pivot.cumsum(axis=1)
    
    # Divide cumulative spends by respective signup cohort size
    cohort_ltv = pd.DataFrame(index=cumulative_spend.index, columns=cumulative_spend.columns)
    for cohort, size in cohort_sizes.items():
        if cohort in cumulative_spend.index:
            cohort_ltv.loc[cohort] = cumulative_spend.loc[cohort] / size
            
    cohort_ltv.index = cohort_ltv.index.astype(str)
    return cohort_ltv.astype(float)

def calculate_purchase_intervals(df_orders):
    """
    Computes intervals in days between repeat checkouts.
    """
    df_sorted = df_orders.sort_values(by=["customer_id", "order_date"])
    df_sorted["prev_order_date"] = df_sorted.groupby("customer_id")["order_date"].shift(1)
    df_sorted["days_between"] = (df_sorted["order_date"] - df_sorted["prev_order_date"]).dt.days
    
    return df_sorted.dropna(subset=["days_between"])
