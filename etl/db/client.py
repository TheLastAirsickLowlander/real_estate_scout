"""Database client facade.

This module keeps backwards compatibility with the original `ListingDatabase`
public API while delegating responsibilities to submodules.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2

from ..models import DatabaseConfig
from .exports import export_all_listings
from .exports import export_listings_with_travel
from .exports import export_price_history
from .exports import export_travel_times
from .listing_ops import backfill_zillow_urls
from .listing_ops import get_active_listings
from .listing_ops import get_cached_listing
from .listing_ops import load_listings_from_db
from .listing_ops import mark_listings_inactive
from .listing_ops import save_travel_time
from .listing_ops import upsert_listing
from .stats import get_database_stats
from .schema import ensure_schema

logger = logging.getLogger(__name__)


class ListingDatabase:
    """PostgreSQL database operations for listings."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
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

    def test_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as exc:
            logger.error(f"Database connection failed: {exc}")
            return False

    def ensure_schema(self) -> None:
        with self.get_connection() as conn:
            ensure_schema(conn)

    def backfill_zillow_urls(self, only_missing: bool = True) -> int:
        with self.get_connection() as conn:
            updated = backfill_zillow_urls(conn, only_missing=only_missing)
            conn.commit()
            return int(updated)

    def get_cached_listing(self, listing_url: str, max_age_days: int = 7):
        with self.get_connection() as conn:
            return get_cached_listing(
                conn, listing_url=listing_url, max_age_days=max_age_days
            )

    def upsert_listing(self, listing):
        with self.get_connection() as conn:
            listing_id = upsert_listing(conn, listing)
            conn.commit()
            return int(listing_id)

    def mark_listings_inactive(self, active_listing_urls: list[str]) -> None:
        with self.get_connection() as conn:
            mark_listings_inactive(conn, active_listing_urls)
            conn.commit()

    def save_travel_time(
        self,
        listing_id: int,
        destination_name: str,
        destination_address: str,
        travel_result,
    ):
        with self.get_connection() as conn:
            save_travel_time(
                conn,
                listing_id=listing_id,
                destination_name=destination_name,
                destination_address=destination_address,
                travel_result=travel_result,
            )
            conn.commit()

    def load_listings_from_db(
        self, listing_urls: list[str], destination_names: list[str] | None = None
    ):
        with self.get_connection() as conn:
            return load_listings_from_db(
                conn, listing_urls=listing_urls, destination_names=destination_names
            )

    def get_active_listings(self):
        with self.get_connection() as conn:
            return get_active_listings(conn)

    def get_database_stats(self) -> dict:
        with self.get_connection() as conn:
            return get_database_stats(conn)

    def export_all_listings(self, include_inactive: bool = False):
        with self.get_connection() as conn:
            return export_all_listings(conn, include_inactive=include_inactive)

    def export_price_history(self):
        with self.get_connection() as conn:
            return export_price_history(conn)

    def export_travel_times(self):
        with self.get_connection() as conn:
            return export_travel_times(conn)

    def export_listings_with_travel(self, include_inactive: bool = False):
        with self.get_connection() as conn:
            return export_listings_with_travel(conn, include_inactive=include_inactive)
