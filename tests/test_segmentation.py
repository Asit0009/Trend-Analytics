import pandas as pd
import pytest

from src.segmentation.clustering import (
    evaluate_k,
    scale_features,
    segment_customers,
    stability_check,
    summarise_segments,
)
from src.segmentation.features import build_rfm


def test_rfm_features_on_a_small_example():
    orders = pd.DataFrame({
        "order_id": [1, 2, 3, 4],
        "customer_id": [10, 10, 20, 20],
        "order_date": pd.to_datetime(["2025-01-01", "2025-01-21", "2025-01-05", "2025-01-05"]),
        "order_value": [100.0, 50.0, 30.0, 70.0],
    })
    rfm = build_rfm(orders, as_of=pd.Timestamp("2025-02-01")).set_index("customer_id")
    assert rfm.loc[10, "recency_days"] == 11
    assert rfm.loc[10, "frequency"] == 2
    assert rfm.loc[10, "monetary"] == 150.0
    assert rfm.loc[20, "recency_days"] == 27
    assert rfm.loc[20, "frequency"] == 2
    assert rfm.loc[20, "monetary"] == 100.0


def test_default_reference_date_is_the_day_after_the_last_order():
    orders = pd.DataFrame({
        "order_id": [1],
        "customer_id": [1],
        "order_date": pd.to_datetime(["2025-03-10"]),
        "order_value": [10.0],
    })
    assert build_rfm(orders).loc[0, "recency_days"] == 1


def test_one_rfm_row_per_customer_with_orders(small_dataset):
    customers, products, orders = small_dataset
    rfm = build_rfm(orders)
    assert rfm["customer_id"].is_unique
    assert set(rfm["customer_id"]) == set(orders["customer_id"])
    assert (rfm["frequency"] >= 1).all()
    assert (rfm["recency_days"] >= 1).all()


@pytest.mark.parametrize("k", [3, 4, 5])
def test_every_customer_gets_exactly_one_label(small_dataset, k):
    customers, products, orders = small_dataset
    rfm = build_rfm(orders)
    segmented, explained = segment_customers(rfm, k)
    assert len(segmented) == len(rfm)
    assert segmented["customer_id"].is_unique
    assert segmented["segment"].notna().all()
    assert segmented["cluster"].nunique() == k
    assert segmented.groupby("cluster")["segment"].nunique().eq(1).all()
    assert segmented["segment"].nunique() == k
    assert len(explained) == 2


def test_segment_summary_adds_up(small_dataset):
    customers, products, orders = small_dataset
    rfm = build_rfm(orders)
    segmented, _ = segment_customers(rfm, 4)
    summary = summarise_segments(segmented)
    assert summary["customers"].sum() == len(rfm)
    assert summary["share_of_customers"].sum() == pytest.approx(1.0)
    assert summary["total_spend"].sum() == pytest.approx(rfm["monetary"].sum())


def test_same_seed_gives_same_labels(small_dataset):
    customers, products, orders = small_dataset
    rfm = build_rfm(orders)
    first, _ = segment_customers(rfm, 4, seed=1)
    second, _ = segment_customers(rfm, 4, seed=1)
    assert (first["cluster"].values == second["cluster"].values).all()


def test_choosing_k_returns_a_value_in_range(small_dataset):
    customers, products, orders = small_dataset
    scores, best_k, elbow_k = evaluate_k(scale_features(build_rfm(orders)), range(2, 7))
    assert list(scores["k"]) == [2, 3, 4, 5, 6]
    assert 3 <= best_k <= 6
    assert 2 <= elbow_k <= 6
    assert scores["inertia"].is_monotonic_decreasing


def test_segments_are_stable_across_seeds(small_dataset):
    customers, products, orders = small_dataset
    stability = stability_check(build_rfm(orders), 3, seeds=range(5))
    assert stability["mean_ari"] > 0.9
    assert stability["min_ari"] <= 1.0
