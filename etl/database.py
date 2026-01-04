"""Database operations for Real Estate Scout."""

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator

import psycopg2
from psycopg2.extras import RealDictCursor

from .models import DatabaseConfig, Listing, TravelResult

logger = logging.getLogger(__name__)


class ListingDatabase:
    """PostgreSQL database operations for listings."""

    def backfill_zillow_urls(self, only_missing: bool = True) -> int:
        """Populate `zillow_url` using the listing address.

        This uses a best-effort Zillow search URL derived from the listing address.

        Args:
            only_missing: If True, only update rows where zillow_url is NULL/empty.

        Returns:
            Number of rows updated.
        """

        where_clause = "WHERE (is_rejected IS NOT TRUE)"
        if only_missing:
            where_clause += " AND (zillow_url IS NULL OR zillow_url = '')"

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Ensure migration exists before update
                cur.execute(
                    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS zillow_url TEXT;"
                )
                cur.execute(
                    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_rejected BOOLEAN NOT NULL DEFAULT FALSE;"
                )

                # Generate a stable-ish URL slug in SQL
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
                updated = cur.rowcount

            conn.commit()

        return int(updated)

    def __init__(self, config: DatabaseConfig):
        """Initialize database connection parameters."""
        self.config = config

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Get a database connection as a context manager."""
        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.name,
            user=self.config.user,
            password=self.config.password,
        )
        try:
            yield conn
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        """Create required tables and indexes if missing.

        This is intentionally idempotent and safe to run on every startup.
        """
        with self.get_connection() as conn:
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
                cur.execute(
                    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS zillow_url TEXT;"
                )
                cur.execute(
                    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS highlights JSONB NOT NULL DEFAULT '[]'::jsonb;"
                )
                cur.execute(
                    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS status TEXT;"
                )
                cur.execute(
                    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS mls_status TEXT;"
                )
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

    def test_connection(self) -> bool:
        """Test if database connection works."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as exc:
            logger.error(f"Database connection failed: {exc}")
            return False

    def get_cached_listing(
        self, listing_url: str, max_age_days: int = 7
    ) -> Listing | None:
        """Get a listing from cache if it exists and is fresh enough."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        with self.get_connection() as conn:
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

                listing = self._row_to_listing(row)

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

    def upsert_listing(self, listing: Listing) -> int:
        """Insert or update a listing, recording price history if changed."""
        with self.get_connection() as conn:
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
                            f"Price change detected for {listing.address}: "
                            f"${old_price:,} -> ${listing.price:,}"
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

                conn.commit()
                return int(listing_id)

    def mark_listings_inactive(self, active_listing_urls: list[str]) -> None:
        """Mark listings not in the current scrape as inactive."""
        with self.get_connection() as conn:
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
            conn.commit()

    def save_travel_time(
        self,
        listing_id: int,
        destination_name: str,
        destination_address: str,
        travel_result: TravelResult,
    ) -> None:
        """Save a travel time calculation."""
        with self.get_connection() as conn:
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
            conn.commit()

    def get_travel_times(self, listing_id: int) -> dict[str, TravelResult]:
        """Get all travel times for a listing."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT destination_name, duration_minutes, distance_miles, traffic_aware
                    FROM travel_times
                    WHERE listing_id = %s
                    """,
                    (listing_id,),
                )
                return {
                    row["destination_name"]: TravelResult(
                        destination=row["destination_name"],
                        duration_minutes=int(row["duration_minutes"]),
                        distance_miles=float(row["distance_miles"]),
                        traffic_aware=bool(row["traffic_aware"]),
                    )
                    for row in cur.fetchall()
                }

    def get_listings_needing_travel(
        self, listing_ids: list[int], destination_names: list[str]
    ) -> dict[int, list[str]]:
        """Get listings that need travel time calculations."""
        if not listing_ids or not destination_names:
            return {}

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT listing_id, destination_name
                    FROM travel_times
                    WHERE listing_id = ANY(%s)
                      AND destination_name = ANY(%s)
                    """,
                    (listing_ids, destination_names),
                )
                existing = {(row[0], row[1]) for row in cur.fetchall()}

        result: dict[int, list[str]] = {}
        for listing_id in listing_ids:
            missing = [
                dest for dest in destination_names if (listing_id, dest) not in existing
            ]
            if missing:
                result[listing_id] = missing

        return result

    def load_listings_from_db(
        self, listing_urls: list[str], destination_names: list[str] | None = None
    ) -> list[Listing]:
        """Load listings from database with their travel times."""
        if not listing_urls:
            return []

        with self.get_connection() as conn:
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

                listings = [self._row_to_listing(row) for row in listing_rows]

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
            if lid not in travel_by_listing:
                travel_by_listing[lid] = {}
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

    def export_all_listings(self, include_inactive: bool = False) -> list[dict]:
        """Export all listings from the database."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                        SELECT 
                            id, address, price, bedrooms, bathrooms, sqft,
                            zestimate, listing_url, zillow_url, status, mls_status,
                            lat, lng, description, highlights, features, first_seen, last_updated, is_active
                        FROM listings
                """
                try:
                    cur.execute(
                        query
                        + (" WHERE is_active = TRUE" if not include_inactive else "")
                        + " ORDER BY id"
                    )
                    rows = cur.fetchall()
                except psycopg2.errors.UndefinedColumn:
                    conn.rollback()
                    query = """
                        SELECT 
                            id, address, price, bedrooms, bathrooms, sqft,
                            zestimate, listing_url, zillow_url, status, mls_status,
                            lat, lng, description, highlights, features, first_seen, last_updated, is_active
                        FROM listings
                    """
                    cur.execute(
                        query
                        + (" WHERE is_active = TRUE" if not include_inactive else "")
                        + " ORDER BY id"
                    )
                    rows = cur.fetchall()

                result: list[dict] = []
                for row in rows:
                    record = dict(row)
                    if record.get("first_seen"):
                        record["first_seen"] = record["first_seen"].isoformat()
                    if record.get("last_updated"):
                        record["last_updated"] = record["last_updated"].isoformat()
                    if isinstance(record.get("features"), str):
                        record["features"] = json.loads(record["features"])
                    if isinstance(record.get("highlights"), str):
                        record["highlights"] = json.loads(record["highlights"])
                    result.append(record)

                return result

    def export_price_history(self) -> list[dict]:
        """Export all price history records."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        ph.id,
                        ph.listing_id,
                        l.address,
                        l.listing_url,
                        ph.price,
                        ph.zestimate,
                        ph.observed_at
                    FROM price_history ph
                    JOIN listings l ON l.id = ph.listing_id
                    ORDER BY ph.listing_id, ph.observed_at
                    """
                )
                rows = cur.fetchall()

                result: list[dict] = []
                for row in rows:
                    record = dict(row)
                    if record.get("observed_at"):
                        record["observed_at"] = record["observed_at"].isoformat()
                    result.append(record)

                return result

    def export_travel_times(self) -> list[dict]:
        """Export all travel time records."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        tt.id,
                        tt.listing_id,
                        l.address AS listing_address,
                        tt.destination_name,
                        tt.destination_address,
                        tt.duration_minutes,
                        tt.distance_miles,
                        tt.traffic_aware,
                        tt.calculated_at
                    FROM travel_times tt
                    JOIN listings l ON l.id = tt.listing_id
                    ORDER BY tt.listing_id, tt.destination_name
                    """
                )
                rows = cur.fetchall()

                result: list[dict] = []
                for row in rows:
                    record = dict(row)
                    if record.get("calculated_at"):
                        record["calculated_at"] = record["calculated_at"].isoformat()
                    if record.get("distance_miles") is not None:
                        record["distance_miles"] = float(record["distance_miles"])
                    result.append(record)

                return result

    def export_listings_with_travel(self, include_inactive: bool = False) -> list[dict]:
        """Export listings with travel times as nested data."""
        listings = self.export_all_listings(include_inactive)

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        listing_id,
                        destination_name,
                        destination_address,
                        duration_minutes,
                        distance_miles,
                        traffic_aware
                    FROM travel_times
                    ORDER BY listing_id, destination_name
                    """
                )
                travel_rows = cur.fetchall()

        travel_by_listing: dict[int, list[dict]] = {}
        for row in travel_rows:
            listing_id = int(row["listing_id"])
            if listing_id not in travel_by_listing:
                travel_by_listing[listing_id] = []
            travel_by_listing[listing_id].append(
                {
                    "destination_name": row["destination_name"],
                    "destination_address": row["destination_address"],
                    "duration_minutes": row["duration_minutes"],
                    "distance_miles": float(row["distance_miles"]),
                    "traffic_aware": row["traffic_aware"],
                }
            )

        for listing in listings:
            listing["travel_times"] = travel_by_listing.get(int(listing["id"]), [])

        return listings

    def get_database_stats(self) -> dict:
        """Get statistics about the database contents."""
        with self.get_connection() as conn:
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

    def get_active_listings(self) -> list[Listing]:
        """Load all active listings from database."""
        with self.get_connection() as conn:
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
                return [self._row_to_listing(row) for row in cur.fetchall()]

    def _row_to_listing(self, row: dict) -> Listing:
        """Convert a database row to a Listing object."""
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
