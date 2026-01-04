"""Schema management helpers."""

from __future__ import annotations

import psycopg2


def ensure_schema(conn: psycopg2.extensions.connection) -> None:
    """Create required tables and indexes if missing.

    Intentionally idempotent and safe to run on every startup.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                address TEXT NOT NULL,
                price INTEGER NOT NULL,
                bedrooms INTEGER NOT NULL,
                bathrooms NUMERIC NOT NULL,
                sqft INTEGER NOT NULL,
                zestimate INTEGER,
                listing_url TEXT UNIQUE NOT NULL,
                zillow_url TEXT,
                status TEXT,
                mls_status TEXT,
                lat DOUBLE PRECISION NOT NULL,
                lng DOUBLE PRECISION NOT NULL,
                description TEXT,
                highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
                features JSONB NOT NULL DEFAULT '[]'::jsonb,
                first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_rejected BOOLEAN NOT NULL DEFAULT FALSE,
                is_starred BOOLEAN NOT NULL DEFAULT FALSE,
                viewed_at TIMESTAMPTZ
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                price INTEGER NOT NULL,
                zestimate INTEGER,
                observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS travel_times (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                destination_name TEXT NOT NULL,
                destination_address TEXT NOT NULL,
                duration_minutes NUMERIC NOT NULL,
                distance_miles NUMERIC NOT NULL,
                traffic_aware BOOLEAN NOT NULL DEFAULT FALSE,
                calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(listing_id, destination_name)
            );
            """
        )

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listings_active ON listings(is_active);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listings_last_updated ON listings(last_updated);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_price_history_listing_id ON price_history(listing_id);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_travel_times_listing_id ON travel_times(listing_id);"
        )

        # Forward-compatible schema migrations
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS zillow_url TEXT;")
        cur.execute(
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS highlights JSONB NOT NULL DEFAULT '[]'::jsonb;"
        )
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS status TEXT;")
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS mls_status TEXT;")
        cur.execute(
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_rejected BOOLEAN NOT NULL DEFAULT FALSE;"
        )
        cur.execute(
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_starred BOOLEAN NOT NULL DEFAULT FALSE;"
        )
        cur.execute(
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS viewed_at TIMESTAMPTZ;"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listings_rejected ON listings(is_rejected);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listings_starred ON listings(is_starred);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_listings_viewed_at ON listings(viewed_at);"
        )

    conn.commit()
