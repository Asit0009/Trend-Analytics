import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

SEASON_LENGTH = 12
BASELINE_NAME = "Same month last year"


def seasonal_naive(train, horizon):
    last_year = train.values[-SEASON_LENGTH:]
    repeats = int(np.ceil(horizon / SEASON_LENGTH))
    return np.tile(last_year, repeats)[:horizon].astype(float)


def holt_winters(train, horizon):
    seasonal_kind = "mul" if (train > 0).all() else "add"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ExponentialSmoothing(
            train,
            trend="add",
            damped_trend=True,
            seasonal=seasonal_kind,
            seasonal_periods=SEASON_LENGTH,
            initialization_method="estimated",
        ).fit()
    return np.asarray(fitted.forecast(horizon), dtype=float)


def sarima(train, horizon):
    log_train = np.log1p(train)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = SARIMAX(
            log_train,
            order=(1, 1, 1),
            seasonal_order=(0, 1, 1, SEASON_LENGTH),
        ).fit(disp=False, maxiter=200)
    return np.expm1(np.asarray(fitted.forecast(horizon), dtype=float))


def calendar_features(month_number, time_index):
    angle = 2 * np.pi * month_number / SEASON_LENGTH
    return [np.sin(angle), np.cos(angle), time_index]


def lag_row(history, month_number, time_index):
    return [history[-1], history[-2], history[-SEASON_LENGTH]] + calendar_features(month_number, time_index)


def ridge_lags(train, horizon):
    log_values = list(np.log1p(train.values))
    months = train.index.month.values
    rows = []
    targets = []
    for position in range(SEASON_LENGTH, len(log_values)):
        rows.append(lag_row(log_values[:position], months[position], position))
        targets.append(log_values[position])
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(np.array(rows), np.array(targets))

    history = list(log_values)
    next_month = train.index[-1]
    predictions = []
    for step in range(horizon):
        next_month = next_month + pd.DateOffset(months=1)
        row = lag_row(history, next_month.month, len(history))
        predicted = float(model.predict(np.array([row]))[0])
        predictions.append(predicted)
        history.append(predicted)
    return np.expm1(np.array(predictions))


MODELS = {
    BASELINE_NAME: seasonal_naive,
    "Holt-Winters": holt_winters,
    "SARIMA": sarima,
    "Ridge with lags": ridge_lags,
}
