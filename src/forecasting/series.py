import pandas as pd

ALL_CATEGORIES = "All categories"


def monthly_revenue(orders, products, category=ALL_CATEGORIES):
    merged = pd.merge(orders, products[["product_id", "category"]], on="product_id", how="inner")
    if category != ALL_CATEGORIES:
        merged = merged[merged["category"] == category]
    if merged.empty:
        return pd.Series(dtype=float, name="revenue")
    series = merged.set_index("order_date")["order_value"].resample("MS").sum()
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="MS")
    series = series.reindex(full_index, fill_value=0.0)
    series.name = "revenue"
    return series
