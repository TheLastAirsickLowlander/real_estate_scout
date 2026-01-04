"""Travel-time recomputation command."""

from __future__ import annotations

import argparse

from ..db import ListingDatabase
from ..travel import TravelCalculator


def run_update_travel(args: argparse.Namespace, config, db: ListingDatabase) -> None:
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
