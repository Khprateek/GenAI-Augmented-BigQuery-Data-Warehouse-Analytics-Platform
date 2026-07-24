
  
    

    create or replace table `genai-copilot-enterprisedata`.`metrics`.`marketing_performance`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- marketing_performance.sql
-- ============================================================================
-- Daily marketing spend joined with attributed revenue from delivered orders.
-- Quick-commerce note: orders don't have a "channel" FK, so attribution is
-- done by matching spend_date = order_date at the marketing channel level.
-- This is a simplified last-touch attribution model.
--
-- Grain: one row per (spend_date, channel)
-- Depends on: stg_marketing_spend, stg_orders
-- ============================================================================

with spend as (
    select * from `genai-copilot-enterprisedata`.`staging`.`stg_marketing_spend`
),

-- Daily revenue by date (no channel on orders, so total daily revenue is used)
daily_revenue as (
    select
        order_date,
        count(distinct order_id)                        as total_orders,
        countif(order_status = 'DELIVERED')              as delivered_orders,
        round(sum(case when order_status = 'DELIVERED'
                       then revenue else 0 end), 2)     as delivered_revenue
    from `genai-copilot-enterprisedata`.`staging`.`stg_orders`
    group by order_date
),

-- Total daily spend for proportional attribution
daily_spend_total as (
    select
        spend_date,
        sum(spend_inr)                                  as total_daily_spend
    from spend
    group by spend_date
),

final as (
    select
        -- ── Dimensions ──────────────────────────────────────────────────────
        s.spend_date,
        s.channel,

        -- ── Spend metrics ───────────────────────────────────────────────────
        s.spend_inr,
        s.impressions,
        s.clicks,
        s.app_installs,
        s.cpc_inr,
        s.ctr_pct,

        -- ── Cost per install ────────────────────────────────────────────────
        round(safe_divide(s.spend_inr, nullif(s.app_installs, 0)), 2)
                                                        as cost_per_install,

        -- ── Proportional revenue attribution ────────────────────────────────
        -- Each channel gets a share of daily revenue proportional to its spend
        round(safe_divide(s.spend_inr, dst.total_daily_spend)
              * coalesce(dr.delivered_revenue, 0), 2)   as attributed_revenue,

        round(safe_divide(s.spend_inr, dst.total_daily_spend)
              * coalesce(dr.delivered_orders, 0), 0)    as attributed_orders,

        -- ── Efficiency metrics ──────────────────────────────────────────────
        -- ROAS = attributed revenue / spend
        round(safe_divide(
            safe_divide(s.spend_inr, dst.total_daily_spend)
            * coalesce(dr.delivered_revenue, 0),
            nullif(s.spend_inr, 0)
        ), 2)                                           as roas,

        -- CAC = spend / attributed orders
        round(safe_divide(
            s.spend_inr,
            nullif(
                safe_divide(s.spend_inr, dst.total_daily_spend)
                * coalesce(dr.delivered_orders, 0),
                0
            )
        ), 2)                                           as cac_inr

    from spend s
    left join daily_revenue     dr  on s.spend_date = dr.order_date
    left join daily_spend_total dst on s.spend_date = dst.spend_date
)

select * from final
order by spend_date desc, channel
    );
  