import streamlit as st

from src import ui

st.set_page_config(page_title="Thread & Trend", page_icon="🛍️", layout="wide")

navigation = st.navigation([
    st.Page("pages/overview.py", title="Overview", default=True),
    st.Page("pages/cohorts.py", title="Cohorts and Retention"),
    st.Page("pages/customer_value.py", title="Customer Value"),
    st.Page("pages/sales_forecast.py", title="Sales Forecast"),
    st.Page("pages/customer_segments.py", title="Customer Segments"),
    st.Page("pages/sql_and_exports.py", title="SQL and Exports"),
])

st.session_state[ui.ROUTER_KEY] = True
ui.render_sidebar()
navigation.run()
