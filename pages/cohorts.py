import pandas as pd
import streamlit as st

from src import ui
from src.data import cohorts
from src.plots import charts

ui.require_router()

st.title("Cohorts and Retention")
st.caption(
    "Each row is the group of customers who signed up in one month. Each column shows the share of "
    "that group that ordered in a later month, counted in months since signup."
)

tables = ui.page_tables(use_categories=True)
counts, percentages, sizes = cohorts.calculate_cohort_retention(tables.orders, tables.customers)

left, middle, right = st.columns([1.2, 1.2, 1.6])
mode = left.radio("Show", ["Percent", "Customers"], horizontal=True)
colorscale = middle.selectbox("Colors", ["Blues", "Teal", "Viridis", "Purples", "Oranges"])
longest = int(counts.columns.max())
max_tenure = right.slider("Months since signup to show", 3, max(longest, 4), min(12, longest))

shown_columns = [column for column in counts.columns if column <= max_tenure]
matrix = percentages[shown_columns] if mode == "Percent" else counts[shown_columns]
st.plotly_chart(
    charts.retention_heatmap(matrix, as_percent=(mode == "Percent"), colorscale=colorscale),
    width="stretch",
)

with st.expander("Cohort table"):
    table = pd.DataFrame({"Cohort": counts.index, "Signups": sizes.values})
    for month in (0, 1, 2, 3):
        if month in percentages.columns:
            table[f"Month {month} %"] = (percentages[month] * 100).round(1).values
    st.dataframe(table, hide_index=True, width="stretch")
