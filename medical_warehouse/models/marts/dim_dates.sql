-- Dimension table for dates
-- Generates a full date spine covering all message dates + 30 days buffer

{{ config(materialized='table') }}

WITH date_spine AS (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="cast(current_date + interval '30 days' as date)"
    ) }}
),

date_details AS (
    SELECT
        TO_CHAR(date_day, 'YYYYMMDD')::INTEGER      AS date_key,
        date_day                                     AS full_date,
        EXTRACT(DOW FROM date_day)::INTEGER          AS day_of_week,
        TO_CHAR(date_day, 'Day')                     AS day_name,
        EXTRACT(WEEK FROM date_day)::INTEGER         AS week_of_year,
        EXTRACT(MONTH FROM date_day)::INTEGER        AS month,
        TO_CHAR(date_day, 'Month')                   AS month_name,
        EXTRACT(QUARTER FROM date_day)::INTEGER      AS quarter,
        EXTRACT(YEAR FROM date_day)::INTEGER         AS year,
        CASE
            WHEN EXTRACT(DOW FROM date_day) IN (0, 6) THEN TRUE
            ELSE FALSE
        END                                          AS is_weekend
    FROM date_spine
)

SELECT * FROM date_details
