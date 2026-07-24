
  
    

    create or replace table `genai-copilot-enterprisedata`.`metrics`.`revenue_daily`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- revenue_daily.sql
-- ============================================================================
-- Pre-aggregated daily revenue & operations metrics.
-- Streamlit / BI dashboards query this instead of the raw fact table.
--
-- Grain: one row per (order_date, store_city, platform, customer_type)
-- Depends on: fact_orders
-- ============================================================================

with fact as (
    select * from `genai-copilot-enterprisedata`.`marts`.`fact_orders`
),

daily as (
    select
        -- ── Dimensions ──────────────────────────────────────────────────────
        order_date,
        order_year,
        order_month,
        order_week,
        order_hour,

        customer_state,
        customer_city,
        store_city,
        store_locality,
        platform,
        payment_method,
        customer_type,
        is_pass_member,

        -- ── Order counts ────────────────────────────────────────────────────
        count(distinct order_id)                            as total_orders,
        count(distinct case when is_delivered = 1
                            then order_id end)              as delivered_orders,
        sum(is_cancelled)                                   as cancelled_orders,
        sum(is_failed_delivery)                             as failed_deliveries,

        -- ── Customer activity ───────────────────────────────────────────────
        count(distinct customer_sk)                         as unique_customers,

        -- ── Financials (INR) ────────────────────────────────────────────────
        round(sum(case when is_delivered = 1
                       then revenue else 0 end), 2)         as gross_revenue,
        round(sum(case when is_delivered = 1
                       then discount else 0 end), 2)        as total_discount,
        round(sum(case when is_delivered = 1
                       then delivery_fee else 0 end), 2)    as total_delivery_fees,
        round(sum(case when is_delivered = 1
                       then refund_amount else 0 end), 2)   as total_refunds,
        round(sum(case when is_delivered = 1
                       then net_revenue else 0 end), 2)     as net_revenue,

        -- ── Basket ──────────────────────────────────────────────────────────
        sum(total_items)                                    as total_items_sold,
        round(safe_divide(
            sum(total_items),
            nullif(count(distinct case when is_delivered = 1
                                      then order_id end), 0)
        ), 1)                                               as avg_basket_size,

        -- ── AOV ─────────────────────────────────────────────────────────────
        round(safe_divide(
            sum(case when is_delivered = 1 then revenue else 0 end),
            nullif(count(distinct case when is_delivered = 1
                                      then order_id end), 0)
        ), 2)                                               as avg_order_value,

        -- ── Delivery performance ────────────────────────────────────────────
        round(avg(case when is_delivered = 1
                       then actual_delivery_minutes end), 1)
                                                            as avg_delivery_minutes,
        round(safe_divide(
            countif(is_delivered = 1 and is_on_time),
            nullif(countif(is_delivered = 1), 0)
        ), 4)                                               as on_time_pct,

        -- ── Fulfilment rate ─────────────────────────────────────────────────
        round(safe_divide(
            count(distinct case when is_delivered = 1 then order_id end),
            nullif(count(distinct order_id), 0)
        ), 4)                                               as fulfilment_rate_pct,

        -- ── Issues ──────────────────────────────────────────────────────────
        countif(has_order_issue)                             as orders_with_issues,
        sum(issue_count)                                    as total_issues

    from fact
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
)

select * from daily
    );
  