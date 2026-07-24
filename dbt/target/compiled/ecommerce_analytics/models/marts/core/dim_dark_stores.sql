-- ============================================================================
-- dim_dark_stores.sql
-- ============================================================================
-- Dark store (micro-fulfilment center) dimension.
-- One row per store with geography, capacity, rider count, and order volume.
--
-- Grain: one row per store_id
-- Depends on: stg_dark_stores, stg_delivery_partners, stg_orders
-- ============================================================================

with stores as (
    select * from `genai-copilot-enterprisedata`.`staging`.`stg_dark_stores`
),

-- ── Rider headcount per store ───────────────────────────────────────────────
rider_stats as (
    select
        home_store_id                               as store_id,
        count(distinct rider_id)                    as total_riders,
        countif(vehicle_type = 'Electric Scooter')  as electric_scooter_riders,
        countif(vehicle_type = 'Bike')              as bike_riders,
        countif(vehicle_type = 'Bicycle')           as bicycle_riders
    from `genai-copilot-enterprisedata`.`staging`.`stg_delivery_partners`
    group by home_store_id
),

-- ── Order volume per store ──────────────────────────────────────────────────
order_stats as (
    select
        store_id,
        count(distinct order_id)                    as total_orders,
        percent_rank() over (order by count(distinct order_id) desc) as volume_percentile,
        countif(order_status = 'DELIVERED')          as delivered_orders,
        countif(order_status = 'CANCELLED')          as cancelled_orders,
        round(avg(case when order_status = 'DELIVERED'
                       then actual_delivery_minutes end), 1)
                                                    as avg_delivery_minutes,
        round(safe_divide(
            countif(order_status = 'DELIVERED' and is_on_time),
            nullif(countif(order_status = 'DELIVERED'), 0)
        ), 4)                                       as on_time_pct,
        round(sum(revenue), 2)                      as total_revenue,
        min(order_date)                             as first_order_date,
        max(order_date)                             as last_order_date
    from `genai-copilot-enterprisedata`.`staging`.`stg_orders`
    group by store_id
),

final as (
    select
        -- ── Key ─────────────────────────────────────────────────────────────
        to_hex(md5(cast(coalesce(cast(s.store_id as string), '_dbt_utils_surrogate_key_null_') as string)))
                                                    as store_sk,
        s.store_id,

        -- ── Geography ───────────────────────────────────────────────────────
        s.city_name,
        s.state_name,
        s.locality,
        s.latitude,
        s.longitude,

        -- ── Store attributes ────────────────────────────────────────────────
        s.sku_capacity,
        s.delivery_radius_km,
        s.launch_date,
        s.days_since_launch,

        -- ── Fleet ───────────────────────────────────────────────────────────
        coalesce(rs.total_riders, 0)                as total_riders,
        coalesce(rs.electric_scooter_riders, 0)     as electric_scooter_riders,
        coalesce(rs.bike_riders, 0)                 as bike_riders,
        coalesce(rs.bicycle_riders, 0)              as bicycle_riders,

        -- ── Performance ─────────────────────────────────────────────────────
        coalesce(os.total_orders, 0)                as total_orders,
        coalesce(os.delivered_orders, 0)            as delivered_orders,
        coalesce(os.cancelled_orders, 0)            as cancelled_orders,
        os.avg_delivery_minutes,
        coalesce(os.on_time_pct, 0)                 as on_time_pct,
        coalesce(os.total_revenue, 0)               as total_revenue,
        os.first_order_date,
        os.last_order_date,

        -- ── Derived labels ──────────────────────────────────────────────────
        case
            when coalesce(os.total_orders, 0) = 0 then 'Not Operational'
            when os.volume_percentile <= 0.2      then 'High Volume'   -- Top 20%
            when os.volume_percentile <= 0.8      then 'Medium Volume' -- Next 30%
            else 'Low Volume'                                          -- Bottom 50%
        end                                         as volume_tier,

        case
            when coalesce(os.on_time_pct, 0) >= 90 then 'Excellent'
            when coalesce(os.on_time_pct, 0) >= 75 then 'Good'
            when coalesce(os.on_time_pct, 0) >= 60 then 'Needs Improvement'
            else 'Critical'
        end                                         as delivery_performance_tier

    from stores s
    left join rider_stats  rs on s.store_id = rs.store_id
    left join order_stats  os on s.store_id = os.store_id
)

select * from final