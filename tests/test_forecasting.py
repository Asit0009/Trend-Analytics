import numpy as np
import pandas as pd
import pytest

from src.forecasting.backtest import (
    best_model_name,
    compare_models,
    mae,
    mape,
    rmse,
    rolling_origin_backtest,
)
from src.forecasting.forecast import forecast_with_range
from src.forecasting.models import BASELINE_NAME, MODELS, seasonal_naive
from src.forecasting.series import ALL_CATEGORIES, monthly_revenue


def test_monthly_revenue_is_continuous_and_keeps_the_total(small_dataset):
    customers, products, orders = small_dataset
    series = monthly_revenue(orders, products)
    assert series.index.freq is not None
    assert (series.index.day == 1).all()
    assert len(series) == 36
    assert series.sum() == pytest.approx(orders["order_value"].sum())


def test_category_series_add_up_to_the_store_series(small_dataset):
    customers, products, orders = small_dataset
    total = monthly_revenue(orders, products, ALL_CATEGORIES)
    parts = sum(
        monthly_revenue(orders, products, category).reindex(total.index, fill_value=0.0)
        for category in products["category"].unique()
    )
    assert np.allclose(total.values, parts.values)


def test_seasonal_naive_repeats_the_last_year(monthly_series):
    predicted = seasonal_naive(monthly_series, 14)
    assert np.allclose(predicted[:12], monthly_series.values[-12:])
    assert np.allclose(predicted[12:], monthly_series.values[-12:-10])


@pytest.mark.parametrize("model_name", list(MODELS))
def test_every_model_returns_one_value_per_month(monthly_series, model_name):
    predicted = MODELS[model_name](monthly_series, 6)
    assert predicted.shape == (6,)
    assert np.isfinite(predicted).all()
    assert (predicted >= 0).all()


def test_forecast_dates_continue_the_history(monthly_series):
    backtest = rolling_origin_backtest(monthly_series, MODELS[BASELINE_NAME], horizon=6, n_origins=3)
    forecast = forecast_with_range(monthly_series, BASELINE_NAME, backtest, horizon=6)
    assert len(forecast) == 6
    assert forecast["month"].iloc[0] == monthly_series.index[-1] + pd.DateOffset(months=1)
    assert (forecast["month"].diff().dropna().dt.days >= 28).all()
    assert list(forecast.columns) == ["month", "forecast", "lower", "upper"]
    assert (forecast["lower"] <= forecast["forecast"]).all()
    assert (forecast["forecast"] <= forecast["upper"]).all()


def test_backtest_only_shows_the_model_past_months(monthly_series):
    seen = []

    def spy_model(train, horizon):
        seen.append(train.index[-1])
        return np.full(horizon, train.iloc[-1])

    results = rolling_origin_backtest(monthly_series, spy_model, horizon=6, n_origins=5)
    for train_end, group in results.groupby("train_end"):
        assert train_end in seen
        assert group["target_month"].min() == train_end + pd.DateOffset(months=1)
        assert (group["target_month"] > train_end).all()
    assert results["target_month"].max() == monthly_series.index[-1]


def test_changing_future_values_does_not_change_earlier_predictions(monthly_series):
    changed = monthly_series.copy()
    changed.iloc[-6:] = changed.iloc[-6:] * 50
    for name in (BASELINE_NAME, "Holt-Winters", "Ridge with lags"):
        original = rolling_origin_backtest(monthly_series, MODELS[name], horizon=6, n_origins=4)
        altered = rolling_origin_backtest(changed, MODELS[name], horizon=6, n_origins=4)
        first_end = original["train_end"].min()
        before = original[original["train_end"] == first_end]["predicted"].values
        after = altered[altered["train_end"] == first_end]["predicted"].values
        assert np.allclose(before, after)


def test_backtest_needs_enough_history(monthly_series):
    with pytest.raises(ValueError):
        rolling_origin_backtest(monthly_series.iloc[:20], MODELS[BASELINE_NAME], horizon=6)


def test_error_metrics_on_known_numbers():
    actual = np.array([100.0, 200.0, 400.0])
    predicted = np.array([110.0, 180.0, 400.0])
    assert mae(actual, predicted) == pytest.approx(10.0)
    assert rmse(actual, predicted) == pytest.approx(np.sqrt((100 + 400 + 0) / 3))
    assert mape(actual, predicted) == pytest.approx((10 + 10 + 0) / 3)


def test_comparison_table_has_all_models_and_a_baseline_row(monthly_series):
    table, backtests = compare_models(monthly_series, horizon=6, n_origins=3)
    assert list(table["Model"]) == list(MODELS)
    assert {"MAE", "RMSE", "MAPE %", "Beats baseline"} <= set(table.columns)
    baseline_row = table[table["Model"] == BASELINE_NAME].iloc[0]
    assert baseline_row["RMSE vs baseline %"] == 0
    assert best_model_name(table) in MODELS
    assert set(backtests) == set(MODELS)
