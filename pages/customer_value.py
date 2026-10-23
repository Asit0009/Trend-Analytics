import pandas as pd
import streamlit as st

from src import ui
from src.data import cohorts
from src.plots import charts

ui.require_router()

st.title("Customer Value")
st.caption("Lifetime value, repeat purchase timing and a look at single customers.")

tables = ui.page_tables(use_categories=True)
orders = tables.orders
customers = tables.customers

st.subheader("Lifetime value against acquisition cost")
cac_target = st.slider("Target cost to acquire one customer (₹)", 500, 3000, 1000, step=100)
ltv = cohorts.calculate_cohort_ltv(orders, customers)

left, right = st.columns([2.2, 1])
with left:
    st.plotly_chart(charts.ltv_chart(ltv, cac_target), width="stretch")
with right:
    rows = []
    for cohort in ltv.index:
        values = ltv.loc[cohort].dropna()
        crossed = values[values >= cac_target]
        rows.append({
            "Cohort": cohort,
            "Latest LTV": values.iloc[-1] if len(values) else 0.0,
            "Pays back in month": f"+{crossed.index[0]}" if not crossed.empty else "Not yet",
        })
    st.caption("Latest eight cohorts")
    st.dataframe(
        pd.DataFrame(rows).tail(8),
        hide_index=True,
        width="stretch",
        column_config={"Latest LTV": st.column_config.NumberColumn(format="₹%.0f")},
    )

st.subheader("Time between orders")
intervals = cohorts.calculate_purchase_intervals(orders)
if intervals.empty:
    st.info("No repeat orders in the current selection.")
else:
    st.write(
        f"Repeat customers come back after {intervals['days_between'].mean():.0f} days on average "
        f"(median {intervals['days_between'].median():.0f} days)."
    )
    left, right = st.columns([2, 1])
    with left:
        st.plotly_chart(charts.interval_histogram(intervals), width="stretch")
    with right:
        numbered = orders.sort_values(["customer_id", "order_date", "order_id"]).copy()
        position = numbered.groupby("customer_id").cumcount() + 1
        numbered["order_sequence"] = position.map(lambda n: f"Order {n}" if n <= 4 else "Order 5+")
        sequence_stats = numbered.groupby("order_sequence")["order_value"].mean().reset_index(name="avg_value")
        st.plotly_chart(charts.order_sequence_chart(sequence_stats), width="stretch")

st.subheader("Customer explorer")
summary = cohorts.calculate_customer_summary(orders, customers)
summary = summary[summary["order_count"] > 0]
left, right = st.columns([2, 1])
search = left.text_input("Search by name or customer id")
loyalty = right.selectbox("Customers", ["All", "Repeat buyers", "One-time buyers"])
if loyalty == "Repeat buyers":
    summary = summary[summary["is_repeat"]]
elif loyalty == "One-time buyers":
    summary = summary[~summary["is_repeat"]]
if search:
    query = search.strip().lower()
    summary = summary[
        summary["customer_name"].str.lower().str.contains(query, regex=False)
        | summary["customer_id"].astype(str).str.contains(query, regex=False)
    ]

st.write(f"{len(summary):,} customers")
st.dataframe(
    summary[["customer_id", "customer_name", "segment", "signup_date", "order_count", "items_bought",
             "total_spend", "aov", "first_order", "last_order"]],
    hide_index=True,
    width="stretch",
    column_config={
        "segment": "Channel",
        "total_spend": st.column_config.NumberColumn(format="₹%.0f"),
        "aov": st.column_config.NumberColumn("Avg order", format="₹%.0f"),
        "signup_date": st.column_config.DateColumn(),
        "first_order": st.column_config.DateColumn(),
        "last_order": st.column_config.DateColumn(),
    },
)

if not summary.empty:
    names = summary.set_index("customer_id")["customer_name"]
    chosen = st.selectbox(
        "Order history for", names.index.tolist()[:500], format_func=lambda cid: f"{cid} - {names[cid]}"
    )
    history = pd.merge(orders[orders["customer_id"] == chosen], tables.products, on="product_id", how="left")
    history = history.sort_values("order_date", ascending=False)
    st.dataframe(
        history[["order_id", "order_date", "product_name", "category", "quantity", "price", "order_value"]],
        hide_index=True,
        width="stretch",
        column_config={
            "order_date": st.column_config.DateColumn(),
            "price": st.column_config.NumberColumn(format="₹%.0f"),
            "order_value": st.column_config.NumberColumn(format="₹%.0f"),
        },
    )
