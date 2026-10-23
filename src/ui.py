import os
from collections import namedtuple

import streamlit as st

from src.data import loader
from src.data.filters import apply_filters

Tables = namedtuple("Tables", ["customers", "products", "orders"])

CHANNELS_KEY = "filter_channels"
CATEGORIES_KEY = "filter_categories"
DATES_KEY = "filter_dates"
SOURCE_KEY = "data_source"
ROUTER_KEY = "router_started"
SOURCE_LABELS = {"mysql": "MySQL database", "csv": "CSV files in the data folder"}


def secret_settings():
    try:
        return dict(st.secrets["mysql"])
    except Exception:
        return {}


@st.cache_data(show_spinner="Reading data from MySQL...", ttl=600)
def read_mysql(settings_items):
    return loader.load_from_mysql(dict(settings_items))


@st.cache_data(show_spinner="Reading the CSV files...")
def read_csv_files():
    return loader.load_from_csv()


def try_mysql():
    settings = loader.get_db_settings(secret_settings())
    if settings is None:
        return None, "No database settings found. Add them to a .env file or to .streamlit/secrets.toml."
    try:
        return read_mysql(tuple(sorted(settings.items()))), None
    except Exception as error:
        return None, f"Could not reach MySQL: {error}"


def choose_source():
    if st.session_state.get(SOURCE_KEY):
        return st.session_state[SOURCE_KEY]
    if os.getenv("DATA_SOURCE", "").lower() == "csv":
        st.session_state[SOURCE_KEY] = "csv"
        return "csv"
    tables, problem = try_mysql()
    if tables is not None:
        st.session_state[SOURCE_KEY] = "mysql"
        return "mysql"
    st.title("Thread & Trend")
    st.error(problem)
    st.write("The dashboard can run on the CSV files in the data folder instead.")
    if st.button("Use the CSV files", type="primary"):
        st.session_state[SOURCE_KEY] = "csv"
        st.rerun()
    st.stop()


def load_raw_tables():
    source = choose_source()
    try:
        if source == "mysql":
            tables, problem = try_mysql()
            if tables is None:
                raise RuntimeError(problem)
            return Tables(*tables), source
        return Tables(*read_csv_files()), source
    except Exception as error:
        st.session_state[SOURCE_KEY] = None
        st.error(f"Could not load the data: {error}")
        st.stop()


def render_sidebar():
    tables, source = load_raw_tables()
    with st.sidebar:
        st.caption(f"Data source: {SOURCE_LABELS[source]}")
        if source == "mysql":
            if st.button("Switch to CSV files"):
                st.session_state[SOURCE_KEY] = "csv"
                st.rerun()
        elif st.button("Try MySQL again"):
            st.session_state[SOURCE_KEY] = None
            st.cache_data.clear()
            st.rerun()

        st.subheader("Filters")
        channels = sorted(tables.customers["segment"].dropna().unique())
        categories = sorted(tables.products["category"].dropna().unique())
        first_day = tables.orders["order_date"].min().date()
        last_day = tables.orders["order_date"].max().date()
        st.multiselect("Sales channel", channels, default=channels, key=CHANNELS_KEY)
        st.multiselect("Category", categories, default=categories, key=CATEGORIES_KEY)
        st.date_input(
            "Order dates", value=(first_day, last_day), min_value=first_day, max_value=last_day, key=DATES_KEY
        )
        st.caption(
            "Overview uses all three filters. Cohorts and Customer Value use channel and category. "
            "Forecast and Segments use channel."
        )


def require_router():
    if not st.session_state.get(ROUTER_KEY):
        st.switch_page("app.py")


def selected_dates():
    chosen = st.session_state.get(DATES_KEY)
    if isinstance(chosen, (tuple, list)) and len(chosen) == 2:
        return chosen[0], chosen[1]
    return None, None


def page_tables(use_categories=False, use_dates=False):
    raw, _ = load_raw_tables()
    channels = st.session_state.get(CHANNELS_KEY)
    categories = st.session_state.get(CATEGORIES_KEY) if use_categories else None
    start, end = selected_dates() if use_dates else (None, None)
    customers, products, orders = apply_filters(
        raw.customers, raw.products, raw.orders, channels, categories, start, end
    )
    if orders.empty:
        st.warning("No orders match the current filters. Widen the filters in the sidebar.")
        st.stop()
    return Tables(customers, products, orders)


def all_tables():
    raw, _ = load_raw_tables()
    return raw


def money(value):
    return f"₹{value:,.0f}"


def money_short(value):
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    return f"₹{value:,.0f}"
