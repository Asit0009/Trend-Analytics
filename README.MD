# Thread & Trend - Customer Cohort and Lifecycle Analytics

An interactive customer cohort retention and lifetime value (LTV) analytics dashboard built for the clothing brand Thread & Trend. The project processes transactional records to track customer loyalty, purchase latency, and customer acquisition cost (CAC) profitability metrics.

The system is built using Streamlit for the front-end dashboard and MySQL for the database engine.

## Project Structure

* app.py - The main Streamlit dashboard application.
* cohort_analytics.py - Calculations module for cohort matrices and transaction metrics.
* cohort_analysis.sql - Reference SQL scripts containing advanced window functions (LAG, DENSE_RANK) and CTEs.
* generate_data.py - Simulated transactional data generator.
* setup_mysql.sql - MySQL setup script containing database schemas and seed records.
* dim_customers.csv, dim_products.csv, fact_orders.csv - Power BI compatible relational tables.

## Setup and Installation

### 1. Database Configuration
1. Open MySQL Workbench and connect to your local MySQL instance.
2. Load and run the setup_mysql.sql script in a query editor tab. This will create the database 'ecommerce_analytics' and seed the tables with simulated fashion retail data.

### 2. Running the Dashboard
Install the required packages and run the Streamlit application:
```bash
pip install pandas numpy plotly streamlit mysql-connector-python
python -B -m streamlit run app.py
```
Open http://localhost:8502 in your web browser, enter your local MySQL password, and click Connect.

### 3. Power BI Integration
Open Power BI Desktop and load the three CSV files from the project folder. Connect them in the Model view:
* dim_customers (customer_id) to fact_orders (customer_id)
* dim_products (product_id) to fact_orders (product_id)

Refer to the Power BI guide inside the Advanced Console expander at the bottom of the Streamlit dashboard for key DAX formulas.