-- ============================================================================
-- conversion_rate.sql
-- ============================================================================
-- Daily event funnel: page_view → add_to_cart → reorder_click → purchase.
-- Adapted for quick-commerce (no session_id or device_type in raw events,
-- uses customer_id as the session proxy).
--
-- Grain: one row per event_date
-- Depends on: stg_events
-- ============================================================================

with events as (
    select * from `genai-copilot-enterprisedata`.`staging`.`stg_events`
),

daily_funnel as (
    select
        event_date,

        -- Total events & unique visitors
        count(*)                                            as total_events,
        count(distinct customer_id)                         as unique_visitors,

        -- Funnel stages (count distinct customers at each step)
        count(distinct case when event_type = 'page_view'
                            then customer_id end)           as page_viewers,

        count(distinct case when event_type = 'add_to_cart'
                            then customer_id end)           as add_to_carters,

        count(distinct case when event_type = 'begin_checkout'
                            then customer_id end)           as checkout_starters,

        count(distinct case when event_type = 'reorder_click'
                            then customer_id end)           as reorder_clickers,

        count(distinct case when event_type = 'purchase'
                            then customer_id end)           as purchasers

    from events
    where customer_id is not null
      and customer_id != ''
    group by event_date
),

with_rates as (
    select
        *,

        -- Conversion rates
        round(safe_divide(add_to_carters, page_viewers), 4)
                                                                    as view_to_cart_pct,
        round(safe_divide(checkout_starters, add_to_carters), 4)
                                                                    as cart_to_checkout_pct,
        round(safe_divide(purchasers, page_viewers), 4)
                                                                    as overall_conversion_pct,
        round(safe_divide(purchasers, checkout_starters), 4)
                                                                    as checkout_to_purchase_pct,

        -- Reorder engagement
        round(safe_divide(reorder_clickers, unique_visitors), 4)
                                                                    as reorder_click_rate_pct

    from daily_funnel
)

select * from with_rates
order by event_date desc