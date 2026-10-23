import numpy as np
import pandas as pd
import pytest

from generate_data import build_dataset


@pytest.fixture(scope="session")
def small_dataset():
    return build_dataset(seed=7, n_customers=800)


@pytest.fixture
def monthly_series():
    rng = np.random.default_rng(0)
    months = pd.date_range("2022-01-01", periods=40, freq="MS")
    season = 1 + 0.3 * np.sin(2 * np.pi * (months.month - 1) / 12)
    trend = 1000 + 15 * np.arange(40)
    values = trend * season * rng.normal(1, 0.03, 40)
    return pd.Series(values, index=months, name="revenue")
