-- Dimension table for Telegram channels
-- Provides surrogate keys and channel-level analytics

{{ config(materialized='table') }}

WITH channel_stats AS (
    SELECT
        channel_name,
        MIN(message_date)                   AS first_post_date,
        MAX(message_date)                   AS last_post_date,
        COUNT(*)                            AS total_posts,
        AVG(views)                          AS avg_views,
        SUM(CASE WHEN has_image THEN 1 ELSE 0 END) AS total_images
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY channel_name
),

with_type AS (
    SELECT
        channel_name,
        first_post_date,
        last_post_date,
        total_posts,
        ROUND(avg_views::NUMERIC, 2)    AS avg_views,
        total_images,
        CASE
            WHEN channel_name ILIKE '%lobelia%' OR channel_name ILIKE '%cosmetic%'
                THEN 'Cosmetics'
            WHEN channel_name ILIKE '%pharma%' OR channel_name ILIKE '%tikvah%'
                THEN 'Pharmaceutical'
            WHEN channel_name ILIKE '%chemed%' OR channel_name ILIKE '%med%'
                THEN 'Medical'
            ELSE 'Other'
        END                             AS channel_type
    FROM channel_stats
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['channel_name']) }} AS channel_key,
    channel_name,
    channel_type,
    first_post_date,
    last_post_date,
    total_posts,
    avg_views,
    total_images
FROM with_type
