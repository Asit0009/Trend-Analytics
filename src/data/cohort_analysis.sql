use ecommerce_analytics;

-- [QUERY_START: retention_matrix]
with cohort_sizes as (
    select 
        date_format(c.signup_date, '%Y-%m') as cohort_month,
        count(distinct c.customer_id) as cohort_size
    from customers c
    group by date_format(c.signup_date, '%Y-%m')
),
customer_activities as (
    select distinct
        o.customer_id,
        date_format(c.signup_date, '%Y-%m') as cohort_month,
        (year(o.order_date) - year(c.signup_date)) * 12 + 
        (month(o.order_date) - month(c.signup_date)) as month_index
    from orders o
    join customers c on o.customer_id = c.customer_id
)
select 
    ca.cohort_month,
    cs.cohort_size,
    ca.month_index,
    count(distinct ca.customer_id) as active_shoppers,
    round(count(distinct ca.customer_id) * 100.0 / cs.cohort_size, 2) as retention_rate
from customer_activities ca
join cohort_sizes cs on ca.cohort_month = cs.cohort_month
group by ca.cohort_month, cs.cohort_size, ca.month_index
order by ca.cohort_month, ca.month_index;
-- [QUERY_END: retention_matrix]


-- [QUERY_START: cohort_ltv]
with cohort_sizes as (
    select 
        date_format(c.signup_date, '%Y-%m') as cohort_month,
        count(distinct c.customer_id) as cohort_size
    from customers c
    group by date_format(c.signup_date, '%Y-%m')
),
monthly_spend as (
    select 
        o.customer_id,
        date_format(c.signup_date, '%Y-%m') as cohort_month,
        (year(o.order_date) - year(c.signup_date)) * 12 + 
        (month(o.order_date) - month(c.signup_date)) as month_index,
        sum(o.order_value) as total_spend
    from orders o
    join customers c on o.customer_id = c.customer_id
    group by o.customer_id, cohort_month, month_index
),
cohort_monthly_spend as (
    select 
        cohort_month,
        month_index,
        sum(total_spend) as cohort_spend
    from monthly_spend
    group by cohort_month, month_index
)
select 
    cms.cohort_month,
    cs.cohort_size,
    cms.month_index,
    round(sum(cms.cohort_spend) over (
        partition by cms.cohort_month 
        order by cms.month_index
    ) / cs.cohort_size, 2) as average_ltv_inr
from cohort_monthly_spend cms
join cohort_sizes cs on cms.cohort_month = cs.cohort_month
order by cms.cohort_month, cms.month_index;
-- [QUERY_END: cohort_ltv]


-- [QUERY_START: repeat_intervals]
with order_history as (
    select 
        order_id,
        customer_id,
        order_date,
        lag(order_date) over (
            partition by customer_id 
            order by order_date, order_id
        ) as previous_order_date
    from orders
),
order_intervals as (
    select 
        customer_id,
        datediff(order_date, previous_order_date) as days_since_last_order
    from order_history
    where previous_order_date is not null
)
select 
    customer_id,
    count(*) as total_repeat_orders,
    round(avg(days_since_last_order), 1) as avg_days_between
from order_intervals
group by customer_id
order by total_repeat_orders desc
limit 20;
-- [QUERY_END: repeat_intervals]


-- [QUERY_START: dense_rank_orders]
with ranked_orders as (
    select 
        o.order_id,
        o.customer_id,
        o.order_value,
        dense_rank() over (
            partition by o.customer_id 
            order by o.order_date, o.order_id
        ) as purchase_sequence
    from orders o
)
select 
    purchase_sequence,
    count(order_id) as total_orders,
    round(avg(order_value), 2) as average_order_value_inr
from ranked_orders
where purchase_sequence <= 5
group by purchase_sequence
order by purchase_sequence;
-- [QUERY_END: dense_rank_orders]
