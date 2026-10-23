# Thread & Trend

Thread & Trend is a Streamlit dashboard for an online fashion store. It started as a cohort and lifetime value dashboard. I added sales forecasting and customer segmentation so it also covers the machine learning side of data work.

## Why I built it

I wanted one project that goes from raw orders in MySQL to a forecast and to customer groups, with the numbers checked properly. I also wanted the dashboard to be usable by someone who does not read Python.

## What it does

- Overview: revenue, orders, average order value, repeat rate, monthly trend, category share and top products.
- Cohorts and Retention: a retention heatmap by signup month.
- Customer Value: lifetime value per cohort against a target acquisition cost, time between orders, and a customer explorer.
- Sales Forecast: monthly revenue for the whole store or one category, forecast up to 12 months, with a backtest table that compares four models.
- Customer Segments: recency, frequency and monetary features, K-Means groups, a PCA plot, a segment table and a CSV download with the label for every customer.
- SQL and Exports: run the reference queries (they work on MySQL and on the CSV files) and download the three tables for Power BI.

The sidebar has filters for sales channel, category and order dates. The caption under the filters says which pages use which filter.

## The data

The data is simulated. `generate_data.py` creates 6,000 customers and about 16,500 orders from June 2023 to May 2026, using a fixed seed. Orders have a yearly pattern (a festive peak in October to December, slow months in June and July), a mild upward trend and random noise. Customers are drawn from five behaviour types (one-time, occasional, loyal, big spender, lapsed), so the segments have something real to find.

Because I built the pattern myself, the forecasts look easier than they would on real shop data. Real data has promotions, stock problems, price changes and sudden shifts that I did not simulate. Treat the error numbers as a check that the code works, not as a promise about a real business.

## How to run it

You need Python 3.11 to 3.13.

```bash
pip install -r requirements.txt
python generate_data.py
python -m streamlit run app.py
```

If MySQL is not reachable, the app says so and shows a button to use the CSV files in the `data` folder. To skip that screen, set `DATA_SOURCE=csv` in your `.env` file.

To use MySQL, run `data/setup_mysql.sql` to create and fill the `ecommerce_analytics` database. Then copy `.env.example` to `.env` and fill in your settings. You can also put them in `.streamlit/secrets.toml` under a `[mysql]` section with the keys `host`, `port`, `user`, `password` and `database`.

To rebuild the report files:

```bash
python make_reports.py
```

## Folders

- `app.py`: sidebar navigation and filters.
- `pages/`: one file per page.
- `src/data`: loading from MySQL or CSV, filters, cohort calculations, SQL runner and the reference queries.
- `src/forecasting`: monthly series, the four models, backtest and forecast ranges.
- `src/segmentation`: RFM features and K-Means.
- `src/plots`: all Plotly charts.
- `data`: the CSV files and the MySQL setup script.
- `reports`: `metrics.json` and two CSV tables written by `make_reports.py`.

## Sales forecasting

I forecast monthly revenue with four models:

1. Same month last year (the baseline).
2. Holt-Winters with a damped trend and multiplicative seasonality.
3. SARIMA(1,1,1)(0,1,1,12) on log revenue.
4. Ridge regression on lag features (1, 2 and 12 months back) plus month and time features, forecast one month at a time.

I test them with rolling-origin backtesting. The model is fitted on the months up to a cut-off, predicts the next 6 months, then the cut-off moves forward one month and it starts again. There are 7 cut-offs, so the test months run from June 2025 to May 2026. A model never sees data after its cut-off. A test checks this.

The forecast range is the middle 80% of the relative errors that the chosen model made in the backtest. It has the same relative width for every month, so far-away months are probably less certain than the range shows.

### Backtest results, whole store

| Model | MAE (INR) | RMSE (INR) | MAPE % | Beats baseline on RMSE |
|---|---|---|---|---|
| Same month last year | 397,215 | 495,015 | 15.9 | - |
| Holt-Winters | 321,966 | 417,354 | 14.3 | Yes |
| SARIMA | 424,017 | 508,663 | 18.6 | No |
| Ridge with lags | 324,149 | 403,400 | 13.8 | Yes |

Ridge with lags had the lowest RMSE for the whole store, about 18.5% lower than the baseline. Holt-Winters was 15.7% lower. SARIMA did not beat the baseline for any series. With only 24 to 30 months of training data it probably has too little to learn from. The best model changes by category: Holt-Winters won in Accessories, Menswear and Womenswear, and Ridge won in Footwear. Footwear is the clearest case where Holt-Winters and SARIMA lost to the baseline. The full table for every category is in `reports/backtest_table.csv`.

I picked the model setups before looking at results, but I did fix one thing after seeing them. My first SARIMA settings gave one unstable fit in Menswear that predicted ten times too high, so I switched to the default stationarity checks.

## Customer segmentation

For each customer I calculate recency (days since the last order), frequency (number of orders) and monetary value (total spend). I take the log of these and standardise them, because a few customers spend far more than the rest. Then I run K-Means.

Choosing k: the silhouette score is highest at k=2 (0.47), but two groups only split active customers from lapsed ones, so I look from k=3 upwards. There the best silhouette is k=3 (0.44). The elbow plot bends at k=4. They are close but not the same, and the page lets you move the slider to compare. The default is 3. I made the "start from 3" rule after seeing the k=2 result.

Segments are named from their average numbers, using simple rules in `src/segmentation/clustering.py`.

| Segment | Customers | Share of customers | Average spend (INR) | Average orders | Days since last order | Share of revenue |
|---|---|---|---|---|---|---|
| Loyal | 1,522 | 25.4% | 27,185 | 6.92 | 324 | 67.5% |
| Occasional | 863 | 14.4% | 6,156 | 1.67 | 55 | 8.7% |
| Lapsed | 3,615 | 60.3% | 4,037 | 1.25 | 589 | 23.8% |

Stability: I reran K-Means with 10 different random seeds. The groups matched the first run with an adjusted Rand index of 0.997 on average and 0.994 at worst. The two PCA components keep 94% of the variation.

## Limits

- The data is simulated, so the forecast errors are optimistic.
- The history is only 36 months, which is short for seasonal models. The backtest covers 12 months of test data.
- The prediction range comes from a handful of backtest errors and the same range is used for every month.
- SARIMA and Holt-Winters settings were not tuned.
- The segments depend on how I simulated customer behaviour. On real data the groups would be less clean.
- The segment names come from rules on averages, so they are a label for a human to check, not a finding.
- Only revenue is forecast. There is no price, promotion or stock information.
- The date filter does not apply to cohort, forecast or segment pages, because those need the full history.

## What I fixed from the first version

- Two of the four reference SQL queries failed on the CSV data because SQLite has no `YEAR` or `MONTH` function. They now work.
- Retention percentages used the number of customers who ordered in their first month as the cohort size. They now use the number of signups.
- Lifetime value lines stayed flat after the data ended. Those months are now left blank.
- The old page text had fixed claims such as customer counts and marketing lines. The numbers now come from the data.
