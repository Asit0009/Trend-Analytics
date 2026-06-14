# Thread & Trend - Customer Cohort Analytics

A customer analytics dashboard made with Python, Streamlit and MySQL to analyse customer retention, lifetime value (LTV) and repeat orders for an online clothing store.

## Requirements
```bash
pip install pandas numpy plotly streamlit mysql-connector-python
```

## How to run

1. Open MySQL Workbench and run `setup_mysql.sql` to create database and insert data.
2. Run streamlit:
   ```bash
   streamlit run app.py
   ```
3. Enter your MySQL password on login page and click Connect.

## Files
- `app.py`: main streamlit dashboard code
- `cohort_analytics.py`: functions for cohort retention and ltv
- `cohort_analysis.sql`: sql queries (window functions, ctes)
- `setup_mysql.sql`: database table schema and dataset
- `dim_customers.csv`, `dim_products.csv`, `fact_orders.csv`: data files for power bi