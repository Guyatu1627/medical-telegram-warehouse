-- Fact table for Telegram messages
-- Central fact table in the star schema connecting messages to channel and date dimensions

{{ config(materialized='table') }}

WITH messages AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),

channels AS (
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
),

dates AS (
    SELECT date_key, full_date FROM {{ ref('dim_dates') }}
)

SELECT
    m.message_id,
    c.channel_key,
    d.date_key,
    m.message_text,
    m.message_length,
    m.views                                     AS view_count,
    m.forwards                                  AS forward_count,
    m.has_image                                 AS has_image,
    m.image_path,
    m.message_date
FROM messages m
LEFT JOIN channels c
    ON m.channel_name = c.channel_name
LEFT JOIN dates d
    ON DATE(m.message_date) = d.full_date
