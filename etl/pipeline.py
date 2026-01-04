"""Core search pipeline orchestration."""

from __future__ import annotations

import argparse
import sys

from .db import ListingDatabase
from .filter import ListingFilter
from .formatter import Formatter
from .models import Listing
from .scorer import ListingScorer
from .search import ListingFetcher
from .travel import TravelCalculator


def run_search(args: argparse.Namespace, config, db: ListingDatabase | None) -> None:
    fetcher = ListingFetcher()
    print("Fetching listings from API...")

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

    if db:
        print("\nSyncing with database...")

        dests_to_use = config.destinations
        if config.max_destinations > 0:
            dests_to_use = config.destinations[: config.max_destinations]
        destination_names = [d["name"] for d in dests_to_use]

        listings_needing_travel: list[Listing] = []
        cached_count = 0

        for listing in listings:
            cached = db.get_cached_listing(
                listing.listing_url, config.listing_max_age_days
            )

            if cached and cached.travel_times:
                missing_dests = [
                    d for d in destination_names if d not in cached.travel_times
                ]
                if not missing_dests:
                    listing.travel_times = cached.travel_times
                    listing.id = cached.id
                    cached_count += 1
                else:
                    listing.id = db.upsert_listing(listing)
                    listings_needing_travel.append(listing)
            else:
                listing.id = db.upsert_listing(listing)
                listings_needing_travel.append(listing)

        print(f"  Loaded {cached_count} listings from cache with travel times")
        print(f"  {len(listings_needing_travel)} listings need travel calculations")
    else:
        listings_needing_travel = listings

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

    print("\nDestinations analyzed:")
    dests_to_show = config.destinations
    if config.max_destinations > 0:
        dests_to_show = config.destinations[: config.max_destinations]
    for dest in dests_to_show:
        print(f"  - {dest['name']}: {dest['address']}")

    if db:
        print(f"\nDatabase: listings persisted to {config.database.name}")
