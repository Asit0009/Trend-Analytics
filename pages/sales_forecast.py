import streamlit as st

from src import ui
from src.forecasting.backtest import MIN_TRAIN_MONTHS, best_model_name, compare_models
from src.forecasting.forecast import forecast_with_range
from src.forecasting.models import BASELINE_NAME, MODELS
from src.forecasting.series import ALL_CATEGORIES, monthly_revenue
from src.plots import charts

BACKTEST_HORIZON = 6


@st.cache_data(show_spinner="Running the backtest. SARIMA can take a few seconds.")
def run_backtest(series):
    return compare_models(series, horizon=BACKTEST_HORIZON)


ui.require_router()

st.title("Sales Forecast")
st.caption(
    "Monthly revenue forecast. Four models are tested on months they have not seen, and the one with the "
    "lowest error is used by default. The sales channel filter in the sidebar applies here."
)

tables = ui.page_tables()
categories = [ALL_CATEGORIES] + sorted(tables.products["category"].unique())

left, middle, right = st.columns(3)
category = left.selectbox("Category", categories)
horizon = middle.slider("Months to forecast", 1, 12, 6)
model_choice = right.selectbox("Model", ["Best in backtest"] + list(MODELS))

series = monthly_revenue(tables.orders, tables.products, category)
needed = MIN_TRAIN_MONTHS + BACKTEST_HORIZON
if len(series) < needed:
    st.warning(f"This selection has {len(series)} months of history. At least {needed} are needed.")
    st.stop()

comparison, backtests = run_backtest(series)
best_name = best_model_name(comparison)
model_name = best_name if model_choice == "Best in backtest" else model_choice
forecast = forecast_with_range(series, model_name, backtests[model_name], horizon)

last_year = series.iloc[-12:].iloc[:horizon]
forecast_total = forecast["forecast"].sum()
metric_one, metric_two, metric_three = st.columns(3)
metric_one.markdown(f"Model used\n\n**{model_name}**")
metric_two.metric(f"Forecast for next {horizon} months", ui.money_short(forecast_total))
metric_three.metric(
    "Same months last year",
    ui.money_short(last_year.sum()),
    delta=f"{(forecast_total / last_year.sum() - 1) * 100:+.1f}%",
)

other_models = {}
if model_choice == "Best in backtest" and model_name != BASELINE_NAME:
    other_models[BASELINE_NAME] = forecast_with_range(series, BASELINE_NAME, backtests[BASELINE_NAME], horizon)
st.plotly_chart(
    charts.forecast_chart(series, forecast, f"{category}: history and forecast", other_models),
    width="stretch",
)
st.caption(
    "The shaded range covers the middle 80% of the errors this model made in the backtest. "
    "It has the same relative width for every month."
)

st.subheader("Backtest results")
st.write(
    f"Each model was refitted {len(backtests[BASELINE_NAME]['train_end'].unique())} times, each time using only "
    f"the months before the test window, then asked to predict the next {BACKTEST_HORIZON} months. "
    f"The test months run from {backtests[model_name]['target_month'].min():%b %Y} to "
    f"{backtests[model_name]['target_month'].max():%b %Y}."
)
st.dataframe(
    comparison,
    hide_index=True,
    width="stretch",
    column_config={
        "MAE": st.column_config.NumberColumn(format="₹%.0f"),
        "RMSE": st.column_config.NumberColumn(format="₹%.0f"),
        "MAPE %": st.column_config.NumberColumn(format="%.1f"),
        "RMSE vs baseline %": st.column_config.NumberColumn(format="%+.1f"),
    },
)
beaten = comparison[comparison["Beats baseline"] == "Yes"]
if beaten.empty:
    st.info(f"None of the models beat the baseline ({BASELINE_NAME}) on RMSE for this category.")
else:
    st.success(
        f"{len(beaten)} of {len(comparison) - 1} models beat the baseline on RMSE: "
        + ", ".join(beaten["Model"]) + "."
    )

with st.expander("Forecast values and one month ahead check"):
    st.dataframe(
        forecast,
        hide_index=True,
        width="stretch",
        column_config={
            "month": st.column_config.DateColumn(format="MMM YYYY"),
            "forecast": st.column_config.NumberColumn(format="₹%.0f"),
            "lower": st.column_config.NumberColumn(format="₹%.0f"),
            "upper": st.column_config.NumberColumn(format="₹%.0f"),
        },
    )
    st.download_button(
        "Download forecast CSV", forecast.to_csv(index=False).encode("utf-8"), "forecast.csv", "text/csv"
    )
    st.plotly_chart(
        charts.backtest_chart(backtests[model_name], f"{model_name}: actual against one month ahead forecast"),
        width="stretch",
    )
