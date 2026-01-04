#!/usr/bin/env python3
"""Real Estate Scout - Real Estate Decision Tool CLI."""

import argparse
import logging
import sys

from .config import load_config
from .database import ListingDatabase
from .exporter import DataExporter
from .filter import ListingFilter
from .formatter import Formatter
from .models import Listing
from .scorer import ListingScorer
from .search import ListingFetcher
from .travel import TravelCalculator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_export(args: argparse.Namespace, db: ListingDatabase) -> None:
    """Run the export command.

    Args:
        args: Parsed command line arguments.
        db: Database instance.
    """
    exporter = DataExporter(db, args.export_dir)

    # Show stats first
    exporter.print_stats()

    export_type = args.export
    export_format = args.export_format
    include_inactive = args.include_inactive

    print(f"\nExporting {export_type} as {export_format}...")
    print(f"Output directory: {args.export_dir}")

    if export_type == "all":
        results = exporter.export_all(export_format, include_inactive)
        print("\nExported files:")
        for table, paths in results.items():
            for path in paths:
                if path:
                    print(f"  {path}")
    elif export_type == "listings":
        if export_format in ("csv", "both"):
            path = exporter.export_listings_csv(include_inactive)
            print(f"  {path}")
        if export_format in ("json", "both"):
            path = exporter.export_listings_json(include_inactive, include_travel=True)
            print(f"  {path}")
    elif export_type == "price-history":
        if export_format in ("csv", "both"):
            path = exporter.export_price_history_csv()
            print(f"  {path}")
        if export_format in ("json", "both"):
            path = exporter.export_price_history_json()
            print(f"  {path}")
    elif export_type == "travel-times":
        if export_format in ("csv", "both"):
            path = exporter.export_travel_times_csv()
            print(f"  {path}")
        if export_format in ("json", "both"):
            path = exporter.export_travel_times_json()
            print(f"  {path}")

    print("\nExport complete!")


def run_update_travel(args: argparse.Namespace, config, db: ListingDatabase) -> None:
    """Recalculate travel times for active listings only.

    This mode avoids hitting the HomeHarvest listings API and only updates rows in
    `travel_times` for listings already in the database.

    Args:
        args: Parsed command line arguments.
        config: Application configuration.
        db: Database instance.
    """
    dests_to_use = config.destinations
    if config.max_destinations > 0:
        dests_to_use = config.destinations[: config.max_destinations]

    destination_names = [d["name"] for d in dests_to_use]
    listings = db.get_active_listings()
    if config.max_listings > 0 and len(listings) > config.max_listings:
        listings = listings[: config.max_listings]

    print(f"Updating travel times for {len(listings)} active listings")
    print(
        f"Destinations: {', '.join(destination_names) if destination_names else '(none)'}"
    )

    if not listings or not dests_to_use:
        print("Nothing to update")
        return

    travel_calc = TravelCalculator(
        use_approximate=config.use_approximate,
        rate_limit_delay=config.rate_limit_delay,
    )

    travel_results = travel_calc.calculate_matrix(listings, dests_to_use)
    updated = 0

    for listing in listings:
        if listing.address not in travel_results:
            continue

        listing_results = travel_results[listing.address]
        if not listing_results:
            continue

        for dest in dests_to_use:
            dest_name = dest["name"]
            result = listing_results.get(dest_name)
            if result is None:
                continue

            if listing.id is None:
                continue

            db.save_travel_time(
                listing.id,
                dest_name,
                dest["address"],
                result,
            )
            updated += 1

    print(f"Updated {updated} travel time records")


def run_search(args: argparse.Namespace, config, db: ListingDatabase | None) -> None:
    """Run the main search command.

    Args:
        args: Parsed command line arguments.
        config: Application configuration.
        db: Database instance (may be None).
    """
    fetcher = ListingFetcher()
    print("Fetching listings from API...")

    # Always fetch from API to get current market state
    listings = fetcher.search(
        location=config.center_address,
        radius_miles=config.radius_miles,
        listing_type=config.listing_type,
        property_types=config.property_types,
        past_days=config.past_days,
        price_min=config.min_price,
        price_max=config.max_price,
        beds_min=config.min_bedrooms,
        baths_min=config.min_bathrooms,
    )

    if not listings:
        print("No listings found!")
        sys.exit(0)

    print(f"Found {len(listings)} listings from API")

    filter_obj = ListingFilter(
        min_price=config.min_price,
        max_price=config.max_price,
        min_bedrooms=config.min_bedrooms,
        min_bathrooms=config.min_bathrooms,
    )
    listings = filter_obj.filter_listings(listings)
    print(f"After filtering: {len(listings)} listings")

    if config.max_listings > 0 and len(listings) > config.max_listings:
        listings = listings[: config.max_listings]
        print(f"Limited to {config.max_listings} listings for processing")

    # Database persistence and cache logic
    if db:
        print("\nSyncing with database...")

        # Get destination names for travel time lookup
        dests_to_use = config.destinations
        if config.max_destinations > 0:
            dests_to_use = config.destinations[: config.max_destinations]
        destination_names = [d["name"] for d in dests_to_use]

        # Track which listings need travel calculations
        listings_needing_travel: list[Listing] = []
        cached_count = 0

        for listing in listings:
            # Check if we have a fresh cached version with travel times
            cached = db.get_cached_listing(
                listing.listing_url, config.listing_max_age_days
            )

            if cached and cached.travel_times:
                # Check if cached has all needed destinations
                missing_dests = [
                    d for d in destination_names if d not in cached.travel_times
                ]
                if not missing_dests:
                    # Use cached travel times
                    listing.travel_times = cached.travel_times
                    listing.id = cached.id
                    cached_count += 1
                else:
                    # Need to calculate missing destinations
                    listing.id = db.upsert_listing(listing)
                    listings_needing_travel.append(listing)
            else:
                # Save/update listing and mark for travel calculation
                listing.id = db.upsert_listing(listing)
                listings_needing_travel.append(listing)

        print(f"  Loaded {cached_count} listings from cache with travel times")
        print(f"  {len(listings_needing_travel)} listings need travel calculations")

        # Note: we intentionally do NOT auto-mark listings inactive.
        # Listings remain visible until manually rejected in the web UI.
    else:
        listings_needing_travel = listings

    # Calculate travel times for listings that need them
    if not config.skip_travel and listings_needing_travel:
        print(
            f"\nCalculating travel times for {len(listings_needing_travel)} listings..."
        )
        travel_calc = TravelCalculator(
            use_approximate=config.use_approximate,
            rate_limit_delay=config.rate_limit_delay,
        )

        dests_to_use = config.destinations
        if config.max_destinations > 0:
            dests_to_use = config.destinations[: config.max_destinations]

        travel_results = travel_calc.calculate_matrix(
            listings_needing_travel, dests_to_use
        )

        for listing in listings_needing_travel:
            if listing.address in travel_results:
                listing.travel_times = travel_results[listing.address]

                # Save travel times to database
                if db and listing.id:
                    for dest in dests_to_use:
                        dest_name = dest["name"]
                        if dest_name in listing.travel_times:
                            db.save_travel_time(
                                listing.id,
                                dest_name,
                                dest["address"],
                                listing.travel_times[dest_name],
                            )
    elif config.skip_travel:
        print("\nSkipping travel calculations (haversine approximation)...")
        for listing in listings:
            if not listing.travel_times:
                listing.travel_times = {}

    if config.include_scores:
        print("Scoring listings...")
        scorer = ListingScorer(max_budget=config.max_price, min_budget=config.min_price)
        listings = scorer.score_listings(listings)

    formatter = Formatter(include_scores=config.include_scores)

    output_format = args.output or config.output_format

    if output_format == "table":
        result = formatter.format_table(listings, args.sort_by, args.top)
        print(result)
    elif output_format == "csv":
        csv_content = formatter.format_csv(listings, args.csv_output)
        if not args.csv_output:
            print(csv_content)
    elif output_format == "json":
        json_content = formatter.format_json(listings)
        print(json_content)

    print(f"\nDestinations analyzed:")
    dests_to_show = config.destinations
    if config.max_destinations > 0:
        dests_to_show = config.destinations[: config.max_destinations]
    for dest in dests_to_show:
        print(f"  - {dest['name']}: {dest['address']}")

    # Show database stats if enabled
    if db:
        print(f"\nDatabase: listings persisted to {config.database.name}")


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
