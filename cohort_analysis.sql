-- ============================================================================
-- Thread & Trend | Fashion Cohort & Customer Lifecycle Analytics
-- Dialect: MySQL 8.0+ (Tested in MySQL Workbench)
-- ============================================================================

USE ecommerce_analytics;

-- [QUERY_START: retention_matrix]
-- 1. Cohort Retention Matrix (Active Shopper Counts & Percentages)
-- Tracks what percentage of customers acquired in a month return to buy in subsequent months.
WITH cohort_sizes AS (
    SELECT 
        DATE_FORMAT(c.signup_date, '%Y-%m') AS cohort_month,
        COUNT(DISTINCT c.customer_id) AS cohort_size
    FROM customers c
    GROUP BY DATE_FORMAT(c.signup_date, '%Y-%m')
),
customer_activities AS (
    SELECT DISTINCT
        o.customer_id,
        DATE_FORMAT(c.signup_date, '%Y-%m') AS cohort_month,
        (YEAR(o.order_date) - YEAR(c.signup_date)) * 12 + 
        (MONTH(o.order_date) - MONTH(c.signup_date)) AS month_index
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
)
SELECT 
    ca.cohort_month,
    cs.cohort_size,
    ca.month_index,
    COUNT(DISTINCT ca.customer_id) AS active_shoppers,
    ROUND(COUNT(DISTINCT ca.customer_id) * 100.0 / cs.cohort_size, 2) AS retention_rate
FROM customer_activities ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
GROUP BY ca.cohort_month, cs.cohort_size, ca.month_index
ORDER BY ca.cohort_month, ca.month_index;
-- [QUERY_END: retention_matrix]


-- [QUERY_START: cohort_ltv]
-- 2. Customer Cohort Cumulative Lifetime Value (LTV)
-- Tracks the average cumulative spend of a customer over time per signup cohort.
WITH cohort_sizes AS (
    SELECT 
        DATE_FORMAT(c.signup_date, '%Y-%m') AS cohort_month,
        COUNT(DISTINCT c.customer_id) AS cohort_size
    FROM customers c
    GROUP BY DATE_FORMAT(c.signup_date, '%Y-%m')
),
monthly_spend AS (
    SELECT 
        o.customer_id,
        DATE_FORMAT(c.signup_date, '%Y-%m') AS cohort_month,
        (YEAR(o.order_date) - YEAR(c.signup_date)) * 12 + 
        (MONTH(o.order_date) - MONTH(c.signup_date)) AS month_index,
        SUM(o.order_value) AS total_spend
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY o.customer_id, cohort_month, month_index
),
cohort_monthly_spend AS (
    SELECT 
        cohort_month,
        month_index,
        SUM(total_spend) AS cohort_spend
    FROM monthly_spend
    GROUP BY cohort_month, month_index
)
SELECT 
    cms.cohort_month,
    cs.cohort_size,
    cms.month_index,
    ROUND(SUM(cms.cohort_spend) OVER (
        PARTITION BY cms.cohort_month 
        ORDER BY cms.month_index
    ) / cs.cohort_size, 2) AS average_ltv_inr
FROM cohort_monthly_spend cms
JOIN cohort_sizes cs ON cms.cohort_month = cs.cohort_month
ORDER BY cms.cohort_month, cms.month_index;
-- [QUERY_END: cohort_ltv]


-- [QUERY_START: repeat_intervals]
-- 3. Customer Purchase Interval Analysis (Window Functions: LAG)
-- Analyzes repurchase latency (days between orders) for repeat buyers.
WITH order_history AS (
    SELECT 
        order_id,
        customer_id,
        order_date,
        LAG(order_date) OVER (
            PARTITION BY customer_id 
            ORDER BY order_date, order_id
        ) AS previous_order_date
    FROM orders
),
order_intervals AS (
    SELECT 
        customer_id,
        DATEDIFF(order_date, previous_order_date) AS days_since_last_order
    FROM order_history
    WHERE previous_order_date IS NOT NULL
)
SELECT 
    customer_id,
    COUNT(*) AS total_repeat_orders,
    ROUND(AVG(days_since_last_order), 1) AS avg_days_between
FROM order_intervals
GROUP BY customer_id
ORDER BY total_repeat_orders DESC
LIMIT 20;
-- [QUERY_END: repeat_intervals]


-- [QUERY_START: dense_rank_orders]
-- 4. Customer Purchase Sequence Rank (DENSE_RANK)
-- Ranks each purchase sequence number (1st order, 2nd order) to analyze spending patterns.
WITH ranked_orders AS (
    SELECT 
        o.order_id,
        o.customer_id,
        o.order_value,
        DENSE_RANK() OVER (
            PARTITION BY o.customer_id 
            ORDER BY o.order_date, o.order_id
        ) AS purchase_sequence
    FROM orders o
)
SELECT 
    purchase_sequence,
    COUNT(order_id) AS total_orders,
    ROUND(AVG(order_value), 2) AS average_order_value_inr
FROM ranked_orders
WHERE purchase_sequence <= 5
GROUP BY purchase_sequence
ORDER BY purchase_sequence;
-- [QUERY_END: dense_rank_orders]
