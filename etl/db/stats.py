"""Read-only statistics queries."""

from __future__ import annotations

import psycopg2


def get_database_stats(conn: psycopg2.extensions.connection) -> dict:
    with conn.cursor() as cur:
        stats: dict[str, int] = {}

        cur.execute("SELECT COUNT(*) FROM listings WHERE is_active = TRUE")
        row = cur.fetchone()
        stats["active_listings"] = int(row[0]) if row else 0

        cur.execute("SELECT COUNT(*) FROM listings WHERE is_active = FALSE")
        row = cur.fetchone()
        stats["inactive_listings"] = int(row[0]) if row else 0

        cur.execute("SELECT COUNT(*) FROM price_history")
        row = cur.fetchone()
        stats["price_history_records"] = int(row[0]) if row else 0

        cur.execute("SELECT COUNT(*) FROM travel_times")
        row = cur.fetchone()
        stats["travel_time_records"] = int(row[0]) if row else 0

        cur.execute("SELECT COUNT(DISTINCT destination_name) FROM travel_times")
        row = cur.fetchone()
        stats["unique_destinations"] = int(row[0]) if row else 0

        cur.execute(
            """
            SELECT COUNT(*) FROM listings l
            JOIN LATERAL (
                SELECT price FROM price_history
                WHERE listing_id = l.id
                ORDER BY observed_at ASC LIMIT 1
            ) ph ON true
            WHERE l.is_active = TRUE AND l.price < ph.price
            """
        )
        row = cur.fetchone()
        stats["listings_with_price_drops"] = int(row[0]) if row else 0

        return stats
