"""Export-oriented queries."""

from __future__ import annotations

import json

import psycopg2
from psycopg2.extras import RealDictCursor


def export_all_listings(
    conn: psycopg2.extensions.connection, *, include_inactive: bool = False
) -> list[dict]:
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


def export_price_history(conn: psycopg2.extensions.connection) -> list[dict]:
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


def export_travel_times(conn: psycopg2.extensions.connection) -> list[dict]:
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


def export_listings_with_travel(
    conn: psycopg2.extensions.connection, *, include_inactive: bool = False
) -> list[dict]:
    listings = export_all_listings(conn, include_inactive=include_inactive)

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
        travel_by_listing.setdefault(listing_id, [])
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
