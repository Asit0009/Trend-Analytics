import numpy as np
import pandas as pd

from src.forecasting.models import MODELS


def forecast_with_range(series, model_name, backtest_results, horizon=6, lower_quantile=0.1, upper_quantile=0.9):
    point = np.asarray(MODELS[model_name](series, horizon), dtype=float)
    point = np.clip(point, 0, None)

    results = backtest_results[backtest_results["predicted"] > 0]
    relative_error = results["actual"] / results["predicted"] - 1
    low = min(float(relative_error.quantile(lower_quantile)), 0.0)
    high = max(float(relative_error.quantile(upper_quantile)), 0.0)

    future_months = pd.date_range(series.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
    return pd.DataFrame({
        "month": future_months,
        "forecast": point,
        "lower": point * (1 + low),
        "upper": point * (1 + high),
    })
