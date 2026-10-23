import pytest
from streamlit.testing.v1 import AppTest

from src import ui

PAGES = [
    "pages/overview.py",
    "pages/cohorts.py",
    "pages/customer_value.py",
    "pages/sales_forecast.py",
    "pages/customer_segments.py",
    "pages/sql_and_exports.py",
]


@pytest.fixture
def no_database(monkeypatch):
    for key in ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        monkeypatch.delenv(key, raising=False)


def start_app():
    app = AppTest.from_file("app.py", default_timeout=240)
    app.session_state[ui.SOURCE_KEY] = "csv"
    app.run()
    return app


def metric_value(app, label):
    return next(metric.value for metric in app.metric if metric.label == label)


def sidebar_box(app, label):
    return next(box for box in app.sidebar.multiselect if box.label == label)


def test_app_offers_csv_button_when_database_is_missing(no_database):
    app = AppTest.from_file("app.py", default_timeout=60).run()
    assert not app.exception
    assert len(app.error) == 1
    assert [button.label for button in app.button] == ["Use the CSV files"]
    app.button[0].click().run()
    assert not app.exception
    assert len(app.metric) == 6


def test_unreachable_database_falls_back_to_csv_button(monkeypatch):
    monkeypatch.setenv("DB_USER", "nobody")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "1")
    app = AppTest.from_file("app.py", default_timeout=60).run()
    assert not app.exception
    assert "Could not reach MySQL" in app.error[0].value
    app.button[0].click().run()
    assert not app.exception
    assert len(app.metric) == 6


@pytest.mark.parametrize("page", PAGES)
def test_every_page_loads_without_errors(no_database, page):
    app = start_app()
    app.switch_page(page).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    assert len(app.title) == 1


def test_channel_filter_changes_the_numbers(no_database):
    app = start_app()
    before = metric_value(app, "Orders")
    sidebar_box(app, "Sales channel").set_value(["Direct"]).run()
    after = metric_value(app, "Orders")
    assert not app.exception
    assert int(after.replace(",", "")) < int(before.replace(",", ""))


def test_category_filter_changes_the_revenue(no_database):
    app = start_app()
    before = metric_value(app, "Revenue")
    sidebar_box(app, "Category").set_value(["Footwear"]).run()
    assert metric_value(app, "Revenue") != before


def test_emptying_a_filter_shows_a_warning_not_a_crash(no_database):
    app = start_app()
    sidebar_box(app, "Sales channel").set_value([]).run()
    assert not app.exception
    assert len(app.warning) == 1


def test_forecast_page_controls(no_database):
    app = start_app()
    app.switch_page("pages/sales_forecast.py").run()
    next(box for box in app.selectbox if box.label == "Category").select("Footwear").run()
    next(slider for slider in app.slider if slider.label == "Months to forecast").set_value(9).run()
    assert not app.exception
    assert len(app.dataframe) >= 2


def test_segment_slider_changes_the_segment_count(no_database):
    app = start_app()
    app.switch_page("pages/customer_segments.py").run()
    app.slider[0].set_value(5).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 5
