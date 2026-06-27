-- Staging model for raw Telegram messages
-- Cleans, casts, and standardizes raw data from raw.telegram_messages

WITH source AS (
    SELECT
        message_id,
        channel_name,
        message_date,
        message_text,
        has_media,
        image_path,
        views,
        forwards,
        scraped_at
    FROM {{ source('raw', 'telegram_messages') }}
),

cleaned AS (
    SELECT
        -- Cast and clean message ID
        TRIM(message_id)                                                AS message_id,

        -- Normalize channel name
        LOWER(TRIM(channel_name))                                       AS channel_name,

        -- Cast date to proper timestamp
        message_date::TIMESTAMPTZ                                       AS message_date,

        -- Clean message text (remove nulls and extra whitespace)
        NULLIF(TRIM(message_text), '')                                  AS message_text,

        -- Media flags
        COALESCE(has_media, FALSE)                                      AS has_media,
        image_path,

        -- Cast view and forward counts (default to 0 if null or negative)
        GREATEST(COALESCE(views::INTEGER, 0), 0)                        AS views,
        GREATEST(COALESCE(forwards::INTEGER, 0), 0)                     AS forwards,

        -- Calculated fields
        COALESCE(LENGTH(TRIM(message_text)), 0)                         AS message_length,
        CASE WHEN image_path IS NOT NULL AND image_path != '' THEN TRUE
             ELSE FALSE END                                             AS has_image,

        scraped_at
    FROM source
    -- Filter out records with no text AND no media
    WHERE NOT (
        (message_text IS NULL OR TRIM(message_text) = '')
        AND has_media = FALSE
    )
    -- Filter out future-dated messages
    AND message_date <= NOW()
)

SELECT * FROM cleaned
