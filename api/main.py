"""
Medical Telegram Warehouse — Analytical API
FastAPI application exposing analytical endpoints over the dbt star schema.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from api.database import get_db_session, check_db_connection
from api.schemas import (
    TopProductsResponse, TopProductItem,
    ChannelActivityResponse, DailyActivity,
    MessageSearchResponse, MessageSearchItem,
    VisualContentResponse, VisualContentChannelStat,
)
from typing import Optional
from datetime import datetime
import re

app = FastAPI(
    title="Medical Telegram Warehouse API",
    description="""
    Analytical REST API for Ethiopian Medical Telegram channel data.

    Provides insights from the dbt star schema including:
    - Top mentioned products
    - Channel activity trends
    - Message search
    - Visual content statistics
    """,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="API Root")
async def root():
    return {"message": "Welcome to the Medical Telegram Warehouse API", "docs": "/docs"}


@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database_connected": db_ok
    }


# ── Endpoint 1: Top Products ───────────────────────────────────────────────────

@app.get(
    "/api/reports/top-products",
    response_model=TopProductsResponse,
    tags=["Reports"],
    summary="Top most frequently mentioned product terms",
    description="Returns the most frequently mentioned product terms across all Telegram channel messages."
)
async def top_products(
    limit: int = Query(default=10, ge=1, le=100, description="Number of top products to return")
):
    # Common stopwords to filter
    stopwords = (
        "the", "a", "an", "and", "or", "for", "of", "in", "to", "is", "it",
        "this", "that", "with", "are", "be", "as", "at", "by", "we", "our",
        "available", "now", "new", "quality", "get", "your", "you", "all", "from",
        "have", "has", "not", "on", "can", "will", "price", "order", "contact",
        "more", "best", "good", "high", "only", "also", "than", "its"
    )

    try:
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT
                        LOWER(word) AS term,
                        COUNT(*) AS frequency
                    FROM (
                        SELECT regexp_split_to_table(LOWER(message_text), E'\\\\s+') AS word
                        FROM public.fct_messages
                        WHERE message_text IS NOT NULL
                          AND LENGTH(message_text) > 0
                    ) words
                    WHERE
                        LENGTH(word) > 3
                        AND word ~ '^[a-z]+$'
                        AND word NOT IN :stopwords
                    GROUP BY LOWER(word)
                    ORDER BY frequency DESC
                    LIMIT :limit
                """),
                {"stopwords": tuple(stopwords), "limit": limit}
            )
            rows = result.fetchall()
        items = [TopProductItem(term=row[0], frequency=row[1]) for row in rows]
        return TopProductsResponse(limit=limit, results=items)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database query failed: {str(e)}")


# ── Endpoint 2: Channel Activity ───────────────────────────────────────────────

@app.get(
    "/api/channels/{channel_name}/activity",
    response_model=ChannelActivityResponse,
    tags=["Channels"],
    summary="Channel posting activity and trends",
    description="Returns posting activity, view statistics, and daily trends for a specific channel."
)
async def channel_activity(
    channel_name: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of recent days to include")
):
    try:
        with get_db_session() as session:
            # Channel-level metrics
            channel_result = session.execute(
                text("""
                    SELECT
                        c.channel_name,
                        c.total_posts,
                        c.avg_views
                    FROM public.dim_channels c
                    WHERE LOWER(c.channel_name) = LOWER(:channel_name)
                """),
                {"channel_name": channel_name}
            ).fetchone()

            if not channel_result:
                raise HTTPException(status_code=404, detail=f"Channel '{channel_name}' not found")

            # Daily activity breakdown
            daily_result = session.execute(
                text("""
                    SELECT
                        TO_CHAR(f.message_date, 'YYYY-MM-DD') AS date,
                        COUNT(*) AS message_count,
                        SUM(f.view_count) AS total_views,
                        SUM(f.forward_count) AS total_forwards
                    FROM public.fct_messages f
                    JOIN public.dim_channels c ON f.channel_key = c.channel_key
                    WHERE LOWER(c.channel_name) = LOWER(:channel_name)
                      AND f.message_date >= NOW() - INTERVAL '1 day' * :days
                    GROUP BY TO_CHAR(f.message_date, 'YYYY-MM-DD')
                    ORDER BY date DESC
                """),
                {"channel_name": channel_name, "days": days}
            ).fetchall()

        daily = [
            DailyActivity(
                date=row[0],
                message_count=row[1],
                total_views=row[2] or 0,
                total_forwards=row[3] or 0
            )
            for row in daily_result
        ]

        return ChannelActivityResponse(
            channel_name=channel_result[0],
            total_posts=channel_result[1],
            avg_views=float(channel_result[2] or 0),
            daily_activity=daily
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database query failed: {str(e)}")


# ── Endpoint 3: Message Search ─────────────────────────────────────────────────

@app.get(
    "/api/search/messages",
    response_model=MessageSearchResponse,
    tags=["Search"],
    summary="Search messages by keyword",
    description="Searches for messages containing a specific keyword (case-insensitive, full-text search)."
)
async def search_messages(
    query: str = Query(..., min_length=2, description="Search keyword or phrase"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results to return")
):
    try:
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT
                        f.message_id,
                        c.channel_name,
                        f.message_date,
                        f.message_text,
                        f.view_count,
                        f.forward_count
                    FROM public.fct_messages f
                    JOIN public.dim_channels c ON f.channel_key = c.channel_key
                    WHERE f.message_text ILIKE :query
                    ORDER BY f.view_count DESC
                    LIMIT :limit
                """),
                {"query": f"%{query}%", "limit": limit}
            ).fetchall()

        items = [
            MessageSearchItem(
                message_id=row[0],
                channel_name=row[1],
                message_date=row[2],
                message_text=row[3],
                views=row[4] or 0,
                forwards=row[5] or 0
            )
            for row in result
        ]

        return MessageSearchResponse(query=query, total_results=len(items), results=items)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database query failed: {str(e)}")


# ── Endpoint 4: Visual Content Stats ──────────────────────────────────────────

@app.get(
    "/api/reports/visual-content",
    response_model=VisualContentResponse,
    tags=["Reports"],
    summary="Visual content statistics across channels",
    description="Returns image usage statistics and top YOLO detection categories per channel."
)
async def visual_content_stats():
    try:
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT
                        c.channel_name,
                        COUNT(f.message_id)                                     AS total_messages,
                        SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END)           AS messages_with_images,
                        ROUND(
                            100.0 * SUM(CASE WHEN f.has_image THEN 1 ELSE 0 END)
                            / NULLIF(COUNT(f.message_id), 0), 2
                        )                                                       AS image_percentage,
                        MODE() WITHIN GROUP (ORDER BY d.image_category)         AS top_image_category
                    FROM public.fct_messages f
                    JOIN public.dim_channels c ON f.channel_key = c.channel_key
                    LEFT JOIN public.fct_image_detections d ON f.message_id = d.message_id
                    GROUP BY c.channel_name
                    ORDER BY image_percentage DESC
                """)
            ).fetchall()

        channels = [
            VisualContentChannelStat(
                channel_name=row[0],
                total_messages=row[1],
                messages_with_images=row[2] or 0,
                image_percentage=float(row[3] or 0),
                top_image_category=row[4]
            )
            for row in result
        ]

        return VisualContentResponse(total_channels=len(channels), channels=channels)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database query failed: {str(e)}")
