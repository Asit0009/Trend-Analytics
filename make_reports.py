import json
from pathlib import Path

import pandas as pd

from src.data.loader import load_from_csv
from src.forecasting.backtest import best_model_name, compare_models
from src.forecasting.forecast import forecast_with_range
from src.forecasting.series import ALL_CATEGORIES, monthly_revenue
from src.segmentation.clustering import (
    evaluate_k,
    scale_features,
    segment_customers,
    stability_check,
    summarise_segments,
)
from src.segmentation.features import build_rfm

REPORTS_DIR = Path(__file__).parent / "reports"
BACKTEST_HORIZON = 6
FORECAST_HORIZON = 6


def forecast_report(orders, products):
    names = [ALL_CATEGORIES] + sorted(products["category"].unique())
    report = {}
    long_tables = []
    for name in names:
        series = monthly_revenue(orders, products, name)
        table, backtests = compare_models(series, horizon=BACKTEST_HORIZON)
        best = best_model_name(table)
        future = forecast_with_range(series, best, backtests[best], FORECAST_HORIZON)
        test_months = backtests[best]["target_month"]
        report[name] = {
            "months_of_history": len(series),
            "test_window": f"{test_months.min():%Y-%m} to {test_months.max():%Y-%m}",
            "backtest_origins": int(backtests[best]["train_end"].nunique()),
            "best_model": best,
            "models": table.round(2).to_dict(orient="records"),
            "next_6_months": [
                {
                    "month": f"{row.month:%Y-%m}",
                    "forecast": round(row.forecast),
                    "lower": round(row.lower),
                    "upper": round(row.upper),
                }
                for row in future.itertuples()
            ],
        }
        long_tables.append(table.assign(Series=name))
    return report, pd.concat(long_tables)[["Series"] + list(long_tables[0].columns[:-1])]


def segmentation_report(orders):
    rfm = build_rfm(orders)
    scores, best_k, elbow_k = evaluate_k(scale_features(rfm))
    segmented, explained = segment_customers(rfm, best_k)
    summary = summarise_segments(segmented)
    report = {
        "customers_segmented": len(rfm),
        "k_scores": scores.round(4).to_dict(orient="records"),
        "best_k_by_silhouette": best_k,
        "elbow_k": elbow_k,
        "chosen_k": best_k,
        "pca_variance_kept": round(float(explained.sum()), 4),
        "stability": {key: round(value, 4) if isinstance(value, float) else value
                      for key, value in stability_check(rfm, best_k).items()},
        "segments": summary.round(4).to_dict(orient="records"),
    }
    return report, summary


def main():
    customers, products, orders = load_from_csv()
    REPORTS_DIR.mkdir(exist_ok=True)

    forecasting, backtest_table = forecast_report(orders, products)
    segmentation, segment_table = segmentation_report(orders)

    metrics = {
        "data": {
            "customers": int(len(customers)),
            "orders": int(len(orders)),
            "revenue": round(float(orders["order_value"].sum())),
            "first_order": f"{orders['order_date'].min():%Y-%m-%d}",
            "last_order": f"{orders['order_date'].max():%Y-%m-%d}",
        },
        "forecasting": forecasting,
        "segmentation": segmentation,
    }
    (REPORTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    backtest_table.round(2).to_csv(REPORTS_DIR / "backtest_table.csv", index=False)
    segment_table.round(2).to_csv(REPORTS_DIR / "segment_summary.csv", index=False)
    print("wrote reports/metrics.json, backtest_table.csv, segment_summary.csv")


if __name__ == "__main__":
    main()
