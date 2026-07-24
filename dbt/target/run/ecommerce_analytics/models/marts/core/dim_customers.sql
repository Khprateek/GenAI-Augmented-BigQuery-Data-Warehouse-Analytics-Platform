
  
    

    create or replace table `genai-copilot-enterprisedata`.`marts`.`dim_customers`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- dim_customers.sql
-- ============================================================================
-- Customer dimension enriched with RFM segments, lifetime value, delivery
-- experience, churn risk, and Zepto Pass membership.
--
-- Grain: one row per customer_id
-- Depends on: stg_customers, int_customer_orders, int_customer_churn_features
-- ============================================================================

with customers as (
    select * from `genai-copilot-enterprisedata`.`staging`.`stg_customers`
),

customer_stats as (
    select * from `genai-copilot-enterprisedata`.`staging`.`int_customer_orders`
),

churn_features as (
    select
        customer_id,
        churn_risk_tier,
        orders_30d,
        aov_trend,
        active_days_30d
    from `genai-copilot-enterprisedata`.`staging`.`int_customer_churn_features`
),

final as (
    select
        -- ── Key ─────────────────────────────────────────────────────────────
        to_hex(md5(cast(coalesce(cast(c.customer_id as string), '_dbt_utils_surrogate_key_null_') as string)))
                                                        as customer_sk,
        c.customer_id,

        -- ── Personal attributes ─────────────────────────────────────────────
        c.first_name,
        c.last_name,
        concat(c.first_name, ' ', coalesce(c.last_name, ''))
                                                        as full_name,
        c.email,

        -- ── Geography ───────────────────────────────────────────────────────
        c.city_name,
        c.state_name,
        c.home_locality,
        c.home_store_id,

        -- ── Subscription ────────────────────────────────────────────────────
        c.is_pass_member,

        -- ── Lifecycle ───────────────────────────────────────────────────────
        c.signup_date,
        c.days_since_signup,
        cs.first_order_date,
        cs.last_order_date,
        cs.days_since_last_order,
        cs.customer_tenure_days,

        -- ── Order activity ──────────────────────────────────────────────────
        coalesce(cs.total_orders, 0)                    as total_orders,
        coalesce(cs.avg_basket_size, 0)                 as avg_basket_size,
        cs.preferred_payment_method,
        cs.preferred_platform,

        -- ── Financials (INR) ────────────────────────────────────────────────
        coalesce(cs.lifetime_revenue, 0)                as lifetime_revenue,
        coalesce(cs.lifetime_net_revenue, 0)            as lifetime_net_revenue,
        coalesce(cs.avg_order_value, 0)                 as avg_order_value,
        coalesce(cs.avg_discount_pct, 0)                as avg_discount_pct,

        -- ── Delivery experience ─────────────────────────────────────────────
        cs.avg_delivery_minutes,
        coalesce(cs.on_time_pct, 0)                     as on_time_pct,

        -- ── Quality ─────────────────────────────────────────────────────────
        coalesce(cs.orders_with_issues, 0)              as orders_with_issues,
        coalesce(cs.issue_rate_pct, 0)                  as issue_rate_pct,
        coalesce(cs.cancelled_orders, 0)                as cancelled_orders,
        coalesce(cs.cancellation_rate_pct, 0)           as cancellation_rate_pct,

        -- ── RFM scoring ─────────────────────────────────────────────────────
        cs.recency_score,
        cs.frequency_score,
        cs.monetary_score,
        cs.rfm_score,
        coalesce(cs.rfm_segment, 'No Purchases')       as rfm_segment,

        -- ── Churn risk ──────────────────────────────────────────────────────
        coalesce(cf.churn_risk_tier, 'Dormant')         as churn_risk_tier,
        coalesce(cf.orders_30d, 0)                      as orders_last_30d,
        coalesce(cf.active_days_30d, 0)                 as active_days_last_30d,

        -- ── Value tier (INR thresholds for Indian quick-commerce) ───────────
        case
            when coalesce(cs.lifetime_revenue, 0) >= 25000 then 'Platinum'
            when coalesce(cs.lifetime_revenue, 0) >= 10000 then 'Gold'
            when coalesce(cs.lifetime_revenue, 0) >= 3000  then 'Silver'
            when coalesce(cs.lifetime_revenue, 0) > 0      then 'Bronze'
            else 'No Purchase'
        end                                             as value_tier

    from customers c
    left join customer_stats  cs on c.customer_id = cs.customer_id
    left join churn_features  cf on c.customer_id = cf.customer_id
)

select * from final
    );
  