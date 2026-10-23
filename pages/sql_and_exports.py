import time

import streamlit as st

from src import ui
from src.data import loader
from src.data.sqlrunner import load_query_templates, run_on_mysql, run_on_tables

ui.require_router()

st.title("SQL and Exports")
st.caption("This page always works on the full data, not the sidebar filters.")

raw = ui.all_tables()
source = st.session_state.get(ui.SOURCE_KEY, "csv")

presets = {
    "Cohort retention matrix": "retention_matrix",
    "Cumulative LTV by cohort": "cohort_ltv",
    "Days between orders (LAG)": "repeat_intervals",
    "Order sequence number (DENSE_RANK)": "dense_rank_orders",
}
templates = load_query_templates()

st.subheader("SQL runner")
left, right = st.columns([2.5, 1])
preset_name = left.selectbox("Starting query", list(presets))
right.info("Running on MySQL" if source == "mysql" else "Running on the CSV files (SQLite)")
query = st.text_area(
    "Query",
    value=templates.get(presets[preset_name], "SELECT * FROM customers LIMIT 10"),
    height=240,
    key=f"query_{preset_name}",
)

if st.button("Run query", type="primary"):
    started = time.time()
    try:
        if source == "mysql":
            result = run_on_mysql(query, loader.get_db_settings(ui.secret_settings()))
        else:
            result = run_on_tables(query, raw.customers, raw.products, raw.orders)
        st.success(f"{len(result):,} rows in {time.time() - started:.2f} seconds")
        st.dataframe(result, width="stretch")
    except Exception as error:
        st.error(f"The query failed: {error}")

st.divider()
st.subheader("Power BI exports")
st.write(
    "Connect dim_customers.customer_id to fact_orders.customer_id and dim_products.product_id to "
    "fact_orders.product_id, both one to many."
)
first, second, third = st.columns(3)
for column, name, frame in (
    (first, "dim_customers.csv", raw.customers),
    (second, "dim_products.csv", raw.products),
    (third, "fact_orders.csv", raw.orders),
):
    column.download_button(
        f"Download {name}", frame.to_csv(index=False).encode("utf-8"), name, "text/csv", width="stretch"
    )
