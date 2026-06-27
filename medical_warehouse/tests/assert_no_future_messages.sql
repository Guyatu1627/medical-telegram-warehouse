-- Custom dbt test: assert_no_future_messages
-- Ensures no messages have a date in the future
-- This query must return 0 rows to pass

SELECT
    message_id,
    channel_name,
    message_date
FROM {{ ref('stg_telegram_messages') }}
WHERE message_date > NOW()
