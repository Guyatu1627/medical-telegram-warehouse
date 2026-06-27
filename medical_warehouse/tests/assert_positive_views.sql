-- Custom dbt test: assert_positive_views
-- Ensures no messages have a negative view count
-- This query must return 0 rows to pass

SELECT
    message_id,
    channel_name,
    views
FROM {{ ref('stg_telegram_messages') }}
WHERE views < 0
