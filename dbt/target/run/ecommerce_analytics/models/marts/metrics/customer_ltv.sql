
  
    

    create or replace table `genai-copilot-enterprisedata`.`metrics`.`customer_ltv`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- customer_ltv.sql
-- ============================================================================
-- Customer lifetime value summary for BI dashboards.
-- Flat, wide table of high-value customers with all key dimensions.
--
-- Grain: one row per customer_id (only customers with ≥ 1 order)
-- Depends on: dim_customers
-- ============================================================================

select
    -- Identity
    customer_id,
    full_name,
    email,

    -- Geography
    city_name,
    state_name,
    home_locality,

    -- Subscription
    is_pass_member,

    -- Lifecycle
    signup_date,
    days_since_signup,
    first_order_date,
    last_order_date,
    days_since_last_order,
    customer_tenure_days,

    -- Segmentation
    rfm_segment,
    value_tier,
    churn_risk_tier,

    -- Activity
    total_orders,
    avg_basket_size,
    preferred_payment_method,
    preferred_platform,

    -- Financials (INR)
    lifetime_revenue,
    lifetime_net_revenue,
    avg_order_value,
    avg_discount_pct,

    -- Delivery experience
    avg_delivery_minutes,
    on_time_pct,

    -- Quality
    orders_with_issues,
    issue_rate_pct,
    cancelled_orders,
    cancellation_rate_pct,

    -- RFM scores
    recency_score,
    frequency_score,
    monetary_score,
    orders_last_30d,
    active_days_last_30d

from `genai-copilot-enterprisedata`.`marts`.`dim_customers`
where total_orders > 0
order by lifetime_revenue desc
    );
  