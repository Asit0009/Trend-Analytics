import numpy as np
import pandas as pd

from src.forecasting.models import BASELINE_NAME, MODELS

MIN_TRAIN_MONTHS = 24


def mae(actual, predicted):
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual, predicted):
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mape(actual, predicted):
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def rolling_origin_backtest(series, model_fn, horizon=6, n_origins=7, min_train=MIN_TRAIN_MONTHS):
    n_origins = min(n_origins, len(series) - horizon - min_train + 1)
    if n_origins < 1:
        raise ValueError(
            f"Need at least {min_train + horizon} months of history, got {len(series)}."
        )
    last_origin = len(series) - horizon
    rows = []
    for origin in range(last_origin - n_origins + 1, last_origin + 1):
        train = series.iloc[:origin]
        predicted = np.asarray(model_fn(train, horizon), dtype=float)
        actual = series.iloc[origin:origin + horizon]
        for step in range(horizon):
            rows.append({
                "train_end": train.index[-1],
                "target_month": actual.index[step],
                "step": step + 1,
                "actual": float(actual.iloc[step]),
                "predicted": float(predicted[step]),
            })
    return pd.DataFrame(rows)


def score_backtest(results):
    actual = results["actual"].values
    predicted = results["predicted"].values
    return {
        "MAE": mae(actual, predicted),
        "RMSE": rmse(actual, predicted),
        "MAPE %": mape(actual, predicted),
    }


def compare_models(series, horizon=6, n_origins=7):
    backtests = {}
    scores = []
    for name, model_fn in MODELS.items():
        results = rolling_origin_backtest(series, model_fn, horizon, n_origins)
        backtests[name] = results
        scores.append({"Model": name, **score_backtest(results)})
    table = pd.DataFrame(scores)
    baseline_rmse = table.loc[table["Model"] == BASELINE_NAME, "RMSE"].iloc[0]
    table["RMSE vs baseline %"] = (table["RMSE"] / baseline_rmse - 1) * 100
    table["Beats baseline"] = np.where(
        table["Model"] == BASELINE_NAME, "-", np.where(table["RMSE"] < baseline_rmse, "Yes", "No")
    )
    return table, backtests


def best_model_name(table):
    return table.loc[table["RMSE"].idxmin(), "Model"]
