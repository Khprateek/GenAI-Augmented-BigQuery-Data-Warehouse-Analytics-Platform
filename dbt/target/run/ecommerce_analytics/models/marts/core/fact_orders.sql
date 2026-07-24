
  
    

    create or replace table `genai-copilot-enterprisedata`.`marts`.`fact_orders`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- fact_orders.sql
-- ============================================================================
-- Central order fact table for the quick-commerce star schema.
-- One row per order with surrogate-key FKs to all dimension tables.
-- All monetary measures in INR, all additive.
--
-- Grain: one row per order_id
-- Depends on: int_orders_enriched, dim_customers, dim_products,
--             dim_dark_stores, dim_delivery_partners, dim_date
-- ============================================================================

with orders as (
    select * from `genai-copilot-enterprisedata`.`staging`.`int_orders_enriched`
),

dim_customers as (
    select customer_sk, customer_id
    from `genai-copilot-enterprisedata`.`marts`.`dim_customers`
),

dim_dark_stores as (
    select store_sk, store_id
    from `genai-copilot-enterprisedata`.`marts`.`dim_dark_stores`
),

dim_riders as (
    select rider_sk, rider_id
    from `genai-copilot-enterprisedata`.`marts`.`dim_delivery_partners`
),

-- Primary product per order: highest line-revenue item
dim_products_bridge as (
    select
        oi.order_id,
        dp.product_sk
    from `genai-copilot-enterprisedata`.`staging`.`stg_order_items` oi
    inner join `genai-copilot-enterprisedata`.`marts`.`dim_products` dp on oi.product_id = dp.product_id
    qualify row_number() over (
        partition by oi.order_id
        order by oi.line_revenue desc
    ) = 1
),

dim_date as (
    select date_key, full_date
    from `genai-copilot-enterprisedata`.`marts`.`dim_date`
),

final as (
    select
        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Surrogate & Natural Keys                                       ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        to_hex(md5(cast(coalesce(cast(o.order_id as string), '_dbt_utils_surrogate_key_null_') as string)))
                                                        as order_sk,
        o.order_id,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Foreign Keys → Dimensions                                      ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        dc.customer_sk,
        ds.store_sk,
        dr.rider_sk,
        dpb.product_sk                                  as primary_product_sk,
        dd.date_key                                     as order_date_key,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Degenerate Dimensions                                          ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.order_status,
        o.payment_method,
        o.platform,
        o.customer_type,
        o.basket_size_tier,
        o.delivery_time_bucket,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Date & Time                                                    ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.order_timestamp,
        o.order_date,
        o.order_year,
        o.order_month,
        o.order_week,
        o.order_day_of_week,
        o.order_hour,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Location                                                       ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.customer_city,
        o.customer_state,
        o.store_city,
        o.store_locality,
        o.is_home_store_order,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Delivery Performance Measures                                  ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.promised_delivery_minutes,
        o.actual_delivery_minutes,
        o.is_on_time,
        o.delivery_delay_minutes,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Basket Measures                                                ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.total_items,
        o.unique_products,
        o.substituted_item_count,
        o.has_substitution,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Financial Measures (INR, additive)                             ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.revenue,
        o.discount,
        o.delivery_fee,
        o.refund_amount,
        o.gross_revenue,
        o.net_revenue,
        o.discount_pct,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Issue Measures                                                 ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.issue_count,
        o.has_order_issue,
        o.primary_issue_type,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Customer Context                                               ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        o.is_pass_member,
        o.days_since_signup,

        -- ╔═══════════════════════════════════════════════════════════════════╗
        -- ║  Convenience Flags (for BI aggregation)                         ║
        -- ╚═══════════════════════════════════════════════════════════════════╝
        case when o.order_status = 'DELIVERED'       then 1 else 0 end as is_delivered,
        case when o.order_status = 'CANCELLED'       then 1 else 0 end as is_cancelled,
        case when o.order_status = 'FAILED_DELIVERY' then 1 else 0 end as is_failed_delivery

    from orders o
    left join dim_customers       dc  on o.customer_id = dc.customer_id
    left join dim_dark_stores     ds  on o.store_id    = ds.store_id
    left join dim_riders          dr  on o.rider_id    = dr.rider_id
    left join dim_products_bridge dpb on o.order_id    = dpb.order_id
    left join dim_date            dd  on o.order_date  = dd.full_date
)

select * from final
    );
  