import pandas as pd

RFM_COLUMNS = ["recency_days", "frequency", "monetary"]


def build_rfm(orders, as_of=None):
    if orders.empty:
        return pd.DataFrame(columns=["customer_id"] + RFM_COLUMNS)
    if as_of is None:
        as_of = orders["order_date"].max() + pd.Timedelta(days=1)
    per_customer = orders.groupby("customer_id").agg(
        last_order=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("order_value", "sum"),
    )
    per_customer["recency_days"] = (as_of - per_customer["last_order"]).dt.days
    rfm = per_customer[RFM_COLUMNS].reset_index()
    return rfm
