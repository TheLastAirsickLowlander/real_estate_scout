"""Core listing/travel persistence operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from ..models import Listing, TravelResult

logger = logging.getLogger(__name__)


def backfill_zillow_urls(
    conn: psycopg2.extensions.connection, *, only_missing: bool = True
) -> int:
    where_clause = "WHERE (is_rejected IS NOT TRUE)"
    if only_missing:
        where_clause += " AND (zillow_url IS NULL OR zillow_url = '')"

    with conn.cursor() as cur:
        cur.execute("ALTER TABLE listings ADD COLUMN IF NOT EXISTS zillow_url TEXT;")
        cur.execute(
            "ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_rejected BOOLEAN NOT NULL DEFAULT FALSE;"
        )
        cur.execute(
            f"""
            UPDATE listings
            SET zillow_url = 'https://www.zillow.com/homes/'
                || regexp_replace(lower(trim(address)), '[^a-z0-9]+', '-', 'g')
                || '_rb/',
                last_updated = NOW()
            {where_clause}
            """
        )
        return int(cur.rowcount)


def get_cached_listing(
    conn: psycopg2.extensions.connection, *, listing_url: str, max_age_days: int = 7
) -> Listing | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                SELECT id, address, price, bedrooms, bathrooms, sqft,
                       zestimate, listing_url, zillow_url, status, mls_status,
                       lat, lng, description, highlights, features, first_seen, last_updated
                FROM listings
                WHERE listing_url = %s
                  AND last_updated > %s
                  AND is_active = TRUE
                """,
                (listing_url, cutoff),
            )
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()
            cur.execute(
                """
                SELECT id, address, price, bedrooms, bathrooms, sqft,
                       zestimate, listing_url, zillow_url, status, mls_status,
                       lat, lng, description, highlights, features, first_seen, last_updated
                FROM listings
                WHERE listing_url = %s
                  AND last_updated > %s
                  AND is_active = TRUE
                """,
                (listing_url, cutoff),
            )

        row = cur.fetchone()
        if not row:
            return None

        listing = _row_to_listing(row)

        cur.execute(
            """
            SELECT destination_name, duration_minutes, distance_miles, traffic_aware
            FROM travel_times
            WHERE listing_id = %s
            """,
            (listing.id,),
        )
        for travel_row in cur.fetchall():
            listing.travel_times[travel_row["destination_name"]] = TravelResult(
                destination=travel_row["destination_name"],
                duration_minutes=int(travel_row["duration_minutes"]),
                distance_miles=float(travel_row["distance_miles"]),
                traffic_aware=bool(travel_row["traffic_aware"]),
            )

        return listing


def upsert_listing(conn: psycopg2.extensions.connection, listing: Listing) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, price FROM listings WHERE listing_url = %s",
            (listing.listing_url,),
        )
        existing = cur.fetchone()

        if existing:
            listing_id, old_price = existing

            cur.execute(
                """
                UPDATE listings SET
                    address = %s,
                    price = %s,
                    bedrooms = %s,
                    bathrooms = %s,
                    sqft = %s,
                    zestimate = %s,
                    listing_url = %s,
                    zillow_url = %s,
                    status = %s,
                    mls_status = %s,
                    lat = %s,
                    lng = %s,
                    description = %s,
                    highlights = %s,
                    features = %s,
                    last_updated = NOW(),
                    is_active = TRUE
                WHERE id = %s
                """,
                (
                    listing.address,
                    listing.price,
                    listing.bedrooms,
                    listing.bathrooms,
                    listing.sqft,
                    listing.zestimate,
                    listing.listing_url,
                    listing.zillow_url or None,
                    listing.status or None,
                    listing.mls_status or None,
                    listing.lat,
                    listing.lng,
                    listing.description,
                    json.dumps(listing.highlights),
                    json.dumps(listing.features),
                    listing_id,
                ),
            )

            if old_price != listing.price:
                cur.execute(
                    """
                    INSERT INTO price_history (listing_id, price, zestimate)
                    VALUES (%s, %s, %s)
                    """,
                    (listing_id, listing.price, listing.zestimate),
                )
                logger.info(
                    f"Price change detected for {listing.address}: ${old_price:,} -> ${listing.price:,}"
                )
        else:
            cur.execute(
                """
                INSERT INTO listings (
                    address, price, bedrooms, bathrooms, sqft,
                    zestimate, listing_url, zillow_url, status, mls_status,
                    lat, lng, description, highlights, features
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    listing.address,
                    listing.price,
                    listing.bedrooms,
                    listing.bathrooms,
                    listing.sqft,
                    listing.zestimate,
                    listing.listing_url,
                    listing.zillow_url or None,
                    listing.status or None,
                    listing.mls_status or None,
                    listing.lat,
                    listing.lng,
                    listing.description,
                    json.dumps(listing.highlights),
                    json.dumps(listing.features),
                ),
            )
            res = cur.fetchone()
            if res is None:
                raise RuntimeError("Failed to insert listing")
            listing_id = int(res[0])

            cur.execute(
                """
                INSERT INTO price_history (listing_id, price, zestimate)
                VALUES (%s, %s, %s)
                """,
                (listing_id, listing.price, listing.zestimate),
            )

        return int(listing_id)


def mark_listings_inactive(
    conn: psycopg2.extensions.connection, active_listing_urls: list[str]
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE listings
            SET is_active = FALSE
            WHERE is_active = TRUE
              AND listing_url != ALL(%s)
            """,
            (active_listing_urls,),
        )


def save_travel_time(
    conn: psycopg2.extensions.connection,
    *,
    listing_id: int,
    destination_name: str,
    destination_address: str,
    travel_result: TravelResult,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO travel_times (
                listing_id, destination_name, destination_address,
                duration_minutes, distance_miles, traffic_aware
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (listing_id, destination_name)
            DO UPDATE SET
                duration_minutes = EXCLUDED.duration_minutes,
                distance_miles = EXCLUDED.distance_miles,
                traffic_aware = EXCLUDED.traffic_aware,
                calculated_at = NOW()
            """,
            (
                listing_id,
                destination_name,
                destination_address,
                travel_result.duration_minutes,
                travel_result.distance_miles,
                travel_result.traffic_aware,
            ),
        )


def load_listings_from_db(
    conn: psycopg2.extensions.connection,
    *,
    listing_urls: list[str],
    destination_names: list[str] | None = None,
) -> list[Listing]:
    if not listing_urls:
        return []

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                SELECT id, address, price, bedrooms, bathrooms, sqft,
                       zestimate, listing_url, zillow_url, status, mls_status,
                       lat, lng, description, highlights, features, first_seen, last_updated
                FROM listings
                WHERE listing_url = ANY(%s)
                  AND is_active = TRUE
                """,
                (listing_urls,),
            )
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()
            cur.execute(
                """
                SELECT id, address, price, bedrooms, bathrooms, sqft,
                       zestimate, listing_url, zillow_url, status, mls_status,
                       lat, lng, description, highlights, features, first_seen, last_updated
                FROM listings
                WHERE listing_url = ANY(%s)
                  AND is_active = TRUE
                """,
                (listing_urls,),
            )
        listing_rows = cur.fetchall()

        listings = [_row_to_listing(row) for row in listing_rows]

        listing_ids = [l.id for l in listings if l.id is not None]
        if not listing_ids:
            return listings

        if destination_names:
            cur.execute(
                """
                SELECT listing_id, destination_name, duration_minutes, distance_miles, traffic_aware
                FROM travel_times
                WHERE listing_id = ANY(%s)
                  AND destination_name = ANY(%s)
                """,
                (listing_ids, destination_names),
            )
        else:
            cur.execute(
                """
                SELECT listing_id, destination_name, duration_minutes, distance_miles, traffic_aware
                FROM travel_times
                WHERE listing_id = ANY(%s)
                """,
                (listing_ids,),
            )

        travel_rows = cur.fetchall()

    travel_by_listing: dict[int, dict[str, TravelResult]] = {}
    for row in travel_rows:
        lid = int(row["listing_id"])
        travel_by_listing.setdefault(lid, {})
        travel_by_listing[lid][row["destination_name"]] = TravelResult(
            destination=row["destination_name"],
            duration_minutes=int(row["duration_minutes"]),
            distance_miles=float(row["distance_miles"]),
            traffic_aware=bool(row["traffic_aware"]),
        )

    for listing in listings:
        if listing.id is not None:
            listing.travel_times = travel_by_listing.get(int(listing.id), {})

    return listings


def get_active_listings(conn: psycopg2.extensions.connection) -> list[Listing]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        try:
            cur.execute(
                """
                SELECT id, address, price, bedrooms, bathrooms, sqft,
                       zestimate, listing_url, zillow_url, status, mls_status,
                       lat, lng, description, highlights, features, first_seen, last_updated
                FROM listings
                WHERE is_active = TRUE
                ORDER BY id
                """
            )
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()
            cur.execute(
                """
                SELECT id, address, price, bedrooms, bathrooms, sqft,
                       zestimate, listing_url, lat, lng, description,
                       features, first_seen, last_updated
                FROM listings
                WHERE is_active = TRUE
                ORDER BY id
                """
            )
        return [_row_to_listing(row) for row in cur.fetchall()]


def _row_to_listing(row: dict) -> Listing:
    features = row.get("features", [])
    if isinstance(features, str):
        features = json.loads(features)

    highlights = row.get("highlights", [])
    if isinstance(highlights, str):
        highlights = json.loads(highlights)

    return Listing(
        id=row.get("id"),
        address=row.get("address", ""),
        price=int(row.get("price") or 0),
        bedrooms=int(row.get("bedrooms") or 0),
        bathrooms=float(row.get("bathrooms") or 0.0),
        sqft=int(row.get("sqft") or 0),
        zestimate=row.get("zestimate"),
        listing_url=row.get("listing_url", ""),
        zillow_url=row.get("zillow_url") or "",
        status=row.get("status") or "",
        mls_status=row.get("mls_status") or "",
        lat=float(row.get("lat") or 0.0),
        lng=float(row.get("lng") or 0.0),
        description=row.get("description") or "",
        highlights=highlights if isinstance(highlights, list) else [],
        features=features if isinstance(features, list) else [],
        first_seen=row.get("first_seen"),
        last_updated=row.get("last_updated"),
        travel_times={},
    )
