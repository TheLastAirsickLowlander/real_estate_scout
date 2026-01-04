"""Output formatters for listings."""

import csv
import json
from io import StringIO
from pathlib import Path
from typing import List, Optional

from rich.table import Table
from rich.console import Console

from .models import Listing


class Formatter:
    """Format listings for various output types."""

    def __init__(
        self, include_scores: bool = True, destination_names: list[str] | None = None
    ):
        self.include_scores = include_scores
        self.destination_names = destination_names or []

    def format_table(
        self, listings: List[Listing], sort_by: str = "price", top: Optional[int] = None
    ) -> str:
        """Format as a Rich table for terminal display."""
        sorted_listings = self._sort_listings(listings, sort_by)
        if top:
            sorted_listings = sorted_listings[:top]

        table = Table(
            title="Home Search Results",
            show_header=True,
            header_style="bold magenta",
            expand=True,
        )

        table.add_column("Address", width=30, overflow="fold")
        table.add_column("Price", justify="right")
        table.add_column("Beds", justify="right")
        table.add_column("Baths", justify="right")
        table.add_column("Sqft", justify="right")
        table.add_column("Avg Commute", justify="right")

        if self.include_scores:
            table.add_column("Score", justify="right")

        for listing in sorted_listings:
            avg_commute = self._avg_commute(listing)
            score_str = (
                f"{listing.combined_score:.0f}" if listing.combined_score else "-"
            )

            row = [
                listing.address[:30],
                f"${listing.price:,}",
                str(listing.bedrooms),
                str(listing.bathrooms),
                f"{listing.sqft:,}",
                f"{avg_commute} min",
            ]

            if self.include_scores:
                row.append(score_str)

            table.add_row(*row)

        console = Console()
        with console.capture() as capture:
            console.print(table)

        return capture.get()

    def format_csv(
        self, listings: List[Listing], filepath: Optional[str] = None
    ) -> str:
        """Format as CSV string and optionally write to file."""
        if not listings:
            return ""

        output = StringIO()
        fieldnames = self._get_csv_fields(listings)

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for listing in listings:
            row = listing.to_dict()
            writer.writerow(row)

        csv_content = output.getvalue()

        if filepath:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(csv_content)
            print(f"[green]CSV saved to: {filepath}[/green]")

        return csv_content

    def format_json(self, listings: List[Listing]) -> str:
        """Format as JSON string."""
        data = []
        for listing in listings:
            listing_dict = listing.to_dict(include_features=True)
            listing_dict["travel_times"] = {
                k: {
                    "destination": v.destination,
                    "duration_minutes": v.duration_minutes,
                    "distance_miles": v.distance_miles,
                }
                for k, v in listing.travel_times.items()
            }
            data.append(listing_dict)

        return json.dumps(data, indent=2)

    def _sort_listings(self, listings: List[Listing], sort_by: str) -> List[Listing]:
        """Sort listings by specified field."""
        reverse = False if sort_by in ["price", "avg_commute"] else True

        def sort_key(l: Listing):
            if sort_by == "price":
                return l.price
            elif sort_by == "avg_commute":
                return self._avg_commute(l)
            elif sort_by == "size":
                return l.sqft
            elif sort_by == "score" and l.combined_score:
                return l.combined_score
            return 0

        return sorted(listings, key=sort_key, reverse=reverse)

    def _avg_commute(self, listing: Listing) -> str:
        """Calculate average commute time in minutes."""
        if not listing.travel_times:
            return "-"

        times = [
            t.duration_minutes
            for t in listing.travel_times.values()
            if t.duration_minutes > 0
        ]
        if not times:
            return "-"

        return str(int(sum(times) / len(times)))

    def _get_csv_fields(self, listings: list[Listing] | None = None) -> list[str]:
        """Get CSV field names dynamically based on destinations.

        Args:
            listings: Optional list of listings to extract destination names from.
        """
        base_fields = [
            "address",
            "price",
            "bedrooms",
            "bathrooms",
            "sqft",
            "zestimate",
            "url",
            "score",
            "description",
        ]

        # Get destination names from provided list, listings, or fall back to empty
        dest_names: list[str] = []

        if self.destination_names:
            dest_names = self.destination_names
        elif listings:
            # Extract unique destination names from listings
            seen: set[str] = set()
            for listing in listings:
                for dest_name in listing.travel_times.keys():
                    if dest_name not in seen:
                        seen.add(dest_name)
                        dest_names.append(dest_name)

        # Add commute and distance columns for each destination
        for dest_name in dest_names:
            base_fields.append(f"commute_{dest_name}")
            base_fields.append(f"distance_{dest_name}")

        return base_fields
