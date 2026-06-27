-- Fact table for YOLO image detection results
-- Joins image analysis results with the messages fact and channel dimension

{{ config(materialized='table') }}

WITH yolo_raw AS (
    SELECT
        message_id,
        LOWER(TRIM(channel_name))               AS channel_name,
        detected_class,
        confidence_score,
        image_category,
        image_path
    FROM {{ source('raw', 'yolo_detections') }}
),

messages AS (
    SELECT
        message_id,
        channel_key,
        date_key,
        image_path
    FROM {{ ref('fct_messages') }}
    WHERE has_image = TRUE
),

channels AS (
    SELECT channel_key, channel_name
    FROM {{ ref('dim_channels') }}
)

SELECT
    y.message_id,
    m.channel_key,
    m.date_key,
    y.detected_class,
    y.confidence_score,
    y.image_category,
    y.image_path
FROM yolo_raw y
LEFT JOIN channels c
    ON y.channel_name = c.channel_name
LEFT JOIN messages m
    ON y.message_id = m.message_id
    AND m.channel_key = c.channel_key
