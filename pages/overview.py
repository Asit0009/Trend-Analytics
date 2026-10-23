import pandas as pd
import streamlit as st

from src import ui
from src.plots import charts

ui.require_router()

st.title("Overview")
st.caption("Sales of an online fashion store. The data is simulated.")

tables = ui.page_tables(use_categories=True, use_dates=True)
orders = tables.orders

revenue = float(orders["order_value"].sum())
order_count = int(orders["order_id"].nunique())
buyers = orders.groupby("customer_id")["order_id"].nunique()
repeat_rate = (buyers > 1).mean() * 100

first, second, third = st.columns(3)
first.metric("Revenue", ui.money_short(revenue), help=ui.money(revenue))
second.metric("Orders", f"{order_count:,}")
third.metric("Customers who ordered", f"{len(buyers):,}")
fourth, fifth, sixth = st.columns(3)
fourth.metric("Average order value", ui.money(revenue / order_count))
fifth.metric("Repeat customer rate", f"{repeat_rate:.1f}%")
sixth.metric("Items per order", f"{orders['quantity'].mean():.2f}")

monthly = (
    orders.assign(month=orders["order_date"].dt.to_period("M").dt.to_timestamp())
    .groupby("month")
    .agg(revenue=("order_value", "sum"), orders=("order_id", "nunique"))
    .reset_index()
)

left, right = st.columns([1.7, 1])
with left:
    st.subheader("Monthly revenue and orders")
    st.plotly_chart(charts.monthly_revenue_chart(monthly), width="stretch")
with right:
    st.subheader("Revenue by category")
    with_category = pd.merge(orders, tables.products, on="product_id")
    category_revenue = with_category.groupby("category")["order_value"].sum().reset_index()
    st.plotly_chart(charts.category_share_chart(category_revenue), width="stretch")

product_sales = (
    with_category.groupby(["product_id", "product_name", "category", "price"])
    .agg(units_sold=("quantity", "sum"), revenue=("order_value", "sum"), orders=("order_id", "nunique"))
    .reset_index()
    .sort_values("revenue", ascending=False)
)

left, right = st.columns([1.4, 1])
with left:
    st.subheader("Top products")
    st.plotly_chart(charts.top_products_chart(product_sales.head(8)), width="stretch")
with right:
    st.subheader("Items per order")
    basket = orders.groupby("order_id")["quantity"].sum().value_counts().sort_index().reset_index()
    basket.columns = ["items_in_order", "total_orders"]
    st.plotly_chart(charts.basket_chart(basket), width="stretch")

with st.expander("All products"):
    st.dataframe(
        product_sales[["product_id", "product_name", "category", "price", "units_sold", "orders", "revenue"]],
        hide_index=True,
        width="stretch",
        column_config={
            "price": st.column_config.NumberColumn(format="₹%.0f"),
            "revenue": st.column_config.NumberColumn(format="₹%.0f"),
        },
    )
