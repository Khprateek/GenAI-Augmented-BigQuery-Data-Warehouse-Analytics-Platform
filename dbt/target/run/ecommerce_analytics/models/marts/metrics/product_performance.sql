
  
    

    create or replace table `genai-copilot-enterprisedata`.`metrics`.`product_performance`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- product_performance.sql
-- ============================================================================
-- Product performance summary for BI dashboards.
-- Flat, wide table ordered by revenue for quick top-N queries.
--
-- Grain: one row per product_id
-- Depends on: dim_products
-- ============================================================================

select
    -- Identity
    product_id,
    product_name,
    category_name,
    brand_name,
    pack_size,

    -- Attributes
    is_perishable,
    shelf_life_tier,
    price_tier,

    -- Pricing (INR)
    mrp,
    selling_price,
    cost_price,
    discount_from_mrp_pct,
    gross_margin_pct,

    -- Volume
    total_orders,
    total_units_sold,
    units_per_day,

    -- Revenue & Profit (INR)
    total_revenue,
    avg_selling_price,
    gross_profit,
    realised_margin_pct,
    margin_health,

    -- Quality signals
    substitution_count,
    substitution_rate_pct,
    total_issues,
    issue_rate_pct,
    top_issue_type,

    -- Labels
    sales_performance,

    -- Dates
    first_sold_date,
    last_sold_date

from `genai-copilot-enterprisedata`.`marts`.`dim_products`
order by total_revenue desc
    );
  