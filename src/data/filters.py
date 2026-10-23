import pandas as pd


def apply_filters(customers, products, orders, channels=None, categories=None, start=None, end=None):
    if channels is not None:
        customers = customers[customers["segment"].isin(channels)]
    orders = orders[orders["customer_id"].isin(customers["customer_id"])]

    if categories is not None:
        allowed_products = products.loc[products["category"].isin(categories), "product_id"]
        orders = orders[orders["product_id"].isin(allowed_products)]
        products = products[products["category"].isin(categories)]

    if start is not None:
        orders = orders[orders["order_date"] >= pd.Timestamp(start)]
    if end is not None:
        orders = orders[orders["order_date"] <= pd.Timestamp(end)]
    return customers.copy(), products.copy(), orders.copy()
