
  
    

    create or replace table `genai-copilot-enterprisedata`.`marts`.`dim_date`
      
    
    

    
    OPTIONS()
    as (
      -- ============================================================================
-- dim_date.sql
-- ============================================================================
-- Calendar dimension: one row per day from project start_date to today + 1 yr.
-- Uses BigQuery GENERATE_DATE_ARRAY.
-- Indian fiscal year (April–March) and Indian public holiday awareness.
--
-- Grain: one row per date
-- ============================================================================

with date_spine as (
    select date_val
    from unnest(
        generate_date_array(
            '2022-01-01',
            date_add(current_date(), interval 365 day),
            interval 1 day
        )
    ) as date_val
),

enriched as (
    select
        -- ── Key ─────────────────────────────────────────────────────────────
        cast(format_date('%Y%m%d', date_val) as integer)    as date_key,
        date_val                                             as full_date,

        -- ── Gregorian calendar ──────────────────────────────────────────────
        extract(year      from date_val)                     as year,
        extract(quarter   from date_val)                     as quarter_number,
        concat('Q', extract(quarter from date_val))          as quarter_name,
        extract(month     from date_val)                     as month_number,
        format_date('%B',  date_val)                          as month_name,
        format_date('%b',  date_val)                          as month_short,

        -- ── Week ────────────────────────────────────────────────────────────
        extract(isoweek   from date_val)                     as iso_week_number,
        extract(dayofweek from date_val)                     as day_of_week,        -- 1 = Sun
        format_date('%A',  date_val)                          as day_name,
        format_date('%a',  date_val)                          as day_short,

        -- ── Day ─────────────────────────────────────────────────────────────
        extract(day       from date_val)                     as day_of_month,
        extract(dayofyear from date_val)                     as day_of_year,

        -- ── Flags ───────────────────────────────────────────────────────────
        case extract(dayofweek from date_val)
            when 1 then true when 7 then true else false
        end                                                  as is_weekend,

        -- ── Indian Fiscal Year (April–March) ────────────────────────────────
        case
            when extract(month from date_val) >= 4
                then extract(year from date_val)
            else extract(year from date_val) - 1
        end                                                  as fiscal_year_start,
        concat(
            'FY',
            case
                when extract(month from date_val) >= 4
                    then cast(extract(year from date_val) as string)
                else cast(extract(year from date_val) - 1 as string)
            end
        )                                                    as fiscal_year_label,
        case
            when extract(month from date_val) in (4,5,6)   then 1
            when extract(month from date_val) in (7,8,9)   then 2
            when extract(month from date_val) in (10,11,12) then 3
            else 4
        end                                                  as fiscal_quarter,

        -- ── Period labels for dashboard filters ─────────────────────────────
        format_date('%Y-%m', date_val)                       as year_month,
        format_date('%G-W%V', date_val)                      as year_week,

        -- ── Relative date flags ─────────────────────────────────────────────
        date_val = current_date()                            as is_today,
        date_val >= date_sub(current_date(), interval 7 day)  as is_last_7d,
        date_val >= date_sub(current_date(), interval 30 day) as is_last_30d,
        date_val >= date_sub(current_date(), interval 90 day) as is_last_90d

    from date_spine
)

select * from enriched
    );
  