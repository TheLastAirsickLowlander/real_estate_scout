#!/usr/bin/env python3
"""Real Estate Scout - Real Estate Decision Tool CLI."""

import argparse
import logging
import sys

from .config import load_config
from .db import ListingDatabase
from .commands.export import run_export
from .commands.update_travel import run_update_travel
from .exporter import DataExporter
from .pipeline import run_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Real Estate Scout - Find and evaluate homes based on travel times"
    )
    parser.add_argument(
        "--config", "-c", help="Path to config.yaml file", default="config.yaml"
    )

    # Search/output options
    parser.add_argument(
        "--output",
        "-o",
        choices=["table", "csv", "json"],
        help="Output format for search results",
        default=None,
    )
    parser.add_argument(
        "--sort-by",
        choices=["price", "commute", "size", "score"],
        help="Sort results by",
        default="score",
    )
    parser.add_argument("--top", type=int, help="Limit to top N results", default=None)
    parser.add_argument("--csv-output", help="Save CSV to file", default=None)
    parser.add_argument(
        "--max-listings",
        type=int,
        help="Max listings to process (0 = from config, negative = all)",
        default=None,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all listings, ignore max_listings limit",
        default=None,
    )
    parser.add_argument(
        "--no-travel",
        action="store_true",
        help="Skip travel calculations, use haversine approximation",
        default=None,
    )
    parser.add_argument(
        "--delay",
        type=float,
        help="Rate limit delay in seconds between requests",
        default=None,
    )

    # Export options
    parser.add_argument(
        "--export",
        choices=["listings", "price-history", "travel-times", "all"],
        help="Export database contents (no new data fetching)",
        default=None,
    )
    parser.add_argument(
        "--export-format",
        choices=["csv", "json", "both"],
        help="Export file format",
        default="both",
    )
    parser.add_argument(
        "--export-dir",
        help="Directory for export files",
        default="exports",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive (off-market) listings in export",
        default=False,
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics only",
        default=False,
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create database tables/indexes if missing",
        default=False,
    )

    # Travel-only update
    parser.add_argument(
        "--update-travel",
        action="store_true",
        help="Recalculate and persist travel times for active listings only (no new HomeHarvest fetch)",
        default=False,
    )

    # Data maintenance
    parser.add_argument(
        "--backfill-zillow",
        action="store_true",
        help="Backfill zillow_url for active listings from address (no new HomeHarvest fetch)",
        default=False,
    )

    # Future features: --refresh, --history, --price-drops

    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Handle export and stats commands (require database)
    if args.export or args.stats:
        if not config.database.enabled:
            print("Error: Database must be enabled for export/stats commands")
            print("Set 'database.enabled: true' in config.yaml")
            sys.exit(1)

        db = ListingDatabase(config.database)
        if not db.test_connection():
            print("Error: Could not connect to database")
            sys.exit(1)

        if args.stats:
            exporter = DataExporter(db, args.export_dir)
            exporter.print_stats()
            sys.exit(0)

        if args.export:
            run_export(args, db)
            sys.exit(0)

    # Normal search flow
    cli_overrides = {}

    if args.max_listings is not None:
        cli_overrides["max_listings"] = args.max_listings

    if args.all:
        cli_overrides["max_listings"] = 0

    if args.no_travel is not None:
        cli_overrides["skip_travel"] = args.no_travel

    if args.delay is not None:
        cli_overrides["rate_limit_delay"] = args.delay

    for key, value in cli_overrides.items():
        setattr(config, key, value)

    print("Real Estate Scout - Real Estate Decision Tool")
    print("=" * 50)
    print(f"Searching near: {config.center_address}")
    print(f"Radius: {config.radius_miles} miles")
    print(f"Budget: ${config.min_price:,} - ${config.max_price:,}")
    print(f"Min bedrooms: {config.min_bedrooms}")
    if config.max_listings > 0:
        print(f"Max listings: {config.max_listings}")
    if config.skip_travel:
        print("Travel: haversine approximation (fast)")
    else:
        print(f"Travel: OSRM routing (delay: {config.rate_limit_delay}s)")

    # Initialize database if enabled
    db: ListingDatabase | None = None
    if config.database.enabled:
        candidate_db = ListingDatabase(config.database)
        if candidate_db.test_connection():
            db = candidate_db
            print(
                f"Database: connected to {config.database.host}/{config.database.name}"
            )
            if args.init_db:
                print("Database: initializing schema...")
                db.ensure_schema()
                print("Database: schema ready")
        else:
            print("Database: connection failed, proceeding without persistence")
    else:
        print("Database: disabled")

    # Travel-only update (requires database)
    if args.update_travel:
        if not db:
            print("Error: Database must be enabled for --update-travel")
            sys.exit(1)
        print("-" * 50)
        run_update_travel(args, config, db)
        sys.exit(0)

    if args.backfill_zillow:
        if not db:
            print("Error: Database must be enabled for --backfill-zillow")
            sys.exit(1)
        print("-" * 50)
        db.ensure_schema()
        updated = db.backfill_zillow_urls(only_missing=True)
        print(f"Backfilled zillow_url for {updated} listings")
        sys.exit(0)

    print("-" * 50)

    run_search(args, config, db)


if __name__ == "__main__":
    main()
