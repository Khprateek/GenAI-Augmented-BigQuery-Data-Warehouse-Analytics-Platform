-- ============================================================================
-- funnel_stages.sql
-- ============================================================================
-- Unpivoted funnel for Streamlit bar/funnel charts.
-- Each row = one (date, stage_name, count) tuple for easy plotting.
--
-- Grain: one row per (event_date, stage_name)
-- Depends on: conversion_rate
-- ============================================================================

select
    event_date,
    'Page Views'        as stage_name,
    1                   as stage_order,
    page_viewers        as user_count
from `genai-copilot-enterprisedata`.`metrics`.`conversion_rate`

union all

select
    event_date,
    'Add to Cart',
    2,
    add_to_carters
from `genai-copilot-enterprisedata`.`metrics`.`conversion_rate`

union all

select
    event_date,
    'Begin Checkout',
    3,
    checkout_starters
from `genai-copilot-enterprisedata`.`metrics`.`conversion_rate`

union all

select
    event_date,
    'Purchase',
    4,
    purchasers
from `genai-copilot-enterprisedata`.`metrics`.`conversion_rate`

order by event_date desc, stage_order