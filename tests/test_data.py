import numpy as np
import pandas as pd
import pytest

from generate_data import END_DATE, START_DATE, build_dataset
from src.data import cohorts, loader
from src.data.filters import apply_filters
from src.data.sqlrunner import load_query_templates, run_on_tables

DB_VARIABLES = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")


def test_same_seed_gives_same_data():
    first = build_dataset(seed=3, n_customers=200)
    second = build_dataset(seed=3, n_customers=200)
    for left, right in zip(first, second):
        pd.testing.assert_frame_equal(left, right)


def test_different_seed_gives_different_orders():
    first = build_dataset(seed=3, n_customers=200)[2]
    second = build_dataset(seed=4, n_customers=200)[2]
    assert len(first) != len(second) or not first["order_value"].equals(second["order_value"])


def test_orders_are_consistent_with_customers_and_products(small_dataset):
    customers, products, orders = small_dataset
    merged = orders.merge(customers, on="customer_id").merge(products, on="product_id")
    assert orders["order_id"].is_unique
    assert (merged["order_date"] >= merged["signup_date"]).all()
    assert merged["order_date"].between(START_DATE, END_DATE).all()
    assert np.allclose(merged["order_value"], merged["quantity"] * merged["price"])
    assert orders["customer_id"].isin(customers["customer_id"]).all()
    assert customers["customer_id"].is_unique


def test_festive_months_sell_more_than_slow_months(small_dataset):
    customers, products, orders = small_dataset
    by_month = orders.groupby(orders["order_date"].dt.month)["order_value"].sum()
    assert by_month[[10, 11, 12]].mean() > 1.3 * by_month[[6, 7, 8]].mean()


def test_filters_by_channel_category_and_date(small_dataset):
    customers, products, orders = small_dataset
    start, end = "2025-01-01", "2025-06-30"
    filtered_customers, filtered_products, filtered = apply_filters(
        customers, products, orders, channels=["Retail"], categories=["Footwear"], start=start, end=end
    )
    assert set(filtered_customers["segment"]) == {"Retail"}
    assert set(filtered_products["category"]) == {"Footwear"}
    assert filtered["order_date"].between(start, end).all()
    merged = filtered.merge(products, on="product_id").merge(customers, on="customer_id")
    assert set(merged["category"]) == {"Footwear"}
    assert set(merged["segment"]) == {"Retail"}
    assert 0 < len(filtered) < len(orders)


def test_no_filter_keeps_everything(small_dataset):
    customers, products, orders = small_dataset
    kept_customers, kept_products, kept_orders = apply_filters(customers, products, orders)
    assert len(kept_orders) == len(orders)
    assert len(kept_customers) == len(customers)


def test_retention_uses_signup_counts_as_cohort_size(small_dataset):
    customers, products, orders = small_dataset
    counts, percentages, sizes = cohorts.calculate_cohort_retention(orders, customers)
    assert (percentages.fillna(0) <= 1.0).all().all()
    assert sizes.sum() == len(customers)
    assert (counts[0] <= sizes).all()


def test_ltv_is_cumulative_and_blank_after_the_data_ends(small_dataset):
    customers, products, orders = small_dataset
    ltv = cohorts.calculate_cohort_ltv(orders, customers)
    first_cohort = ltv.iloc[0].dropna()
    assert first_cohort.is_monotonic_increasing
    last_cohort = ltv.iloc[-1]
    assert last_cohort.notna().sum() == 1


def test_purchase_intervals_are_positive(small_dataset):
    customers, products, orders = small_dataset
    intervals = cohorts.calculate_purchase_intervals(orders)
    assert (intervals["days_between"] >= 0).all()
    assert len(intervals) == len(orders) - orders["customer_id"].nunique()


def test_customer_summary_totals(small_dataset):
    customers, products, orders = small_dataset
    summary = cohorts.calculate_customer_summary(orders, customers)
    assert len(summary) == len(customers)
    assert summary["total_spend"].sum() == pytest.approx(orders["order_value"].sum())


def test_every_reference_query_runs_on_the_tables(small_dataset):
    customers, products, orders = small_dataset
    templates = load_query_templates()
    assert len(templates) == 4
    for name, query in templates.items():
        result = run_on_tables(query, customers, products, orders)
        assert len(result) > 0, name


def test_db_settings_come_from_the_environment(monkeypatch):
    for key in DB_VARIABLES:
        monkeypatch.delenv(key, raising=False)
    assert loader.get_db_settings() is None
    monkeypatch.setenv("DB_USER", "shop")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    settings = loader.get_db_settings()
    assert settings["user"] == "shop"
    assert settings["password"] == "secret"
    assert settings["database"] == "ecommerce_analytics"


def test_db_settings_fall_back_to_streamlit_secrets(monkeypatch):
    for key in DB_VARIABLES:
        monkeypatch.delenv(key, raising=False)
    settings = loader.get_db_settings({"user": "reader", "host": "db.example", "port": 3307})
    assert settings["user"] == "reader"
    assert settings["host"] == "db.example"
    assert settings["port"] == 3307


def test_missing_csv_files_give_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="generate_data.py"):
        loader.load_from_csv(tmp_path)
