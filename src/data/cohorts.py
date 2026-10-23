import numpy as np
import pandas as pd


def add_month_index(orders, customers):
    merged = pd.merge(orders, customers[["customer_id", "signup_date"]], on="customer_id", how="inner")
    merged["cohort_month"] = merged["signup_date"].dt.to_period("M")
    order_month = merged["order_date"].dt.to_period("M")
    merged["month_index"] = (
        (order_month.dt.year - merged["cohort_month"].dt.year) * 12
        + (order_month.dt.month - merged["cohort_month"].dt.month)
    )
    return merged[merged["month_index"] >= 0]


def cohort_sizes(customers):
    sizes = customers.groupby(customers["signup_date"].dt.to_period("M"))["customer_id"].nunique()
    sizes.index = sizes.index.astype(str)
    return sizes


def calculate_cohort_retention(orders, customers):
    merged = add_month_index(orders, customers)
    active = merged.groupby(["cohort_month", "month_index"])["customer_id"].nunique().reset_index()
    counts = active.pivot_table(index="cohort_month", columns="month_index", values="customer_id")
    counts.index = counts.index.astype(str)
    sizes = cohort_sizes(customers).reindex(counts.index)
    percentages = counts.divide(sizes, axis=0)
    return counts, percentages, sizes


def calculate_cohort_ltv(orders, customers):
    merged = add_month_index(orders, customers)
    spend = merged.groupby(["cohort_month", "month_index"])["order_value"].sum().reset_index()
    spend_table = spend.pivot_table(
        index="cohort_month", columns="month_index", values="order_value"
    ).fillna(0)
    spend_table.index = spend_table.index.astype(str)
    sizes = cohort_sizes(customers).reindex(spend_table.index)
    cumulative = spend_table.cumsum(axis=1)
    ltv = cumulative.divide(sizes, axis=0)

    last_month = orders["order_date"].max().to_period("M")
    for cohort in ltv.index:
        cohort_period = pd.Period(cohort, freq="M")
        months_observed = (last_month.year - cohort_period.year) * 12 + (last_month.month - cohort_period.month)
        ltv.loc[cohort, ltv.columns > months_observed] = np.nan
    return ltv.astype(float)


def calculate_purchase_intervals(orders):
    ordered = orders.sort_values(["customer_id", "order_date", "order_id"]).copy()
    ordered["previous_order_date"] = ordered.groupby("customer_id")["order_date"].shift(1)
    ordered["days_between"] = (ordered["order_date"] - ordered["previous_order_date"]).dt.days
    return ordered.dropna(subset=["days_between"])


def calculate_customer_summary(orders, customers):
    per_customer = orders.groupby("customer_id").agg(
        order_count=("order_id", "nunique"),
        total_spend=("order_value", "sum"),
        items_bought=("quantity", "sum"),
        first_order=("order_date", "min"),
        last_order=("order_date", "max"),
    ).reset_index()
    summary = pd.merge(customers, per_customer, on="customer_id", how="left")
    summary["order_count"] = summary["order_count"].fillna(0).astype(int)
    summary["total_spend"] = summary["total_spend"].fillna(0.0)
    summary["items_bought"] = summary["items_bought"].fillna(0).astype(int)
    summary["aov"] = np.where(
        summary["order_count"] > 0, summary["total_spend"] / summary["order_count"].replace(0, 1), 0.0
    )
    summary["is_repeat"] = summary["order_count"] > 1
    return summary
