
  
    

    create or replace table `genai-copilot-enterprisedata`.`marts`.`dim_delivery_partners`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- dim_delivery_partners.sql
-- ============================================================================
-- Rider / delivery partner dimension with performance metrics.
-- Quick-commerce specific: delivery speed, on-time %, issue exposure.
--
-- Grain: one row per rider_id
-- Depends on: stg_delivery_partners, stg_orders, stg_dark_stores
-- ============================================================================

with riders as (
    select * from `genai-copilot-enterprisedata`.`staging`.`stg_delivery_partners`
),

stores as (
    select
        store_id,
        city_name   as store_city,
        locality    as store_locality
    from `genai-copilot-enterprisedata`.`staging`.`stg_dark_stores`
),

-- ── Rider delivery performance ──────────────────────────────────────────────
rider_orders as (
    select
        rider_id,
        count(distinct order_id)                        as total_deliveries,
        round(avg(actual_delivery_minutes), 1)          as avg_delivery_minutes,
        round(safe_divide(
            countif(is_on_time),
            nullif(count(distinct order_id), 0)
        ), 4)                                           as on_time_pct,
        round(sum(revenue), 2)                          as total_order_revenue,
        min(order_date)                                 as first_delivery_date,
        max(order_date)                                 as last_delivery_date,
        date_diff(max(order_date), min(order_date), day)
                                                        as active_span_days,
        -- Average deliveries per active day
        round(safe_divide(
            count(distinct order_id),
            nullif(count(distinct order_date), 0)
        ), 1)                                           as avg_deliveries_per_day
    from `genai-copilot-enterprisedata`.`staging`.`stg_orders`
    where order_status = 'DELIVERED'
      and rider_id is not null
      and rider_id != ''
    group by rider_id
),

final as (
    select
        -- ── Key ─────────────────────────────────────────────────────────────
        to_hex(md5(cast(coalesce(cast(r.rider_id as string), '_dbt_utils_surrogate_key_null_') as string)))
                                                        as rider_sk,
        r.rider_id,

        -- ── Personal ────────────────────────────────────────────────────────
        r.full_name,
        r.first_name,
        r.last_name,

        -- ── Assignment ──────────────────────────────────────────────────────
        r.home_store_id,
        s.store_city,
        s.store_locality,
        r.city_name                                     as rider_city,
        r.vehicle_type,

        -- ── Tenure ──────────────────────────────────────────────────────────
        r.join_date,
        r.days_since_join,

        -- ── Delivery performance ────────────────────────────────────────────
        coalesce(ro.total_deliveries, 0)                as total_deliveries,
        ro.avg_delivery_minutes,
        coalesce(ro.on_time_pct, 0)                     as on_time_pct,
        coalesce(ro.total_order_revenue, 0)             as total_order_revenue,
        coalesce(ro.avg_deliveries_per_day, 0)          as avg_deliveries_per_day,
        ro.first_delivery_date,
        ro.last_delivery_date,

        -- ── Performance labels ──────────────────────────────────────────────
        case
            when coalesce(ro.on_time_pct, 0) >= 90 then 'Excellent'
            when coalesce(ro.on_time_pct, 0) >= 75 then 'Good'
            when coalesce(ro.on_time_pct, 0) >= 60 then 'Average'
            else 'Needs Training'
        end                                             as performance_tier,

        case
            when coalesce(ro.total_deliveries, 0) >= 500 then 'Veteran'
            when coalesce(ro.total_deliveries, 0) >= 100 then 'Experienced'
            when coalesce(ro.total_deliveries, 0) >= 10  then 'Active'
            when coalesce(ro.total_deliveries, 0) > 0    then 'New'
            else 'Inactive'
        end                                             as experience_tier

    from riders r
    left join stores       s  on r.home_store_id = s.store_id
    left join rider_orders ro on r.rider_id      = ro.rider_id
)

select * from final
    );
  