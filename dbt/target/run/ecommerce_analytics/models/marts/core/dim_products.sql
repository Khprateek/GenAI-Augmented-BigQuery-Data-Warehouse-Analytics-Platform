
  
    

    create or replace table `genai-copilot-enterprisedata`.`marts`.`dim_products`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- dim_products.sql
-- ============================================================================
-- Product dimension for quick-commerce grocery/essentials catalog.
-- Enriched with margin analysis, sales performance labels, perishability,
-- substitution & issue quality signals.
--
-- Grain: one row per product_id
-- Depends on: stg_products, int_product_revenue
-- ============================================================================

with products as (
    select * from `genai-copilot-enterprisedata`.`staging`.`stg_products`
),

product_perf as (
    select * from `genai-copilot-enterprisedata`.`staging`.`int_product_revenue`
),

final as (
    select
        -- ── Key ─────────────────────────────────────────────────────────────
        to_hex(md5(cast(coalesce(cast(p.product_id as string), '_dbt_utils_surrogate_key_null_') as string)))
                                                        as product_sk,
        p.product_id,

        -- ── Product attributes ──────────────────────────────────────────────
        p.product_name,
        p.category_name,
        p.brand_name,
        p.pack_size,

        -- ── Perishability ───────────────────────────────────────────────────
        p.is_perishable,
        p.shelf_life_days,
        case
            when p.shelf_life_days <= 7   then 'Ultra-Short'
            when p.shelf_life_days <= 30  then 'Short'
            when p.shelf_life_days <= 180 then 'Medium'
            else 'Long'
        end                                             as shelf_life_tier,

        -- ── Pricing (INR) ───────────────────────────────────────────────────
        p.mrp,
        p.selling_price,
        p.cost_price,
        coalesce(pp.discount_from_mrp_pct, 0)           as discount_from_mrp_pct,
        coalesce(pp.gross_margin_pct, 0)                as gross_margin_pct,

        -- Price tier (INR thresholds for quick-commerce baskets)
        case
            when p.selling_price >= 500 then 'Premium'
            when p.selling_price >= 150 then 'Mid-Range'
            when p.selling_price >= 50  then 'Value'
            else 'Budget'
        end                                             as price_tier,

        -- ── Sales volume ────────────────────────────────────────────────────
        coalesce(pp.total_orders, 0)                    as total_orders,
        coalesce(pp.total_units_sold, 0)                as total_units_sold,

        -- ── Revenue & profitability (INR) ───────────────────────────────────
        coalesce(pp.total_revenue, 0)                   as total_revenue,
        coalesce(pp.avg_selling_price, 0)               as avg_selling_price,
        coalesce(pp.gross_profit, 0)                    as gross_profit,
        coalesce(pp.realised_margin_pct, 0)             as realised_margin_pct,

        -- ── Quality signals ─────────────────────────────────────────────────
        coalesce(pp.substitution_count, 0)              as substitution_count,
        coalesce(pp.substitution_rate_pct, 0)           as substitution_rate_pct,
        coalesce(pp.total_issues, 0)                    as total_issues,
        coalesce(pp.issue_rate_pct, 0)                  as issue_rate_pct,
        pp.top_issue_type,

        -- ── Velocity ────────────────────────────────────────────────────────
        pp.first_sold_date,
        pp.last_sold_date,
        coalesce(pp.units_per_day, 0)                   as units_per_day,

        -- ── Performance label ───────────────────────────────────────────────
        case
            when coalesce(pp.total_revenue, 0) >= 100000 then 'Star'
            when coalesce(pp.total_revenue, 0) >= 25000  then 'Strong'
            when coalesce(pp.total_revenue, 0) >= 5000   then 'Moderate'
            when coalesce(pp.total_revenue, 0) > 0       then 'Slow Mover'
            else 'No Sales'
        end                                             as sales_performance,

        -- ── Margin health label ─────────────────────────────────────────────
        case
            when coalesce(pp.realised_margin_pct, 0) >= 20 then 'Healthy'
            when coalesce(pp.realised_margin_pct, 0) >= 10 then 'Adequate'
            when coalesce(pp.realised_margin_pct, 0) >= 0  then 'Thin'
            else 'Loss-Making'
        end                                             as margin_health

    from products p
    left join product_perf pp on p.product_id = pp.product_id
)

select * from final
    );
  